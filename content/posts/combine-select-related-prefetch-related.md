---
title: 'Optimize Django Query Performance by combining Select Related and Prefetch Related'
date: 2023-05-06T15:48:39-04:00
tags:
  - Python
  - Django
cover:
  image: 'covers/django-sonic.png'
ShowToc: true
draft: true
---

## Introduction

When building a Django application, one of the key challenges developers face is optimizing database query performance. Django provides two tools,`select_related` and `prefetch_related`, that reduce the number of database queries, and increase the performance of your application.

This blog post explores the power of these two methods and how to combine them to maximize your application's query performance.

My team at [PixieBrix](https://www.pixiebrix.com/) implemented these techniques and have seen a significant improvement in query performance and customer satisfaction.

## Select Related

[`select_related`](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#select-related) performs SQL join operations to include the fields of related models in the initial queryset. This method is useful when you have `ForeignKey` or `OneToOneField` relationships in your models. By using `select_related`, you can retrieve related objects in a single database query, rather than issuing separate queries for each related object.

For example, consider the following models for `Author` and `Book`:

```python
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
```

To fetch all books along with their authors, you can use `select_related`:

```python
books = Book.objects.select_related("author")
```

In this case, `select_related` performs a SQL join to include the books and their respective authors in a single database query.

## Prefetch Related

[`prefetch_related`](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#prefetch-related) reduces the number of queries required to fetch related objects. Unlike `select_related`, `prefetch_related` performs a separate query for each relationship, and does the "joining" in Python. This method is useful for `ManyToManyField` and reverse `ForeignKey` relationships.

For example, consider the following models for `Chapter` and `Book`:

```python
class Chapter(models.Model):
    title = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=100)
    chapters = models.ManyToManyField(Chapter)
```

To fetch all books along with their chapters, you can use `prefetch_related`:

```python
books = Book.objects.prefetch_related('chapters')
```

On top of the query to grab all book objects, `prefetch_related` issues a new query to grab all chapter objects, resulting in a total of two queries.

## Combining select related and prefetch related

In some cases, you may need to optimize queries that involve multiple levels of related objects. You can combine `select_related` and `prefetch_related` to reduce the number of queries required to fetch complex object relationships, regardless of the order in which they are applied.

### Select Related before Prefetch Related

Consider the following models for `Landmark`, `Hometown`, `Author` and `Book`:

```python
class Landmark(models.Model):
    name = models.CharField(max_length=100)

class Hometown(models.Model):
    name = models.CharField(max_length=100)
    landmarks = models.ManyToManyField(Landmark)

class Author(models.Model):
    name = models.CharField(max_length=100)
    hometown = models.ForeignKey(Hometown, on_delete=models.SET_NULL, null=True)

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
```

To fetch all books along with their authors, the authors' hometown and the hometowns' landmarks, you can use `select_related` before `prefetch_related`:

```python
books = (
    Book.objects
    .select_related('author__hometown')
    .prefetch_related('author__hometown__landmarks')
)
```

In this example, `select_related` performs two SQL joins to include the related author and hometown objects in a single query. `prefetch_related` will then fetch the associated landmarks for each hometown in a separate query, resulting in a total of two queries. Without the `select_related` optimization, this would have required four queries.

### Select Related after Prefetch Related

The [`Prefetch`](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#django.db.models.Prefetch) object allows you to define custom querysets for related objects, providing more control over how related objects are fetched. By using the `Prefetch` object, you can include `select_related` within `prefetch_related` to reduce the number of issued queries.

Consider the following models for `Editor`, `Chapter` and `Book`:

```python
class Editor(models.Model):
    name = models.CharField(max_length=100)

class Chapter(models.Model):
    title = models.CharField(max_length=100)
    editor = models.ForeignKey(Editor, on_delete=models.SET_NULL, null=True)

class Book(models.Model):
    title = models.CharField(max_length=100)
    chapters = models.ManyToManyField(Chapter)
```

Our application needs to fetch all books, their chapters and each chapter's editor in as few queries as possible. I commonly see developers do this using `prefetch_related` alone:

```python
books = Book.objects.prefetch_related("chapters__editor")
```

This works but it generates three individual queries.

You can use the `Prefetch` object to reduce the number of queries to just two:

```python
from django.db.models import Prefetch

chapters_with_editor_prefetch = Prefetch(
    lookup="chapters",
    queryset=Chapter.objects.select_related("editor"),
)
books = Book.objects.prefetch_related(chapters_with_editor_prefetch)
```

## Conclusion

By effectively combining `select_related` and `prefetch_related`, you can optimize database query performance in your Django application. These techniques help you minimize the number of queries allowing you to build more efficient, performant and scalable applications.
