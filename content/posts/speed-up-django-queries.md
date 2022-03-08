---
title: 'Speed Up Django Queries'
date: 2022-03-03T12:49:00-08:00
tags:
  - Python
  - Django
draft: true
---

<!-- https://www.jooq.org/sakila -->
<!-- https://docs.djangoproject.com/en/4.0/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python -->
<!-- https://stackoverflow.com/questions/27116770/prefetch-related-for-multiple-levels -->
<!-- https://stackoverflow.com/questions/31237042/whats-the-difference-between-select-related-and-prefetch-related-in-django-orm -->

Database access optimization is the most difficult topic in the Django web framework. The [docs](https://docs.djangoproject.com/en/4.0/topics/db/optimization/#database-access-optimization) list many great tips. Here are a few more that are equally as important.

## Understand select_related vs. prefetch_related

Per the [Django docs](https://docs.djangoproject.com/en/4.0/ref/models/querysets/#prefetch-related):

> select_related works by creating an SQL join and including the fields of the related object in the SELECT statement. For this reason, select_related gets the related objects in the same database query. prefetch_related, on the other hand, does a separate lookup for each relationship, and does the ‘joining’ in Python.

In summary, use `select_related` to fetch one-to-one or one-to-many (1:n) relationships. Use `prefetch_related` to fetch many-to-one and many-to-many.

Let's look at an example:

```python
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product)
```

| QuerySet                                      | Relationship description   | DB hits |
| --------------------------------------------- | -------------------------- | ------- |
| `Order.objects.select_related("customer")`    | An order has one customer  | 1       |
| `Customer.objects.prefetch_related("orders")` | A customer has many orders | 2       |
| `Order.objects.prefetch_related("products")`  | An order has many products | 2       |
| `Product.objects.prefetch_related("order")`   | A product has many orders  | 2       |

Note, `prefetch_related` can be used in place of `selected_related`, e.g. `Order.objects.prefetch_related("customer")`, but this incurs a penalty of an extra db hit.

We can also

```
.prefetch_related("field1__field2")
```

## Do as much work in the database as possible

The documentation quickly glances over this in the [Do database work in the database rather than in Python](https://docs.djangoproject.com/en/4.0/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python) section.

Let's say I want to fetch all customer last names and their respective countries.

I can write the following query using `select_related()`.

```python
customers = [
  (customer.last_name, customer.address.city.country)
  for customer in Customer.objects.select_related("address__city__country")
]
```

However, it's much faster to do this in the database:

```python
customers = Customer.objects.values_list("last_name", "address__city__country")
```
