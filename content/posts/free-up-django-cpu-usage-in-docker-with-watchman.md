---
title: 'Free up Django CPU usage in Docker with Watchman'
date: 2021-12-21T23:27:56-08:00
tags:
  - Python
  - Django
  - Docker
draft: true
---

Adam Johnson's [Efficient Reloading in Django’s Runserver With Watchman - Adam Johnson](https://adamj.eu/tech/2021/01/20/efficient-reloading-in-djangos-runserver-with-watchman/) blog post describes how to use [watchman](https://github.com/facebook/watchman) in your Django project to make auto-reloads more CPU efficient. I highly recommend giving it a read. It's a no-brainer for every Django project to speed up your development process.

The tutorial explains how to install watchman on macOS with `brew install watchman` but does not explain how to install it in a Python docker container. Considering all of my Django projects are dockerized, I decided to figure it out.

First, visit the [watchman releases page](https://github.com/facebook/watchman/releases) on GitHub. Find the latest release that contains a linux binary. This binary should follow the following format: `watchman-vYYYY.MM.DD.00-linux.zip`. As of the writing of this post, that release is `v2021.12.06.00` (note, not all releases have the linux binary for some reason).

Next, hardcode the release version into your Dockerfile as an `ARG`.

```
ARG WM_VERSION=v2021.12.06.00
```

Lastly, install the binary. I got the installation instructions from the [watchman docs](https://facebook.github.io/watchman/docs/install.html#linux-and-macos).

```
RUN wget -nv https://github.com/facebook/watchman/releases/download/$WM_VERSION/watchman-$WM_VERSION-linux.zip && \
  unzip watchman-*-linux.zip && \
  cd watchman-*-linux && \
  mkdir -p /usr/local/{bin,lib} /usr/local/var/run/watchman && \
  cp bin/* /usr/local/bin && \
  cp lib/* /usr/local/lib && \
  chmod 755 /usr/local/bin/watchman && \
  chmod 2777 /usr/local/var/run/watchman && \
  cd .. && \
  rm -rf watchman-*-linux.zip watchman-*-linux
```

I implemented this in one of my larger Django projects and benchmarked CPU usage with `docker stats`. Before watchman, CPU usage was **3.5%**. After watchman, CPU usage was a mere **0.05%**.
