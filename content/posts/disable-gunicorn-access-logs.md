---
title: 'Disable Gunicorn Access Logs on Heroku'
date: 2024-11-17T17:08:22-08:00
tags:
  - Python
  - Heroku
  - Gunicorn
cover:
  image: 'covers/heroku-gunicorn.png'
ShowToc: true
---

When hosting an application on Heroku, managing logs efficiently is crucial for maintaining system health and keeping costs down. Heroku provides built-in logging for all incoming requests, but by default, [Gunicorn](https://gunicorn.org/), the Python WSGI HTTP server often used in Heroku deployments, also logs incoming requests. This duplication can clutter your logs, making them harder to parse and more expensive to store. Let's explore why this redundancy exists and how to disable it for a cleaner, cost-effective logging setup.

## Heroku Router Logs: Informative and Unavoidable

Heroku automatically logs all incoming HTTP requests via its router. These logs are always enabled and provide a wealth of data for monitoring system health (see the [Heroku Router Log Format](https://devcenter.heroku.com/articles/http-routing#heroku-router-log-format) documentation), including:

- HTTP method and path
- Response status code
- Request timing and latency
- Dyno handling the request
- Request ID for tracing

Heroku even has a newer [Router 2.0](https://devcenter.heroku.com/articles/heroku-runtime-router-2-0) (currently in beta), which includes even more data and additional features. Since Heroku logs cannot be disabled, we rely on them for critical observability, making other access logs largely redundant.

## Gunicorn Access Logs: Redundant by Default

Gunicorn also has the ability to log incoming requests via the [`--accesslog`](https://docs.gunicorn.org/en/stable/settings.html#accesslog) setting. By default, this is set to None, meaning no access logs are generated. However, when deploying on Heroku, the [Python buildpack](https://github.com/heroku/heroku-buildpack-python) explicitly enables Gunicorn access logs by setting `--accesslog='-'` (see [source code](https://github.com/heroku/heroku-buildpack-python/blob/1416814a17252e1d656d3f60ee862ae1fa0495bb/spec/hatchet/profile_d_scripts_spec.rb#L19)), which logs to stdout.

This results in both Heroku router logs and Gunicorn access logs being written to the same log stream, creating unnecessary duplication.

## Reducing Log Noise and Costs

We have a few options to address this redundancy: excluding logs before they're ingested by our logging service or disabling Gunicorn access logs entirely.

### Filter Logs at the Logging Service Level

If you use a logging service like [PaperTrail](https://www.papertrail.com/) or [Sumo Logic](https://www.sumologic.com/), you can filter out the Gunicorn access logs before they're stored or processed. Most services support filtering based on string or regex patterns:

- PaperTrail: [Log Filtering Documentation](https://www.papertrail.com/help/log-filtering/)
- Sumo Logic: [Processing Rules](https://help.sumologic.com/docs/send-data/collection/processing-rules/)

This approach is useful if you have a specific reason to keep some Gunicorn access logs while excluding others. However, in most cases, you'll likely want to completely disable Gunicorn access logs, as described below.

### Disable Gunicorn Access Logs

If you’re looking to eliminate Gunicorn access logs entirely, the most efficient solution is to disable them at the source. We can achieve this by disabling the access log in the command line because the command line takes precedence over the `GUNICORN_CMD_ARGS` environment variable (according to the [Gunicorn docs](https://docs.gunicorn.org/en/latest/configure.html)). On Heroku, this means updating your `Procfile`:

```
web: gunicorn myapp.wsgi --access-logfile None
```

Gunicorn will now no longer log incoming requests, leaving you with the Heroku router logs as the sole source of truth for HTTP traffic.

May your logs be less noisy, your costs be lower, and your monitoring more effective.
