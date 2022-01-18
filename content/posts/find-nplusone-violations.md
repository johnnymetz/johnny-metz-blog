---
title: 'Find all N+1 violations in your Django app'
date: 2021-04-13T23:10:50-08:00
tags:
  - Python
  - Django
  - Pytest
cover:
  image: 'covers/django-nplusone.png'
---

<!-- https://scoutapm.com/blog/django-and-the-n1-queries-problem -->

The N+1 problem is a common database performance issue. It plagues ORM's, such as Django and SQLAlchemy, because it leads to your application making more database queries than necessary.

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

Now let's create a unit test to ensure `print_songs` runs successfully. We're using `pytest` and `pytest-django` so we can create the test data using a [pytest fixture](https://docs.pytest.org/en/stable/fixture.html). When we run the unit test, you'll notice it passes and our songs are printed to the terminal. Everything seems fine on the surface.

```python
@pytest.fixture()
def make_data():
    artist = Artist.objects.create(name="Foo Fighters")
    for i in range(100):
        Song.objects.create(artist=artist, name=f"Song {i + 1}")

@pytest.mark.django_db()  # permits db access
def test_print_songs(make_data):
    print_songs()

# Foo Fighters - Song 1
# Foo Fighters - Song 2
# Foo Fighters - Song 3
# ...
```

However, if we count the number of database queries, we'll see a total of **101**. Yikes!

Note, `connection.queries` is only available if `DEBUG=True`. We can set this globally for all tests by setting `django_debug_mode = true` in our `pytest.ini` configuration file ([docs](https://pytest-django.readthedocs.io/en/latest/usage.html#django-debug-mode-change-how-debug-is-set)).

```python {hl_lines=[1,6]}
from django.db import connection

@pytest.mark.django_db()
def test_print_songs(make_data):
    print_songs()
    print(len(connection.queries))

# ...
# 101
```

Why are we making so many queries? We make a query to fetch all `Song` objects in the database. Then, for every song, we make a query to fetch its `Artist` object.

Django's [select_related](https://docs.djangoproject.com/en/3.1/ref/models/querysets/#select-related) and [prefetch_related](https://docs.djangoproject.com/en/3.1/ref/models/querysets/#prefetch-related) queryset methods can easily fix this. `Song` to `Artist` is a Many-to-One relationship so we use `select_related`.

```python {hl_lines=[2]}
def print_songs():
    for song in Song.objects.select_related("artist"):
        print(f"{song.artist.name} - {song.name}")
```

If we run the unit test against our refactored function, we're down to a single database hit. Nice!

```python
@pytest.mark.django_db()
def test_print_songs(make_data):
    print_songs()
    print(len(connection.queries))

# ...
# 1
```

Now, how can we write our unit test to catch this blunder? I've traditionally used two strategies.

## Assert query count

We can assert the number of db hits at the end of the unit test.

```python {hl_lines=[4]}
@pytest.mark.django_db()
def test_print_songs(make_data):
    print_songs()
    assert len(connection.queries) == 1
```

This approach works but doesn't scale well. Manually counting the expected number of queries and adding the assertion to every unit test is unreasonable.

## nplusone

The [nplusone](https://github.com/jmcarp/nplusone) package automatically finds N+1 violations for you. It comes with a [generic profiler](https://github.com/jmcarp/nplusone#generic) which raises an `NPlusOneError` when a violation is discovered. We can create a fixture in our `conftest.py` file to wrap all of our tests in this profiler.

```python
# conftest.py
import pytest
from nplusone.core.profiler import Profiler

@pytest.fixture(autouse=True)
def _raise_nplusone(request):
    if request.node.get_closest_marker("skip_nplusone"):
        yield
    else:
        with Profiler():
            yield
```

Here's the exception message for our old version of `print_songs` that did NOT use `select_related`.

> nplusone.core.exceptions.NPlusOneError: Potential n+1 query detected on `Song.artist`

There may be cases where you want to opt-out of the N+1 check. For example, the package may report a false positive or you don't want to fix a specific violation. That's the purpose of the `skip_nplusone` marker.

May your database access be optimal.
