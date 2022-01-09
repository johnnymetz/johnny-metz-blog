---
title: 'Dockerize cypress run and cypress open'
date: 2022-01-10T21:08:44-08:00
tags:
  - Docker
  - Cypress
ShowToc: true
draft: true
---

UI testing is a critical part of any modern web application. My favorite testing framework is [Cypress](https://docs.cypress.io). It's designed for quickly writing clean and reliable tests. I generally use two main commands:

<!-- If you're new to Cypress, check out the [Getting Started guide](https://docs.cypress.io/guides/getting-started/installing-cypress). Once you have a few tests written, continue below. -->

- `cypress open`: Opens Cypress in the interactive GUI. Used for local development.
- `cypress run`: Runs Cypress tests from the CLI without the GUI. Used mostly in CI/CD.

I like to dockerize my entire application so I can run it anywhere (my machine, coworker's machine, CI/CD, etc.) and Cypress is no exception. We're going to dockerize a Cypress test suite for a Django and Next.js application (check out the source code [here](https://github.com/johnnymetz/cypress-docker-django-nextjs)).

{{< mp4-video src="/videos/cypress-run.mp4" >}}

Our application has a simple [`docker-compose.yaml`](https://github.com/johnnymetz/cypress-docker-django-nextjs/blob/main/docker-compose.yaml):

```yaml
services:
  backend:
    build: ./backend
    ports:
      - '8000:8000'
    ...

  frontend:
    build: ./frontend
    ports:
      - '3000:3000'
    ...
```

We'll first review how to run Cypress on our host because it's similar to running Cypress in docker. In both cases we need to add npm scripts to our `package.json` file:

```json
{
  "scripts": {
    "cypress:open": "cypress open",
    "cypress:run": "cypress run"
  }
}
```

## Run Cypress on host

First, update your `cypress.json` file:

```json
{
  "baseUrl": "http://localhost:3000",
  "env": {
    "BACKEND_HOST": "http://localhost:8000"
  },
  "retries": {
    "runMode": 2,
    "openMode": 0
  }
}
```

- `baseUrl` tells Cypress where the frontend is located.
- `BACKEND_HOST` tells Cypress where the backend is located, which is used for [seeding the database](https://github.com/johnnymetz/cypress-docker-django-nextjs/blob/main/frontend/cypress/support/commands.js#L3).
- [`retries`](https://docs.cypress.io/guides/guides/test-retries) reduce test flakiness.

Next, spin up your application:

```
docker compose up -d
```

Now you can run Cypress like so:

```
npm run cypress:open
npm run cypress:run
```

## Run Cypress in Docker

Create a new file called `cypress-docker.json`:

```json
{
  "baseUrl": "http://frontend:3000",
  "env": {
    "BACKEND_HOST": "http://backend:8000"
  },
  "retries": {
    "runMode": 2,
    "openMode": 0
  }
}
```

This looks almost identical to the `cypress.json` file we created earlier. The only difference is we're using the container name for each hostname instead of `localhost`:

- `http://localhost:3000` -> `http://frontend:3000`
- `http://localhost:8000` -> `http://backend:8000`

This is how containers talk to each other in docker compose. Read [Networking in Compose](https://docs.docker.com/compose/networking/) if you'd like to learn more.

Next, find the latest tag for the `cypress/included` image on [DockerHub](https://hub.docker.com/r/cypress/included/tags). It doesn't have a `lastest` tag so we need to hardcode the value.

### cypress run

Create a new file called `docker-compose.cypress-run.yaml` with our Cypress image tag:

```yaml
services:
  frontend:
    environment:
      - NEXT_PUBLIC_BACKEND_HOST=http://backend:8000

  cypress-run:
    image: cypress/included:<TAG>
    volumes:
      - ./frontend/cypress:/cypress
      - ./frontend/cypress-docker.json:/cypress.json
    depends_on:
      - frontend
```

Now we can run our entire stack with one command using docker. Awesome!

```
docker compose -f docker-compose.yaml -f docker-compose.cypress-run.yaml up --abort-on-container-exit
```

The `--abort-on-container-exit` option stops all containers when the Cypress tests are complete; otherwise the containers continue to run and the command hangs.

### cypress open

`cypress open` is more involved because it contains the interactive GUI. We have to forward this GUI from the docker container to our host using a special server called an X server, which is responsible for drawing GUI's on linux.

#### Setup the X server

This only describes how to setup X server on MacOS. Comment below if you figure out how to set this up on a different OS.

- Install [XQuartz](https://www.xquartz.org/), which is an X server distribution for Mac, with `brew install --cask xquartz`.
- Open XQuartz with `open -a XQuartz`.
- In the XQuartz preferences, go to the **Security** tab and make sure "Allow connections from network clients" is checked. Quit & restart XQuartz (to activate the setting).

![xquartz preferences](/xquartz-preferences.png)

- Navigate to your terminal and run the following command to allow our host to connect to the X server.

```
$ xhost + 127.0.0.1
127.0.0.1 being added to access control list
```

- Set the `DISPLAY` variable. This tells the X server to forward the interactive GUI to `host.docker.internal`, which is a special DNS name that points to our host (read more about it [here](https://docs.docker.com/desktop/mac/networking/#use-cases-and-workarounds)).

```
DISPLAY=host.docker.internal:0
```

#### Run cypress open

Create a new file called `docker-compose.cypress-open.yaml`:

```yaml
services:
  frontend:
    environment:
      - NEXT_PUBLIC_BACKEND_HOST=http://backend:8000

  cypress-open:
    image: cypress/included:<TAG>
    entrypoint: cypress open --project .
    environment:
      - DISPLAY
    volumes:
      - ./frontend/cypress:/cypress
      - ./frontend/cypress-docker.json:/cypress.json
    depends_on:
      - frontend
```

The `cypress/included` docker image's entrypoint is `cypress run` so we need to overwrite that with `cypress open`. We also need to append `--project .` so Cypress can find the relevant project files.

Now we can run our entire stack with one command using docker:

```
docker compose -f docker-compose.yaml -f docker-compose.cypress-open.yaml up --abort-on-container-exit
```

## Conclusion

Docker is an excellent tool for building an app that can be run anywhere. I execute `cypress run` in docker locally and in CI/CD all the time.

With `cypress open`, the GUI performance in docker isn't as good as on the host so I generally stick to the latter. But it was fun figuring out how to dockerize it.

**What's the coolest tool you run in docker?**

<!-- Now navigate to your terminal. First we're going to store our machine's IP address in a variable. You can also get this value in System Preferences > Network if you prefer.

```
IP=$(ipconfig getifaddr en0)
```

Let's add our IP to `xhost` so it's allowed to make connections to the X server.

```bash
$ xhost + $IP
10.0.0.112 being added to access control list
```

Now we're going to set a `DISPLAY` variable. This will be used in the next step.

```
DISPLAY=$IP:0
``` -->
