---
title: 'Clear up disk space with docker prune'
date: 2023-01-08T14:11:25-05:00
tags:
  - Docker
draft: true
---

<!-- https://docs.docker.com/config/pruning/ -->

Docker is platform for developing, shipping and running applications in isolated, lightweight, portable containers. It is a critical part of a developer's toolbelt. I use it everyday.

However, Docker consumes an enormous amount of disk space, especially if you work on many dockerized applications. Per the [Docker documentation](https://docs.docker.com/config/pruning/):

> Docker takes a conservative approach to cleaning up unused objects (often referred to as "garbage collection"), such as images, containers, volumes, and networks: these objects are generally not removed unless you explicitly ask Docker to do so. This can cause Docker to use extra disk space.

For example, a container is not automatically removed when it is stopped, unless it's started with the `--rm` flag.

Use the `docker system df` command to show docker disk usage. Note, [df](<https://en.wikipedia.org/wiki/Df_(Unix)>) stands for "disk free".

```bash
$ docker system df
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          31        2         12.86GB   12.41GB (96%)
Containers      2         2         63B       0B (0%)
Local Volumes   27        2         4.404GB   4.355GB (98%)
Build Cache     244       0         6.249GB   6.249GB
```

The "Active" column represents objects that are associated with running containers. You can see detailed information using the `--verbose` flag, such as which objects are active and how long they have been running.

Docker is eating up about 23.5 GB of disk space. 23 GB of that is reclaimable or unused. That's huge! Let's free that up.

## docker prune

Docker comes with a `prune` command to remove unused objects. It doesn't touch active objects. I use it with a few options:

```bash
docker system prune --all --force --volumes
```

The `--all` option removes all unused images, not just dangling images. A dangling image is one that is not tagged and is not referenced by any container. All images can be rebuilt or pulled from [Docker Hub](https://hub.docker.com/) so deleting them is fine.

The `--force` option bypasses the confirmation prompt.

The `--volumes` option instructs Docker to delete all unused volumes. This is the one option you need to be careful with. If you want to keep some volumes, you can do so using the `docker volume rm` command:

```
# Delete all volumes except one
docker volume rm $(docker volume ls -q | grep --invert-match 'volume-name')

# Delete all volumes except two or more
docker volume rm $(docker volume ls -q | grep --invert-match --extended-regexp 'volume-name1|volume-name2')
```

Let's run it:

```
$ docker system prune --all --volumes --force
Deleted Volumes:
demo-app_postgres_data
74c2f2d5dac8563407e55bad36183c962434d17ad76cffbcbf2d8aa4678352b9
...

Deleted Images:
untagged: python:latest
untagged: node:19-alpine
deleted: sha256:2ce4f03f420bf05ff5d798bb0fd6900278935328879cf598c9ee815322853b94
...

Deleted build cache objects:
ihpjhn3qh07x8nxg1ex5j1v8i
cwoa38utb7dg9ehcgegaj7p11
...

Total reclaimed space: 19.99GB
```

Now let

## Exclude objects from pruning

You have a few options to exclude objects from being cleaned up. Let's review them.

## Activate the object

One approach is to activate the object. As mentioned above, active objects are not pruned. You can see which objects are active via the `docker system df --verbose` command.

## Exclude by object name

You can filter objects using the object name. Unfortunately `docker system prune` does not support this filter so you'll need to use other Docker commands. For example, see how to delete all volumes except for one or more:

```bash
# Delete all volumes except one
docker volume rm $(docker volume ls -q | grep --invert-match 'volume-name')

# Delete all volumes except two or more
docker volume rm $(docker volume ls -q | grep --invert-match --extended-regexp 'volume-name1|volume-name2')
```

### Docker objects labels

[Docker object labels](https://docs.docker.com/config/labels-custom-metadata/) is a clever approach to protect volumes from being pruned.

Label objects in `docker-compose.yaml`:

```yaml
services:
  my_app:
    image: nginx
    labels:
      - 'keep'

volumes:
  my_volume:
    labels:
      - 'keep'
```

Prune objects except for those with the `keep` label:

```bash
docker system prune --all --force --volumes --filter "label!=keep"
```

In this example, neither `my_app` nor `my_volume` will be deleted.

Note, object labels are immutable. To modify labels you must recreate the object.

## Takeaways

### Clean up unused objects during development

Reduce the rate at which bloat accumulates by deleting unused objects while you're working.

Other tips:

- Use the `--rm` flag when starting a container, unless you need the container after it has been stopped, which should be rare at best. One of Docker's recommended practices is to [create ephemeral containers](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#create-ephemeral-containers), which means containers should be designed to be stopped and deleted.
- Use `docker compose down` instead of `docker compose stop`. Both commands stop running containers. The former also removes any associated networks. You can take `down` one step further and add the `--volumes` flag to prune all linked volumes.

### Monitor docker disk usage and prune often

Use the `docker system df` command to monitor Docker disk usage. If the total utilization is too high, run the prune command.

<!-- TODO: delete this -->

## Archive

Prune objects created more than 24 hours ago:

```
docker image prune -a --filter "until=24h"
```
