---
title: 'Context Manager Depth'
date: 2023-01-22T19:20:53-05:00
tags:
  - Python
  - Django
draft: true
---

## Title

- Enable
- Django Concurrency: Managing context specific data / state

## Terminology

- Thread local data
- Context local state

Thread local data: data whose values are thread specific ([docs](https://docs.python.org/3/library/threading.html#thread-local-data))

Use case: need data unique to each thread

Thread-local data storage is a mechanism in multi-threaded programming that allows data to be stored and accessed in a way that is private to each thread.

## Objects

- https://docs.python.org/3/library/threading.html#threading.local
- https://docs.python.org/3/library/contextvars.html#contextvars.ContextVar
- https://www.gevent.org/api/gevent.local.html
- https://www.gevent.org/api/gevent.contextvars.html

Context variables are like thread-local variables, just more inconvenient to use. They were designed to work around limitations in asyncio and are rarely needed by greenlet-based code.

If used in the multi threading projects, contextvars and thread local would behave pretty much the same. But with coroutines, using thread local is dangerous and contextvars is the aid.

## Use Cases

- Fire a signal only once
- Ensure code block is NOT run in a transaction
- Override a global variable or setting
- Temporarily disable database writes

## Links

- https://superfastpython.com/thread-local-data/
- https://stackoverflow.com/questions/68856006/is-there-any-reason-to-use-python-threading-local-rather-than-a-contextvar-in
- https://valarmorghulis.io/tech/201904-contextvars-and-thread-local/
-
