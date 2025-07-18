---
title: "Stop Using Django's squashmigrations: There's a Better Way"
date: 2025-07-12T21:41:01-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
draft: true
---

Django's `squashmigrations` command promises to clean up your messy migration history. In reality? It's a nightmare of redundant operations, confusing dependency errors, and fragile multi-step deploys.

There's a better way to keep your migrations clean without the pain.

# ℹ️ What is `squashmigrations`?

[`squashmigrations`](https://docs.djangoproject.com/en/stable/topics/migrations/#squashing-migrations) is Django's built-in command for reducing migration bloat by combining many individual migration files for an app into a single, squashed migration that represents the same final schema. The main goals are to:

- Speed up database creation from scratch, by letting Django apply one consolidated migration instead of replaying every small step. This is especially notable during unit tests because Django creates a new test database from scratch for each test run.
- Simplify your project's migration history, making it easier to understand, maintain, and search through without sifting through dozens or hundreds of small incremental files.

# ⚠️ Why I Don't Use `squashmigrations`

`squashmigrations` isn't bad—it just solves problems I usually don't have. Worse, it creates its own problems:

## It often doesn't work well

For larger codebases with many migrations, it struggles to generate a clean squashed migration:

- It's not smart about optimizing out no-ops. For example, if you have a migration that creates a table or field and another that deletes it, the squashed migration will still include both operations.
- I've often run into `CircularDependencyError` trying to apply squashed migrations, which required manual editing to fix (the docs warn about this).

## Requires multiple coordinated deployments

The Django’s docs recommend splitting it into two deployments so old and new environments stay compatible, which is cumbersome and error-prone. You have to carefully coordinate releases to avoid breaking out-of-sync instances. What if I told you that you can do it all in one deploy?

## It preserves things I don't care about

squashmigrations is designed to keep:

- Full rollback history of every migration step.
- Detailed migration history (when each migration ran).
- Compatibility for environments that haven't applied all migrations yet.

I don't need any of that:

- I almost never roll back more than one deployment. Any rollback is usually immediate after deploy (a day or two at most), not months later.
- I don't care about the exact migration history. I have Git for that.
- I control all environments. There's no "in the wild" instance of my app lagging behind on migrations.

## Comparing the Two Approaches

| Feature                           | squashmigrations                        | Delete/Recreate Migrations                           |
| --------------------------------- | --------------------------------------- | ---------------------------------------------------- |
| Migration history preserved       | ✅ Yes                                  | ❌ No (resets to new baseline)                       |
| Downtime                          | ✅ None                                 | ✅ None (if schema matches and reset is coordinated) |
| Preserves existing data           | ✅ Yes                                  | ✅ Yes                                               |
| Supports out-of-sync environments | ✅ Yes                                  | ❌ No (must coordinate all environments)             |
| Resets migration bloat cleanly    | ⚠️ Kinda (needs cleanup)                | ✅ Very clean                                        |
| Easy to maintain                  | ❌ Needs testing, conflict resolution   | ✅ One-time reset                                    |
| Best for                          | Large production with many environments | Controlled deploys where you can coordinate          |
