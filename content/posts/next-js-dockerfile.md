---
title: 'Next.js multi-stage Dockerfile'
date: 2022-02-02T22:14:31-08:00
tags:
  - Docker
  - JavaScript
  - Next.js
draft: true
---

<!--
# https://github.com/vercel/next.js/blob/canary/examples/with-docker/Dockerfile
# https://www.nicovak.com/posts/nextjs-docker-multistage
# https://www.cloudsavvyit.com/9260/what-are-multi-stage-docker-builds/
 -->

{{< alert theme="info" >}}See the [**source code**](https://github.com/johnnymetz/docker-nextjs) for a working example.{{< /alert >}}

[Next.js](https://nextjs.org/) is a popular React Framework. It comes with a lot of great features such as hybrid static & server rendering, smart bundling, file system routing, and much more. I prefer it over vanilla React.

Let's look at how to dockerize a Next.js application using [multi-stage builds](https://docs.docker.com/develop/develop-images/multistage-build/), which is a feature for minimizing the final image size.

## Stage 1: Install dependencies

```dockerfile
FROM node:17-alpine AS deps
WORKDIR /app
COPY package*.json .
ARG NODE_ENV
ENV NODE_ENV $NODE_ENV
RUN npm install
```

Start by installing our dependencies into a layer called `deps` using the `package.json` and `package-lock.json` files. As we'll see later, setting `NODE_ENV=production` at image build prevents any `devDependencies` from being installed.

## Step 2: Build

```dockerfile
FROM node:17-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY src ./src
COPY public/ ./public
COPY package.json next.config.js jsconfig.json ./
RUN npm run build
```

Create a new layer called `builder`. Copy the `node_modules/` directory, which was created in the `deps` stage, plus any other files you need to build your app.

We could copy everything over using `COPY . .` but it's better if we only bring in what we need. This will reduce the final image size. This is why we're using the [Next.js src directory](https://nextjs.org/docs/advanced-features/src-directory) which consists entirely of files we need to build our app.

Note, the `jsconfig.json` file allows us to use [absolute imports](https://nextjs.org/docs/advanced-features/module-path-aliases) in our code which are much cleaner than relative imports.

## Step 3: Run

```dockerfile
FROM node:17-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
CMD ["npm", "run", "start"]
```

At this point, we have everything we need. We just have to copy in the relevant files and run the app. `.next/` contains our build. `public/` is not included in the build so be sure to copy it over.

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

## Build the Docker image

Multi-stage builds allow us to create different images using the same `Dockerfile`. We can build both our production and development images using the following `docker-compose.yaml`:

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

The production build includes a `--build-arg NODE_ENV=production` argument because production environment variables have to be set at build time. Setting env vars at runtime only work for the dev server.

The `--target deps` argument tells the development build to stop at the end of the `deps` build stage. This makes sense because the next dev server doesn't use the next build so no need to waste time on stages 2 and 3.

## Image Sizes

Here are some image sizes to illustrate how important some of these factors are on the final result.

| Description                                 | Size   |
| ------------------------------------------- | ------ |
| Optimized                                   | 322MB  |
| one stage instead of three                  | 368MB  |
| w/o `NODE_ENV=production`                   | 409MB  |
| using `node:17` instead of `node:17-alpine` | 1.15GB |
