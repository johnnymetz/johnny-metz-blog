---
title: 'Mastering Django Blue-Green Deployments: Handling Database Migrations'
date: 2024-10-12T15:58:00-07:00
tags:
  - Django
ShowToc: true
draft: true
---

In the fast-paced world of software development, minimizing downtime during deployments is crucial. Blue-green deployments have emerged as a popular strategy to achieve this goal. However, they introduce challenges, especially when dealing with database migrations. This article delves into what blue-green deployments are, why database migrations can be tricky in this context, and how to navigate common migration scenarios effectively in Django.

## Blue-Green Deployments

A blue-green deployment is a release management strategy that utilizes two separate production environments called "blue" and "green". At any given time, only one environment is live, serving all production traffic. Changes are deployed to the "green" environment, and after thorough testing, traffic is switched over from the "blue" to the "green" environment. This approach minimizes downtime and provides a quick rollback option by reverting traffic to the "blue" environment if issues occur.

## Database Migrations Break Blue-Green Deployments

While blue-green deployments excel at application code deployments, database migrations introduce complexity because both environments need to be compatible with the shared database. Incompatibilities between versions can lead to errors or data inconsistencies when switching traffic.

For example, suppose we want to remove the `rating` field from the following Django model.

```python
class Product(models.Model):
    name = models.CharField(max_length=255)
    rating = models.IntegerField()
```

If the green environment removes the field, this will break the blue environment if the blue environment relies on it. This is often the case in Django because "fetch all fields" queries explicitly list the fields (e.g. `SELECT name, rating`), instead of using `SELECT *`. So a simple `Product.objects.all()` query will break in the blue environment because the query will try to fetch the `rating` field, which no longer exists.

To mitigate this, we need to use `SeparateDatabaseAndState` to remove the field in stages to ensure compatibility between the blue and green environments.

## Handling Database Migrations in Blue-Green Deployments

The [`SeparateDatabaseAndState`](https://docs.djangoproject.com/en/5.1/ref/migration-operations/#django.db.migrations.operations.SeparateDatabaseAndState) migration operation allows us to separate changes to database and project state. We can use it to remove the `rating` field in two backwards-compatible migrations (instead of removing it in one backwards-incompatible migration):

- Migration 1: Remove `rating` from the green environment project state without removing it from the database
- Migration 2: Remove `rating` from the database

### Migration 1: State changes

```python
# 0002_remove_product_rating_from_state.py
class Migration(migrations.Migration):
    dependencies = [
        ("appname", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="rating",
            field=models.IntegerField(db_default=0),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="product",
                    name="rating",
                ),
            ],
            database_operations=[],
        ),
    ]
```

A few notes about creating and verifying the migration:

- Start by removing the `rating` from the model definition and the application code.
- Create the migration by running the `makemigrations` command. Then move all backward-incompatible changes to the `state_operations` list, which is just the `RemoveField` operation in this case.
- We need to give `rating` a [db default](https://docs.djangoproject.com/en/5.1/ref/models/fields/#db-default) or make it nullable, otherwise the green environment will break when trying to insert new `Product` rows. Note giving the field a [default](https://docs.djangoproject.com/en/5.1/ref/models/fields/#default) won't work because we need to generate the default at the database level, not the Python level.
- Verify the migration issues the expected SQL by running the following command:

```bash
python manage.py sqlmigrate appname 0002_remove_product_rating_from_state
```

- Verify the `rating` field has been removed from the project state by running the following query in the Django shell:

```python
Product.objects.all().query

# Before the release:
# SELECT name, rating FROM product

# After the release:
# SELECT name FROM product
```

Deploy the changes. The blue-green deployment will run the migration, spin up the green environment, switch traffic to it, and spin down the blue environment. Now our production environment is running without the `rating` field and we can safely remove it from the database in the next migration.

### Migration 2: Database changes

```python
# 0003_remove_product_rating_from_db.py
class Migration(migrations.Migration):
    dependencies = [
        ("appname", "0002_remove_product_rating_from_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE product "
                        "DROP COLUMN rating;"
                    ),
                ),
            ],
        ),
    ]
```

A few notes about creating and verifying the migration:

- Start by creating an empty migration file:

```bash
python manage.py makemigrations appname --empty -n 0003_remove_product_rating_from_db
```

- The `database_operations` list takes raw SQL. Run `sqlmigrate` before moving the backward-incompatible changes to the `state_operations` list in the first migration to generate the SQL.

Deploy the changes. Now our production environment is running without the `rating` field in both the project state and the database.
