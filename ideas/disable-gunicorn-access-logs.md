## Titles

- Disable redundant Gunicorn access logs on Heroku

## ChatGPT

Write a blog post titled "Disable redundant Gunicorn access logs on Heroku".

- Explain that Heroku logs all incoming requests, see docs: https://devcenter.heroku.com/articles/http-routing#heroku-router-log-format. The logs are very informative. We have various monitors that checks these logs to determine the health of the system (e.g. check for a spike in 500 errors). Heroku is coming out with a "Router 2.0" (which is currently in beta), which has a slightly different log format, see docs: https://devcenter.heroku.com/articles/heroku-runtime-router-2-0. Note Heroku logs can't be disabled.

Gunicorn also has the ability to log incoming requests via the [`--accesslog`](https://docs.gunicorn.org/en/stable/settings.html#accesslog) setting. The setting defaults to `None` which disables the access log. However, the Python Heroku buildpack (https://github.com/heroku/heroku-buildpack-python) sets `--access-logfile='-'` which logs to stout. See in source code: https://github.com/heroku/heroku-buildpack-python/blob/1416814a17252e1d656d3f60ee862ae1fa0495bb/spec/hatchet/profile_d_scripts_spec.rb#L19. Can confirm this by execing into a dyno:

```bash
$ heroku run bash
$ echo $GUNICORN_CMD_ARGS
--access-logfile -
```

- Both the Heroku router logs and Gunicorn access logs are redundant. Let's disable one of them so our logs are less noisy and to reduce costs.
- If you're using a logging service like PaperTrail or Sumo Logic, one solution is to filter out the logs at the logging service level. This allows you to specify a string or regex pattern to filter out logs.
  - Every service I've seen supports this:
    - PaperTrail: https://www.papertrail.com/help/log-filtering/
    - Sumo Logic: https://help.sumologic.com/docs/send-data/collection/processing-rules/
  - However, a much cleaner solution is to disable the Gunicorn access logs altogether.
- Per the [Gunicorn docs](https://docs.gunicorn.org/en/latest/configure.html), we can override `GUNICORN_CMD_ARGS` settings via the gunicorn CLI. On Heroku, we can do this in the Procfile:

```
web: gunicorn gettingstarted.wsgi --access-logfile None
```

Done. May your logs to be less noisy and your costs be lower.
