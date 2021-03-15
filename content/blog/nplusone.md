---
title: 'Automatically detect N+1 violations in your Pytest suite'
date: 2021-02-17T23:10:50-08:00
description: 'Some description'
type: 'posts'
tags:
  - Django
  - Pytest
  - nplusone
draft: true
---

# Automatically detect N+1 violations in your pytest suite

<!-- https://scoutapm.com/blog/django-and-the-n1-queries-problem -->

The N+1 problem is a common database performance issue often seen in ORMs. It plagues ORM's, such as Django and SQLAlchemy because it involves making more database queries than necessary.

Let's look at a basic example in Django.

```python
class Artist(models.Model):
    name = models.CharField(max_length=255)

class Song(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

def print_songs():
    for song in Song.objects.all():
        print(f"{song.artist.name} - {song.name}")
```

Now let's create a unit test to ensure `print_songs` runs successfully. We're using `pytest` and `pytest-django` so we can create test data using a [fixture](https://docs.pytest.org/en/stable/fixture.html). We must also mark our test with [django_db](https://pytest-django.readthedocs.io/en/latest/helpers.html#pytest-mark-django-db-request-database-access) to request database access. Run the unit test with `pytest`. Notice the test passes and seems fine on the surface.

```python
@pytest.fixture()
def make_data():
    artist = Artist.objects.create(name="Foo Fighters")
    for i in range(100):
        Song.objects.create(artist=artist, name=f"Song {i + 1}")

@pytest.mark.django_db
def test_print_songs(make_data):
    print_songs()

# Foo Fighters - Song 1
# Foo Fighters - Song 2
# Foo Fighters - Song 3
# ...
```

However, if we count the number of database queries, we'll see a total of 101. Yikes!

```python
from django.db import connection

@pytest.mark.django_db
def test_print_songs(settings, make_data):
    settings.DEBUG = True
    print_songs()
    print(len(connection.queries))

# ...
# 101
```

Why are we making so many queries? We make one query to fetch all `Song` objects in the database. Then, for every song, we make one query to fetch its `Artist` object.

Django's [select_related()](https://docs.djangoproject.com/en/3.1/ref/models/querysets/#select-related) and [prefetch_related()](https://docs.djangoproject.com/en/3.1/ref/models/querysets/#prefetch-related) queryset methods can easily fix this
