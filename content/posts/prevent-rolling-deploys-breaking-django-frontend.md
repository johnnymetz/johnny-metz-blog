---
title: 'Prevent Rolling Deploys From Breaking Your Django Frontend'
date: 2026-11-15T12:00:00-08:00
tags:
  - Django
  - DevOps
  - Performance
  - Caching
ShowToc: true
summary: "During a rolling deploy, new HTML can ask an old server for files it doesn't have. Fix it in Django with shared storage and a CDN."
draft: true
---

My team's Django app serves a React SPA. Django renders the HTML shell, and [WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html) served the JavaScript and CSS from the same app servers:

```python
STORAGES = {
    # ...
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

That mostly worked while our deploys switched all traffic to the new release at once. When we moved to rolling deploys, old and new releases overlapped for minutes instead of seconds, and some users got a blank page during every deploy. The problem is called [version skew](https://www.industrialempathy.com/posts/version-skew/): the code in the browser and the code on the server come from different releases. It's the same kind of problem [multistep database changes]({{< relref "multistep-database-changes" >}}) solve for your schema, this time with static files. The fix for zero-downtime deploys is to decouple static files from the app servers entirely.

## Version Skew in a Rolling Deploy

A rolling deploy replaces servers a few at a time, so old and new releases serve traffic side by side for several minutes. The load balancer routes every request independently.

Bundlers like webpack and Vite name each file after a hash of its contents, like `main.3f9a1c.js`. That's cache busting for free: browsers can cache a file forever, and every build that changes it gives it a new name. Call them `main.old.js` and `main.new.js`. Each server only has its own release's files:

```mermaid
sequenceDiagram
  participant Browser
  participant New as New server
  participant Old as Old server
  Browser->>New: GET /app (load balancer picks a new server)
  New-->>Browser: HTML that references main.new.js
  Browser->>Old: GET main.new.js (load balancer picks an old server)
  Old-->>Browser: 404
  Note over Browser: Chunk fails to load, blank page
```

The reverse fails the same way: old HTML asks a new server for `main.old.js`.

This isn't just an SPA problem. If you use Django's `ManifestStaticFilesStorage` (WhiteNoise's storage builds on it), your own CSS and JavaScript get hashed names too. So server-rendered templates and [htmx](https://htmx.org/) apps get the same 404 when new HTML asks an old server for `styles.new.css`.

Open tabs are the hardest case. With [code splitting](https://developer.mozilla.org/en-US/docs/Glossary/Code_splitting), the app downloads parts of its code only when the user needs them, so a tab opened before the deploy requests `chunk.old.js` long after every old server is gone.

The problem is common enough that [Vercel](https://vercel.com/docs/skew-protection) and [Netlify](https://www.netlify.com/blog/introducing-netlify-skew-protection) built skew protection into their hosting: they keep old deployments alive and route each page's requests to the deployment that served it. That only helps apps they host, so when Django serves your SPA, the fix is up to you.

## Fixes That Don't Work on Their Own

- **Sticky sessions.** The load balancer pins each browser to one server with a cookie. That makes the bug rarer, not gone: a deploy replaces the server you're pinned to, so you get re-pinned to a server from the other release, and open tabs still ask new servers for old files.
- **Blue-green (atomic) deploys.** This is what we had before: start a full new fleet, then switch all traffic at once. Errors were rare, but open tabs still broke after the switch. And while both fleets ran, each held its own database connections, which pushed us up against our database's connection limit on every deploy.
- **Reloading when a chunk fails to load.** Catch the error (`ChunkLoadError` in webpack, `vite:preloadError` in Vite) and reload the page. It's a good safety net for flaky networks, but it throws away the user's state, and mid-rollout the reload can land on the wrong server again.
- **A CDN in front of the app servers.** [WhiteNoise's docs](https://whitenoise.readthedocs.io/en/stable/django.html#use-a-content-delivery-network) recommend it, and it gets close. But a cache miss for `main.new.js` still goes to whichever server the load balancer picks, and CloudFront [caches that 404](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HTTPStatusCodes.html) for 10 seconds by default, for everyone behind that cache.

The CDN isn't the problem. Where the files live is.

## Keep Every Build's Files in Shared Storage

Take static files off the app servers. Every release uploads its files to shared storage: one bucket that every release writes to and the CDN reads from, which outlives any single release. Two rules make it work:

1. Upload in a CI/CD release step that runs before any new server takes traffic, so new HTML never references a file that isn't there yet.
2. Keep old files as long as anything might still request them, so old HTML and open tabs always find theirs.

```mermaid
flowchart LR
  Browser -->|HTML + API| App[Django app servers]
  Browser -->|static files| CDN[CDN edge]
  CDN -->|cache miss| Bucket[(Storage bucket)]
  Release[Release step: collectstatic] -->|before new servers take traffic| Bucket
```

Content-hashed names pay off here. A file that didn't change keeps its name across releases, so it doesn't need re-uploading and browsers keep it cached. Per-release folders (`/static/<release>/main.js`) also work with shared storage, but every deploy changes every URL, so users re-download everything.

Deleting old files safely is harder than it looks. An S3 [lifecycle rule](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html) expires objects by upload age. With the setup below, an unchanged file is uploaded once and never again, so an age-based rule would eventually delete files the current build still uses. A safe cleanup keeps every file that recent releases reference and deletes the rest after a grace period. We skipped that and keep everything. For us that costs pennies a month; a site with more or larger files will pay more, but storage is cheap.

## The Django Side

A small storage class, plus `STATIC_URL` as the switch:

```python
# config/storage.py
from storages.backends.s3 import S3ManifestStaticStorage


class StaticStorage(S3ManifestStaticStorage):
    def stored_name(self, name):
        # The bundler already hashed these files, so skip Django's manifest (see below)
        if name.startswith("frontend/"):
            return name
        return super().stored_name(name)


# settings.py
import os
from urllib.parse import urlparse

STATIC_URL = os.environ["STATIC_URL"]  # CDN root "https://static.example.com/" or "/static/"
STATICFILES_DIRS = [("frontend", BASE_DIR / "frontend" / "dist")]  # bundler output

STORAGES = {  # Django's defaults
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Absolute STATIC_URL: upload to the bucket and serve from the CDN.
# Relative: Django's defaults, so local development needs no bucket.
if cdn_domain := urlparse(STATIC_URL).netloc:
    STORAGES["staticfiles"] = {
        "BACKEND": "config.storage.StaticStorage",  # the class above
        "OPTIONS": {
            "bucket_name": os.environ["STATIC_BUCKET_NAME"],  # collectstatic uploads here
            "custom_domain": cdn_domain,  # link to the CDN, not S3
        },
    }
```

`S3ManifestStaticStorage` comes from [django-storages](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html). It ties you to the S3 API, not to AWS: [S3-compatible storage](https://django-storages.readthedocs.io/en/latest/backends/s3_compatible/index.html) like Cloudflare R2 works too.

Add [collectfasta](https://github.com/jasongi/collectfasta) as well. Stock [`collectstatic`](https://docs.djangoproject.com/en/6.1/ref/contrib/staticfiles/#collectstatic) decides what to upload by file modification time, and a fresh CI build gives every file a new one, so it re-uploads everything, one file at a time. collectfasta compares content hashes instead and uploads in parallel, so a typical deploy uploads only the files that changed, in seconds instead of over an hour. List it before `django.contrib.staticfiles` in `INSTALLED_APPS` (it replaces the `collectstatic` command) and use its `Boto3ManifestMemoryStrategy`. Start with `COLLECTFASTA_THREADS = 10`: that matches boto3's default connection pool and avoids "Connection pool is full" warnings.

### The Manifest Is Shared Too

That `stored_name` override fixes one Django-specific gotcha. With S3 storage, the [`ManifestStaticFilesStorage`](https://docs.djangoproject.com/en/6.1/ref/contrib/staticfiles/#manifeststaticfilesstorage) manifest, `staticfiles.json`, lives in the bucket too, and every deploy overwrites it. Loaders like [django-webpack-loader](https://github.com/django-webpack/django-webpack-loader) and [django-vite](https://github.com/MrBin99/django-vite) turn bundle names into URLs through that manifest. If a worker on an old server restarts mid-deploy, it loads the new manifest, can't find its old bundle's name, and raises `Missing staticfiles manifest entry`: a 500. Bundler output is already hashed, so the override serves it by its own names and never asks the manifest. Django's own files still go through it, which is safe as long as a release doesn't delete a file that old templates still reference.

## Serving It From CloudFront

We already ran CloudFront for another asset domain, so we reused it. Any CDN that can serve a bucket works, since Django only sees `STATIC_URL`. The settings worth getting right:

- **Private bucket.** Block public access and let only the distribution read it, with [Origin Access Control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html).
- **Compression and edge caching.** Turn on compression and use the managed [`CachingOptimized`](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html#managed-cache-caching-optimized) policy, which caches Brotli and gzip versions at the edge.
- **Immutable browser caching.** Serve hashed files with `Cache-Control: public, max-age=31536000, immutable` so repeat visits skip revalidation. Keep unhashed files, like Vite's `public/` folder, on a short TTL. The cache policy only controls the edge, so set this header on the objects or with a response headers policy.
- **CORS.** Browsers fetch cross-origin fonts and JavaScript modules (Vite's output) with CORS, so add the headers with a [managed response headers policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-response-headers-policies.html).
- **No invalidations.** Changed content always gets a new hashed name, so a deploy never has to purge the cache.

## What's Next

Infrastructure as code. Defining the bucket, distribution, and DNS records in a tool like Terraform makes every environment identical and every change reviewable.

The short version: upload every build's files to shared storage before the release takes traffic, keep them while anything might still need them, and let the CDN do the rest.
