---
title: 'Check your Django Migrations on every commit'
date: 2021-05-08T12:10:47-07:00
tags:
  - Python
  - Django
  - Pre-commit
cover:
  image: 'covers/django-precommit.png'
---

Keeping your models in sync with your migrations is an important part of any Django app. My team and I frequently make changes to our models and we occassionally forget to create new migrations for those changes. This results in errors and data loss. Let's look at an easy way to ensure your models and migrations are **always** in sync:

We'll use a simple `Product` model.

```python
class Product(models.Model):
    name = models.CharField(max_length=255)
```

Let's say we want to add a `quantity` field.

```python {hl_lines=[3]}
class Product(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
```

At this point, we _should_ create a new migration using `python3 manage.py makemigrations`. However, let's say we forget, which is a common mistake, and we attempt to create a new product. This results in an error and the data is never added to the database.

```python
In [1]: from core.models import Product
In [2]: Product.objects.create(name="Headphones", quantity=3)
# OperationalError: table core_product has no column named quantity
```

It would be ideal to catch this bug earlier in the development cycle. We can do this using the `--check` flag on the `makemigrations` command, which will "Exit with a non-zero status if model changes are missing migrations".

```bash
$ python3 manage.py makemigrations --check
# Migrations for 'core':
#   core/migrations/0002_product_quantity.py
#     - Add field quantity to product
$ echo $?
# 1
```

Before Django 4.2.9, we'd also need the `--dry-run` flag, to prevent the migrations from actually being created (see [Django docs](https://docs.djangoproject.com/en/5.1/ref/django-admin/#makemigrations)).

`echo $?` prints the exit code of the last run command. As we can see from the output and the non-zero exit code, we're missing migrations.

We can automatically run this check before committing to version control using the popular [pre-commit](https://pre-commit.com/) framework.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-django-migrations
        name: Check django migrations
        entry: python3 manage.py makemigrations --check
        language: system
        types: [python] # hook only runs if a python file is staged
        pass_filenames: false
```

If we try to commit, we'll get an error.

```bash
$ git commit -m "Add quantity field to Product model"
# Check django migrations..................................................Failed
# - hook id: check-django-migrations
# - exit code: 1
#
# Migrations for 'core':
#   core/migrations/0002_product_quantity.py
#     - Add field quantity to product
```

Only after we create the required migration files will the check pass and the commit will go through.

```bash
$ git commit -m "Add quantity field to Product model"
# Check django migrations..................................................Passed
```

May your models always be in sync with your migrations.
