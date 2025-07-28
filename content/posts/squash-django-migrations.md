---
title: "Stop Using Django's squashmigrations: There's a Better Way"
date: 2025-07-26T17:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

Squashing merges multiple database migrations into a single consolidated file to speed up database setup and tidy up history. Django's [`squashmigrations`](https://docs.djangoproject.com/en/stable/topics/migrations/#squashing-migrations) command promises to handle this, but it's error-prone and unnecessarily complex. A clean reset is faster and simpler.

## ⚠️ Why `squashmigrations` Falls Short

### Broken in Practice

In medium-to-large projects, I've consistently seen `squashmigrations` generate poor results, such as failing to optimize basic no-ops (like adding and deleting the same field) and even breaking migrations. The [official docs](https://docs.djangoproject.com/en/stable/topics/migrations/#squashing-migrations) acknowledge this:

> Squashing may result in migrations that do not run; either mis-optimized ... or with a `CircularDependencyError`, in which case you can manually resolve it.

Fixing these issues is tedious and not worth the hassle.

### Unnecessary Overhead

`squashmigrations` is designed for projects where you can't guarantee every environment is fully migrated — like open-source libraries or self-managed installs. But if you control all environments, which is generally the case, that flexibility becomes a burden. As the [official docs](https://docs.djangoproject.com/en/stable/topics/migrations/#squashing-migrations) outline, it requires a multi-step deployment and finicky migration tweaks to avoid breaking partially migrated environments.

## ✅ Clean Reset Instead

Skip the squash. Reset the migrations from scratch in one easy deployment.

**1️⃣ Ensure all environments are fully migrated**

Every environment must have applied all existing migrations. Unapplied migrations will be lost, which will break your app.

I highly recommend running migrations automatically during deployments. It simplifies this step and keeps environments consistent.

**2️⃣ Delete all migration files**

```bash
find . -path "*/migrations/*.py" -not -name "__init__.py" -exec git rm {} \;
```

**3️⃣ Generate fresh migrations**

```bash
python manage.py makemigrations
```

This creates a new `0001_initial.py` for each app. In projects with cross-app dependencies, some apps may get a `0002_initial.py` or higher.

**4️⃣ Re-add data migrations**

Neither `squashmigrations` nor resets preserve [data migrations](https://docs.djangoproject.com/en/5.2/topics/migrations/#data-migrations), including `RunPython` and `RunSQL` operations. Re-add them as needed:

```python
migrations.RunPython(create_default_permissions)
```

**5️⃣ Temporarily disable automatic migrations during deployments**

This prevents Django from applying the new migrations before the reset is complete. If you skip this step, you'll hit `django.db.migrations.exceptions.InconsistentMigrationHistory`.

**6️⃣ Reset migration history after deployment**

Create a temporary script that clears the old migration history and fakes the new migrations as applied:

```python
from django.core.management import call_command
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("TRUNCATE TABLE django_migrations")

call_command("migrate", fake=True)
```

Run this script in each environment after deploying the new migrations.

**7️⃣ Re-enable automatic migrations during deployments**

Once the reset is complete, turn auto-migrations back on to resume normal behavior.

That's it. Schema untouched. History clean. Zero downtime.

## 🆚 Comparison

|                                              | `squashmigrations`                                        | Clean Reset                                            |
| -------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------ |
| **Migration cleanup**                        | ❌ Broken                                                 | ✅ Perfect                                             |
| **Effort required**                          | ❌ High — migration fixes / tweaks, multi-step deployment | ✅ Low — simple one-step deployment                    |
| **Supports partially migrated environments** | ✅ Yes                                                    | ❌ No — requires all environments to be fully migrated |
| **Downtime**                                 | ✅ None                                                   | ✅ None                                                |
| **Best for**                                 | Shared or open-source projects                            | Internal projects with controlled environments         |

When you own the pipeline, skip the squash — a clean reset does it better.
