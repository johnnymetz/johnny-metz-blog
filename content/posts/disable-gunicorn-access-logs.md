---
title: 'Disable Redundant Gunicorn Access Logs on Heroku'
date: 2024-11-25T12:00:00-08:00
tags:
  - Python
  - Heroku
  - Gunicorn
cover:
  image: 'covers/heroku-gunicorn.png'
ShowToc: true
---

When hosting an application on [Heroku](https://www.heroku.com/), managing logs efficiently is crucial for maintaining system health and keeping costs down. Heroku provides built-in logging for all incoming requests, but by default, [Gunicorn](https://gunicorn.org/), the Python HTTP server often used in Heroku deployments, also logs incoming requests. This duplication can clutter your logs, making them harder to parse and more expensive to store. Let's explore why this redundancy exists and how to fix it.

## Heroku Router Logs

Heroku's Router automatically logs all incoming HTTP requests, providing a wealth of data for monitoring and debugging your application. These logs are always enabled and include detailed information, such as the HTTP method and URL path of the request, the response status code, the client's IP address, and the request processing time (see [Heroku Router Log Format](https://devcenter.heroku.com/articles/http-routing#heroku-router-log-format)).

Because these logs are highly informative, they serve as a robust tool for observability, making other access logs superfluous.

## Gunicorn Access Logs

Gunicorn includes an option to log incoming requests using the [`accesslog`](https://docs.gunicorn.org/en/stable/settings.html#accesslog) setting. By default, this is set to `None`, meaning no access logs are generated. However, when deploying on Heroku, the [Python buildpack](https://github.com/heroku/heroku-buildpack-python) explicitly sets it to `'-'` using the `GUNICORN_CMD_ARGS` environment variable (see [source code](https://github.com/heroku/heroku-buildpack-python/blob/1416814a17252e1d656d3f60ee862ae1fa0495bb/spec/hatchet/profile_d_scripts_spec.rb#L19)), which logs to stdout.

This results in both Heroku Router logs and Gunicorn access logs being written to the same log stream, creating unnecessary duplication.

## Reducing Log Noise and Costs

You have a few options to remove the excess Gunicorn logs: discard them before they're ingested by your logging service or disable them entirely.

### Filter Logs at the Logging Service Level

If you use a logging service, you can filter out logs before they're processed or stored. Most services support filtering based on string or regex patterns:

- Datadog: [Exclusion Filters](https://docs.datadoghq.com/logs/log_configuration/indexes/#exclusion-filters)
- New Relic: [Drop Filter Rules](https://docs.newrelic.com/docs/logs/ui-data/drop-data-drop-filter-rules/)
- Sumo Logic: [Processing Rules](https://help.sumologic.com/docs/send-data/collection/processing-rules/)
- PaperTrail: [Log Filtering](https://www.papertrail.com/help/log-filtering/)

This approach is useful if you have a specific reason to keep some Gunicorn access logs while excluding others. However, in most cases, you'll want to remove all Gunicorn access logs, which is best done at the source.

### Disable Gunicorn Access Logs

If you want to completely eliminate Gunicorn access logs on Heroku, the most efficient solution is to disable them at the command line. This works because command-line arguments override the `GUNICORN_CMD_ARGS` environment variable, as stated in the [Gunicorn documentation](https://docs.gunicorn.org/en/latest/configure.html). In practice, this is done by updating your Procfile to explicitly disable the access log:

```
web: gunicorn myapp.wsgi --accesslog None
```

With this change, Gunicorn will stop logging incoming requests.

May your logs be clean and cost-effective.
