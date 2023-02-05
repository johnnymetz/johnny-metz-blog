---
title: 'Django Concurrency Basics'
date: 2023-01-29T16:19:18-05:00
tags:
  - Python
  - Django
draft: true
---

## Title

- Django + postgres + gunicorn + gevent
- Django Concurrency: Managing context specific data / state

## Notes

- Parallelize a Django application
- Gunicorn is based on the pre-fork worker model. This means that there is a central master process that manages a set of worker processes. The master never knows anything about individual clients. All requests and responses are handled completely by worker processes. -> https://docs.gunicorn.org/en/latest/design.html#server-model
  - The most basic and the default worker type is a synchronous worker class that handles a single request at a time.
  - The asynchronous workers available are based on Greenlets (via Eventlet and Gevent).
- Gevent: gevent is a coroutine-based Python networking library that uses greenlet to provide a high-level synchronous API on top of the libev or libuv event loop
  - Coroutines are computer program components that allow execution to be suspended and resumed
  - greenlets are lightweight coroutines for in-process sequential concurrent programming.
- GRequests allows you to use Requests with Gevent to make asynchronous HTTP Requests easily.
