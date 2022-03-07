---
title: 'Dockerize a Next.js app using multi-stage builds'
date: 2022-02-26T01:14:31-08:00
tags:
  - Next.js
  - Docker
  - JavaScript
cover:
  image: 'covers/nextjs-docker.png'
ShowToc: true
---

{{< alert theme="info" >}}See the [**source code**](https://github.com/johnnymetz/docker-nextjs) for a working example.{{< /alert >}}

[Next.js](https://nextjs.org/) is a popular React Framework that comes with a lot of great features such as hybrid static & server rendering, smart bundling, file system routing, and much more. I prefer it over vanilla React.

When we dockerize a Next.js application, we want the final production and development images to be small, fast to build and easy to maintain. Let's see how we can use [multi-stage builds](https://docs.docker.com/develop/develop-images/multistage-build/) and other image optimization techniques to create the ideal images.

## Stage 1: Install dependencies

```dockerfile
FROM node:17-alpine AS deps
WORKDIR /app
COPY package*.json .
ARG NODE_ENV
ENV NODE_ENV $NODE_ENV
RUN npm install
```

Start by installing our dependencies into a layer called `deps` using the `package.json` and `package-lock.json` files.

We'll inject `NODE_ENV=production` at image build time to prevent any dev dependencies from being installed. Per the [npm install docs](https://docs.npmjs.com/cli/v8/commands/npm-install):

> With the `--production` flag (or when the `NODE_ENV` environment variable is set to `production`), npm will not install modules listed in `devDependencies`.

## Stage 2: Build

```dockerfile
FROM node:17-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY src ./src
COPY public ./public
COPY package.json next.config.js jsconfig.json ./
RUN npm run build
```

Create a new layer called `builder`. Copy the `node_modules/` directory, which was created in the `deps` stage, plus any other files you need to build your app.

We could copy everything using `COPY . .` but it's better if we only bring in what we need. This is why we're using the [Next.js src directory](https://nextjs.org/docs/advanced-features/src-directory) which consists entirely of files we need to build our app and cuts down on the number of `COPY` commands. As we'll see in the [Image Sizes](#image-sizes) table below, this will dramatically reduce the final image size.

The `jsconfig.json` file allows us to use [absolute imports](https://nextjs.org/docs/advanced-features/module-path-aliases) in our code which are much cleaner than relative imports.

## Stage 3: Run

```dockerfile
FROM node:17-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
CMD ["npm", "run", "start"]
```

At this point, we have everything we need. We just have to copy in the relevant files to our final layer and run the app. Assigning the final layer a name is unnecessary. Note, `.next/` contains our application build. `public/` is not included in the build so be sure to copy it over.

## Complete Dockerfile

```dockerfile
# Stage 1: install dependencies
FROM node:17-alpine AS deps
WORKDIR /app
COPY package*.json .
ARG NODE_ENV
ENV NODE_ENV $NODE_ENV
RUN npm install

# Stage 2: build
FROM node:17-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY src ./src
COPY public/ ./public
COPY package.json next.config.js jsconfig.json ./
RUN npm run build

# Stage 3: run
FROM node:17-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
CMD ["npm", "run", "start"]
```

## Build the Docker images

Multi-stage builds allow us to create different images using the same `Dockerfile`. We can build both our production and development images using the following `docker-compose.yaml` configuration:

```yaml
services:
  app-prod:
    build:
      context: .
      args:
        - NODE_ENV=production
    ports:
      - '3000:3000'

  app-dev:
    build:
      context: .
      target: deps
    command: npm run dev
    ports:
      - '3001:3000'
    environment:
      - NODE_ENV=development
    volumes:
      - .:/app
      - /app/node_modules
      - /app/.next
```

In `app-prod`, we're injecting `NODE_ENV=production` as a [build argument](https://docs.docker.com/engine/reference/commandline/build/#set-build-time-variables---build-arg) because Next.js environment variables have to be set at build time. Setting them at runtime only works in development.

In `app-dev`, we're using the `--target deps` argument to tell docker to stop at the end of the `deps` build stage. The Next.js dev server doesn't use the Next.js build so there's no need to waste time on stages 2 and 3. This reduces the build time from 90 sec to 50 sec. Once the dependencies are cached on your machine, this drops to less than a second.

One more point is we're passing all our source code into the `app-dev` container as a mounted volume so our local changes are immediately reflected in the running container. The latter two volumes tell docker not to copy the `node_modules/` and `.next/` back to the host because we don't need them there.

## Image Sizes

Here are some image sizes to illustrate how important some of these factors are on the final result.

| Description                                        | Size   |
| -------------------------------------------------- | ------ |
| Optimized                                          | 322MB  |
| Single-stage                                       | 368MB  |
| All dependencies                                   | 409MB  |
| `COPY` all files instead of only the required ones | 456MB  |
| Use `node:17` instead of `node:17-alpine`          | 1.15GB |

May your Next.js images be small, fast and maintainable.
