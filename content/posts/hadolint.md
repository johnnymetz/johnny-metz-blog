---
title: 'Using Hadolint, a Dockerfile linter, To Enforce Best Practices'
date: 2022-02-01T19:52:11-08:00
draft: true
---

Docker security is an important topic that doesn't get enough attention. A recent report by Aqua Security found that [50% of new Docker instances are attacked within 56 minutes](https://venturebeat.com/2021/06/28/aqua-security-50-of-new-docker-instances-attacked-within-56-minutes/) of being deployed.

Furthermore, misconfigured Docker containers can be slow, heavy and difficult to maintain leading to sluggish releases, high storage costs and frustrated developers. Docker problems can be devastating for any business and software teams need to put the time and energy in to alleviate these risks.

[Hadolint](https://github.com/hadolint/hadolint) is a Dockerfile linter that helps you build [best practice](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/) Docker images. I use it in all of my projects to ensure I'm creating small, secure, efficient and maintainable images.

## Introduction to Hadolint

Hadolint comes with a robust and easy to use CLI. You can [install it](https://github.com/hadolint/hadolint#install) on a variety on platforms, including macOS using `brew install hadolint`.

We'll use the following `Dockerfile` as an example, which can be used to run a Python [Django](https://www.djangoproject.com/) web server. On the surface, it looks fine but we'll see it has a lot of problems.

```dockerfile
FROM python
MAINTAINER johndoe@gmail.com
LABEL org.website="containiq.com"

RUN mkdir app && cd app

COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

CMD python manage.py runserver 0.0.0.0:80000
```

Let's run it through Hadolint:

```bash
$ hadolint Dockerfile
Dockerfile:1 DL3006 warning: Always tag the version of an image explicitly
Dockerfile:2 DL4000 error: MAINTAINER is deprecated
Dockerfile:4 DL3003 warning: Use WORKDIR to switch to a directory
Dockerfile:4 SC2164 warning: Use 'cd ... || exit' or 'cd ... || return' in case cd fails.
Dockerfile:6 DL3045 warning: `COPY` to a relative destination without `WORKDIR` set.
Dockerfile:7 DL3013 warning: Pin versions in pip. Instead of `pip install <package>` use `pip install <package>==<version>` or `pip install --requirement <requirements file>`
Dockerfile:8 DL3042 warning: Avoid use of cache directory with pip. Use `pip install --no-cache-dir <package>`
Dockerfile:8 DL3059 info: Multiple consecutive `RUN` instructions. Consider consolidation.
Dockerfile:10 DL3045 warning: `COPY` to a relative destination without `WORKDIR` set.
Dockerfile:12 DL3025 warning: Use arguments JSON notation for CMD and ENTRYPOINT arguments
```

Every violation takes on the following structure:

```
<LINE_NUMBER> <RULE_CODE> <SEVERITY_LEVEL>: <DESCRIPTION>
```

For example:

```
Dockerfile:1 DL3006 warning: Always tag the version of an image explicitly
```

### Rule Codes

A rule code is prefixed with either `DL` or `SC`. The `DL` prefix means the rule comes from Hadolint directly. The `SL` prefix means the rule comes from [SpellCheck](https://github.com/koalaman/shellcheck) which is a static analysis tool for shell scripts and comes with Hadolint out of the box. You can find the combined list of rules [here](https://github.com/hadolint/hadolint#rules).

Every rule has a dedicated documentation page that lists example code, rationale and other important details. See the dedicated page for `DL3006` [here](https://github.com/hadolint/hadolint/wiki/DL3006).

You can ignore one or more rules using the `--ignore RULECODE` option:

```
$ hadolint --ignore DL3013 --ignore DL3042 Dockerfile
```

You can also ignore rules within the `Dockerfile` inline. I prefer this approach because you can exclude rules codes on a per-line basis and it's more clear where the violation is actually happening.

```Dockerfile
# hadolint ignore=DL3013
RUN pip install --upgrade pip
```

Hadolint has an active open-source community and rules are added / updated on a regular basis.

### Severity Level

The severity level indicates how critical a violation is.

The CLI includes a `--failure-threshold` (abbreviated as `-t`) to exclude certain severity levels from causing a failure. For example, if we only want Hadolint to fail on `error` violations.

```
$ hadolint -t error Dockerfile
```

Note, violations from other severity levels will still be reported but they won't cause a failure.

If we don't agree with a rule code's severity level, we can easily change it using the `--<SEVERITY_LEVEL> RULECODE` option. For example, we can upgrade `DL3006` to `error` and downgrade `DL3045` to `info` using the following command):

```shell
$ hadolint --error DL3006 --info DL3045 Dockerfile
Dockerfile:1 DL3006 error: Always tag the version of an image explicitly
Dockerfile:7 DL3045 info: `COPY` to a relative destination without `WORKDIR` set.
```

### Label Linting

[Dockerfile labels](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#label) are an excellent tool for annotating your Docker images. Hadolint comes with some label validation options for ensuring your labels are set correctly.

The `--require-label LABELSCHEMA` option verifies that your labels follow to a specific format. You can see all acceptable format values [here](https://github.com/hadolint/hadolint#linting-labels).

```
$ hadolint --require-label maintainer:text --require-label org.website:url Dockerfile
Dockerfile:2 DL3049 info: Label `maintainer` is missing.
Dockerfile:3 DL3052 warning: Label `org.website` is not a valid URL.
```

The `--strict-labels` option verifies there are no extra labels outside of the ones sepcified in your label schema.

```
$ hadolint --require-label maintainer:text --strict-labels Dockerfile
Dockerfile:3 DL3050 info: Superfluous label(s) present.
```

### Configuration file

Manually passing options into every Hadolint run can be annoying and error-prone. Hadolint conveniently comes with configuration file support for storing all of your options in a single place. This file can live in a [variety of locations](https://github.com/hadolint/hadolint#configure) but I generally just put it in the repository's root as `.hadolint.yaml`.

```yaml
override:
  error:
    - DL3006
  info:
    - DL3045
label-schema:
  maintainer: text
  org.website: url
strict-labels: true
```

## Fix the Dockerfile

Working through each error one-by-one is a fantastic exercise for learning about Dockerfile best practices. As mentioned above, every rule has a very clear and well-documented documentation page. Give it a shot and revisit this post when you're done.

Now your file should look similar to this:

```dockerfile
FROM python:3.10
LABEL maintainer="johndoe@gmail.com"
LABEL org.website="https://www.containiq.com/"

WORKDIR /app

COPY requirements.txt ./
# hadolint ignore=DL3013
RUN pip install --upgrade --no-cache-dir pip && \
  pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

A few changes that need further explanation:

- We're tagging the `python` base image with the latest available Python minor version, which is currently `3.10`. We're not including the patch version (`3.10.2`) because Python patch versions are backwards compatible and generally include useful bug fixes.
- I generally like to use the `/app` working directory to keep my Docker images consistent but you can use any new or existing directory you want.
- We're ignoring `DL3013` because we want to download the latest version of `pip`. There's no need to pin it to a specific version.

## Integrations

Hadolint includes many convenient [integrations](https://github.com/hadolint/hadolint/blob/master/docs/INTEGRATION.md) for automatically running the linter throughout the development process. My favorites are:

- [VS Code](https://github.com/hadolint/hadolint/blob/master/docs/INTEGRATION.md#vs-code): run Hadolint directly in your editor
- [pre-commit](https://github.com/hadolint/hadolint/blob/master/docs/INTEGRATION.md#pre-commit): run Hadolint on every git commit
- [GitHub Actions](https://github.com/hadolint/hadolint/blob/master/docs/INTEGRATION.md#github-actions): run Hadolint in GitHub CI/CD

Integrations are crucial, especially in larger teams because some developers will forget to run the linter manually. I set them up immediately when I start a new Docker project.

## Conclusion

Hadolint is a terrific tool for building best practice Docker images. It gives you the peace of mind that your production containers are small, fast and free of any major security vulnerabilities. Run it through your Dockerfiles and see what improvements you can make.
