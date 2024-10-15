---
title: 'Zero Downtime Django Deployments with Multistep Database Changes'
date: 2024-10-12T15:58:00-07:00
tags:
  - Django
ShowToc: true
TocOpen: true
cover:
  # TODO: Create cover image
  image: 'posts/blue-green-deployment-pass.png'
draft: true
---

In the fast-paced world of software development, minimizing downtime during deployments is crucial. Blue-green deployments have emerged as a popular strategy to achieve this goal. However, they introduce challenges, especially when dealing with database changes. This article delves into what blue-green deployments are, why database changes can be tricky in this context, and how to navigate common change scenarios effectively in Django.

## Blue-Green Deployments

A blue-green deployment is a release management strategy that utilizes two separate production environments called "blue" and "green". At any given time, only one environment is live, serving all production traffic. Changes are deployed to the "green" environment, and after thorough testing, traffic is switched over from the "blue" to the "green" environment. This approach minimizes downtime and provides a quick rollback option by reverting traffic to the "blue" environment if issues occur.

## Database Changes Can Break Blue-Green Deployments

While blue-green deployments excel at application code deployments, database changes introduce complexity because both environments need to be compatible with the shared database. Incompatibilities can lead to data inconsistencies, errors and even downtime.

For example, suppose we want to remove the `rating` field from the following Django model.

```python
class Product(models.Model):
    name = models.CharField(max_length=255)
    rating = models.IntegerField()
```

If we remove the field from the database, we will break the blue environment if that environment still relies on it. In Django, this is particularly common because queries specify fields explicitly (e.g. `SELECT name, rating`) rather than using `SELECT *`. As a result, a simple `Product.objects.all()` query in the blue environment will fail since it attempts to fetch the non-missing `rating` field.

![Blue Green Deployment](/posts/blue-green-deployment7.png)

To mitigate this, we need to use `SeparateDatabaseAndState` to remove the field in multiple steps to ensure compatibility between the blue and green environments.

## Multistep Database Changes

The [`SeparateDatabaseAndState`](https://docs.djangoproject.com/en/5.1/ref/migration-operations/#django.db.migrations.operations.SeparateDatabaseAndState) migration operation allows us to separate changes to database and project state. We can use it to remove the `rating` field in two backwards-compatible steps (instead of removing it in one backwards-incompatible step). These steps need to be deployed separately to ensure compatibility between the blue and green environments.

- Step 1: Remove `rating` from the green environment project state without removing it from the database
- Step 2: Remove `rating` from the database

### Step 1: State changes

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
            field=models.IntegerField(null=True),
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
- We need to make `rating` nullable or give it a [db default](https://docs.djangoproject.com/en/5.1/ref/models/fields/#db-default), otherwise the green environment will break when trying to insert new `Product` rows. Making the field nullable is preferred because it consumes less storage. Note giving the field a [default](https://docs.djangoproject.com/en/5.1/ref/models/fields/#default) won't work because we need to generate the default at the database level, not the Python level.
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

Deploy the changes. The blue-green deployment will run the migration, spin up the green environment, switch traffic to it, and spin down the blue environment. Now our production environment is running without the `rating` field and we can safely remove it from the database in the next step.

### Step 2: Database changes

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
python manage.py makemigrations appname --empty -n remove_product_rating_from_db
```

- The `database_operations` list takes raw SQL. Run `sqlmigrate` before moving the backward-incompatible changes to the `state_operations` list in the first step to generate the SQL.

Deploy the changes. Now our production environment is running without the `rating` field in both the project state and the database.

## Common Database Changes

### Backward-Compatible

The following changes can be completed in a single deployment:

- Add a nullable field
- Add a field with a default: See [above](#add-a-field-not-nullable-and-without-a-default) for considerations when adding a field with a default
- Add a table
- Add / remove an index: Be sure to use the `CONCURRENTLY` option to avoid locking the table
- Removing a constraint

### Backward-Incompatible

The following changes must be completed in a multiple deployments:

#### Add a Field (not nullable and without a default)

- Step 1 (migration): Add the field to the database as nullable or with a [db default](https://docs.djangoproject.com/en/5.1/ref/models/fields/#db-default). Making the field nullable is preferred because it consumes less storage and doesn't require the database to lock the table to update existing rows, which can be slow for large tables and cause downtime. Note, some newer database versions update existing rows without locking the table, such as PostgreSQL 11+ which stores the default in the metadata and updates rows when it's convenient.
- Step 2 (migration): Make the field non-nullable or remove the db default

#### Remove a Field

- Step 1 (migration):
  - Make the field nullable or give it a [db default](https://docs.djangoproject.com/en/5.1/ref/models/fields/#db-default) (if not already)
  - Remove the field from the project state
- Step 2 (migration): Remove the field from the database

#### Remove a Table

- Step 1 (no migration): Remove all references to the table in the application code
- Step 2 (migration): Remove the table from the database

#### Add a Constraint

Popular constraints include check constraints, unique constraints, and `NOT NULL` constraints.

- Step 1 (no migration): Update your application code to ensure that it writes data compliant with the new constraint
- Step 2 (migration):
  - Clean up existing data in the database that violates the new constraint
  - Add the constraint to the database
