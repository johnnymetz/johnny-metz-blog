---
title: 'Optimize Django Query Performance by combining select_related and prefetch_related'
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

When building a Django application, one of the challenges developers face is optimizing database query performance. Django provides two tools,`select_related` and `prefetch_related`, that reduce the number of database queries, and increase the performance of your application. 

This blog post explores how to combine these two methods to maximize your application's query performance.

Developer Note: I have observed firsthand how query performance can and will impact application performance. Our application due its size and query frequency requires query optimization. By implementing the technigues explained below, I observed a <percentage>% reduction in application query overhead. Our customers noticed.  

## Select Related

[`select_related`](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#select-related) performs SQL join operations to include the fields of related models in the initial queryset. This method is useful when you have `ForeignKey` or `OneToOneField` relationships in your models. By using `select_related`, you can retrieve related objects in a single database query, rather than issuing separate queries for each related object.

For example, consider the following models for a 'Book' and 'Author':

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

In this case, `select_related` performs a SQL join to include the book's related author objects in the initial queryset. 

This method reduces the number of queries to one, thus optimizing your application performance.

Developer Note: I typically use `select_related` when the application is ...

## Prefetch Related

[`prefetch_related`](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#prefetch-related) reduces the number of queries required to fetch related objects. Unlike `select_related`, `prefetch_related` performs a separate query for each relationship by performing the "joining" in Python. 

This method is useful for `ManyToManyField` and reverse `ForeignKey` relationships.

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

Developer Note:  ...

## Combining select related and prefetch related

In some cases, you may need to optimize queries that involve multiple levels of related objects. You can combine `select_related` and `prefetch_related` to reduce the number of queries required to fetch complex object relationships, regardless of the order in which they are applied.

Developer Note: ...

### Select Related before Prefetch Related

One option you can implement allows you 
For example, consider the following models for `Landmark`, `Hometown`, `Author` and `Book`:

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

In this example, `select_related` performs two SQL joins to include the related author and hometown objects in a single query.`prefetch_related` will then fetch the associated landmarks for each hometown in a separate query, resulting in a total of two queries. 

Without the `select_related` optimization, you would have required four queries.

Developer Note: ...Be sure to ...

### Select Related after Prefetch Related

The [`Prefetch`](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#django.db.models.Prefetch) object allows you to define custom querysets for related objects. This provides you with more control over how related objects are fetched. 

By using the `Prefetch` object in your custom querysets, you can include `select_related` within `prefetch_related` to reduce the number of issued queries.

For example, consider the following models for `Editor`, `Chapter` and `Book`:

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

Your application needs to fetch all books, their chapters and each chapter's editor in as few queries as possible. You could use a single `prefect` to address this requirement:

```python
books = Book.objects.prefetch_related("chapters__editor")
```

This works but it generates three individual queries. 

Developer Note: I commonly see developers use `prefetch_related` alone. This will impact ...

We can use the `Prefetch` object to reduce the number of queries to just two:

```python
from django.db.models import Prefetch

chapters_with_editor_prefetch = Prefetch(
    lookup="chapters",
    queryset=Chapter.objects.select_related("editor"),
)
books = Book.objects.prefetch_related(chapters_with_editor_prefetch)
```

Developer Note: .. I observed ...

## Conclusion

By effectively combining `select_related` and `prefetch_related`, you can optimize database query performance in your Django application. These techniques help you minimize the number of queries allowing you to build more efficient, performant and scalable applications.
