---
title: 'Dockerize cypress open and cypress run'
date: 2022-01-10T21:08:44-08:00
tags:
  - Docker
  - Cypress
ShowToc: true
draft: true
---

UI testing is a critical part of any modern web application. My favorite testing framework is [Cypress](https://docs.cypress.io). It's designed for quickly writing clean and reliable tests and consists of two main commands:

- `cypress open`: Opens Cypress in the interactive GUI. Used for local development.
- `cypress run`: Runs Cypress tests from the CLI without the GUI. Used mostly in CI/CD.

I like to dockerize my entire application so it can be run anywhere (my machine, coworker's machine, CI/CD, etc.) and Cypress is no exception. We're going to dockerize the `cypress open` and `cypress run` commands for a simple Todo app written in Django and Next.js (check out the source code [here](https://github.com/johnnymetz/cypress-docker-django-nextjs)).

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

We'll first review how to run Cypress on our host because it's similar to running it in docker. If you're new to Cypress, it may be helpful to review the [Getting Started](https://docs.cypress.io/guides/getting-started/installing-cypress) documentation.

## Run Cypress on host

Assuming we've [installed Cypress](https://docs.cypress.io/guides/getting-started/installing-cypress), ensure `package.json` contains the following npm scripts:

```json
{
  "scripts": {
    "cypress:open": "cypress open",
    "cypress:run": "cypress run"
  }
}
```

Update the `cypress.json` file:

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
- `BACKEND_HOST` tells Cypress where the backend is located, which is a custom environment variable I'm using to [seed the database](https://github.com/johnnymetz/cypress-docker-django-nextjs/blob/main/frontend/cypress/support/commands.js#L3).
- [`retries`](https://docs.cypress.io/guides/guides/test-retries) reduce test flakiness.

Next, spin up the application:

```
docker compose up -d
```

Now we can run Cypress like so:

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

Next, find the latest tag for the `cypress/included` image on [DockerHub](https://hub.docker.com/r/cypress/included/tags). It doesn't have an actual `lastest` tag so we'll need to hardcode the value. Note, Cypress has [several different docker images](https://github.com/cypress-io/cypress-docker-images) but this one includes everything we need.

### cypress run

Create a new file called `docker-compose.cypress-run.yaml` with our image tag:

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

`cypress open` is more involved because it contains the interactive GUI. We have to forward this GUI from the docker container to our host using an [X server](http://www.linfo.org/x_server.html), which is a program that is responsible for drawing GUI's on our screen.

#### Setup X server

This only describes how to setup X server on MacOS. Comment below if you figure out how to set this up on a different OS.

- Install [XQuartz](https://www.xquartz.org/), which is an X server distribution for Mac, with `brew install --cask xquartz`.
- Open XQuartz with `open -a XQuartz`.
- In the XQuartz preferences, go to the **Security** tab and make sure "Allow connections from network clients" is checked. Quit & restart XQuartz (to activate the setting).

![xquartz preferences](/xquartz-preferences.png)

- Run the following command in the terminal to allow our host to connect to X server.

```
$ xhost + 127.0.0.1
127.0.0.1 being added to access control list
```

- Set the `DISPLAY` variable, which we're going to pass to our Cypress docker container. This tells X server to forward the interactive GUI to `host.docker.internal`, which is a special DNS name that points to our host (read more about it [here](https://docs.docker.com/desktop/mac/networking/#use-cases-and-workarounds)).

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

The `cypress/included` docker image's entrypoint is `cypress run` so we need to overwrite that with `cypress open`. We also need to append `--project .` so Cypress can find the project files.

Now we can run our entire stack with one command:

```
docker compose -f docker-compose.yaml -f docker-compose.cypress-open.yaml up --abort-on-container-exit
```

Cypress is running in docker but we can use the interactive GUI on our host!

The GUI performance in docker isn't as good as on the host so I generally stick to the latter but it was fun figuring out how to dockerize it.

**What's your favorite tool to run in docker?**
