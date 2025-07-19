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

Squashing migrations merges multiple database migrations into one consolidated schema to speed up database setup and simplify the migration history. Django's [`squashmigrations`](https://docs.djangoproject.com/en/stable/topics/migrations/#squashing-migrations) command promises to do this, but it's fragile and overcomplicated. A clean reset of your migrations is often better.

## ⚠️ What's wrong with `squashmigrations`

**Bad results**: In real-world projects, I've found it fails to optimize no-ops (like adding then deleting a field) and produces migrations that trigger `CircularDependencyError` because it can't handle model interdependencies, requiring tedious manual cleanup.

**Unnecessary complexity for fully controlled environments**: `squashmigrations` is designed to support partially migrated instances, which makes sense for open source projects or self-hosted deployments. But when you fully control all environments, which is the case for most apps, that flexibility adds unnecessary friction. It forces coordinated multi-step rollouts and fragile manual edits to keep migrations in sync.

## ✅ Resetting Migrations

I skip the squash entirely and just reset the migrations from scratch.

Here are the steps:

**1️⃣ Delete all existing migration files**

```bash
find . -path "*/migrations/*.py" -not -path "./venv/*" -not -name "__init__.py" -delete
```

**2️⃣ Recreate fresh migration files**

```bash
python manage.py makemigrations
```

This generates a new `0001_initial.py` for each app that reflects the current schema.

**3️⃣ Re-add any necessary seed data**

Any `RunPython` or `RunSQL` operations won't be auto-recreated. We need to add these back manually so new environments still get the required initial data, such as default groups or permissions.

Any `RunPython` or `RunSQL` operations won't be auto-recreated. This is true for both a clean reset and `squashmigrations` — in both cases, Django requires you to manually copy the functions into the new migration file so they don't get lost.

```python
migrations.RunPython(seed_default_groups)
```

**4️⃣ Disable automatic migrations on deployment temporarily**

If your deployment script runs migrate automatically (which I recommend it does), disable that step for this deploy. We'll re-enable it after the reset.

**5️⃣ Reset migration history in all instances**

Clear the recorded migration history:

```sql
TRUNCATE TABLE django_migrations;
```

Fake-apply the new initial migration, which just marks the new migrations as applied without actually running them:

```bash
python manage.py migrate --fake
```

**6️⃣ Re-enable automatic migrations on deployment**

Done. Your DB schema is untouched. Your migration history is clean. Your app continues serving traffic with zero downtime.

## Comparing the Two Approaches

|                                       | `squashmigrations`                                                     | Clean Reset                                 |
| ------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------- |
| **Migration cleanup**                 | ⚠️ Poor                                                                | ✅ Excellent                                |
| **Manual edits required **            | ❌ Many                                                                | ✅ Minimal                                  |
| **Breakage risk**                     | ❌ High: `CircularDependencyError` is common and required manual edits |
| **Deployment complexity**             | ❌ Requires 2 coordinated deployments                                  | ✅ Single coordinated deployment            |
| **Supports out-of-sync environments** | ✅ Yes — built to handle partially migrated environments               | ❌ No — all environments must reset in sync |
|                                       |
| **Best for**                          | Projects where you don't control all environments                      | Projects where you control all environments |
