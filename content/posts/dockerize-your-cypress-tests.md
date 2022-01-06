---
title: 'Dockerize Your Cypress Tests'
date: 2022-01-10T21:08:44-08:00
tags:
  - Docker
  - Cypress
draft: true
---

<!-- - [Cypress Running in a Docker Container & Viewable with a VNC Client](https://spin.atomicobject.com/2021/10/14/cypress-running-docker-container/)
- [Run Cypress with a single Docker command](https://www.cypress.io/blog/2019/05/02/run-cypress-with-a-single-docker-command/)
- [Running GUI applications using Docker for Mac - Sourabh](https://sourabhbajaj.com/blog/2017/02/07/gui-applications-docker-mac/)
- [Using Docker to run your Cypress tests](https://www.mariedrake.com/post/using-docker-to-run-your-cypress-tests) -->

UI testing is a critical part of any modern web application. My favorite UI testing framework is [Cypress](https://docs.cypress.io/guides/overview/why-cypress).

I like to dockerize my entire application so I can run it on anywhere and Cypress is no exception. Let's take a look at how to achieve this.

## Run Cypress on host machine

First, let's see how to run Cypress on your host machine. Cypress includes two major commands: `cypress run` and `cypress open`
