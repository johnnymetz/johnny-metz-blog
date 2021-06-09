---
title: 'Automatically detect N+1 violations in your Pytest suite'
date: 2021-03-13T23:10:50-08:00
description: 'Automatically detect N+1 violations in your Pytest suite'
type: 'posts'
tags:
  - Python
  - Django
  - Pytest
draft: true
---

<!-- https://scoutapm.com/blog/django-and-the-n1-queries-problem -->

## Background

The N+1 problem is a common database performance issue. It plagues ORM's, such as Django and SQLAlchemy, because it results in your application making more database queries than necessary.

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

Now let's create a unit test to ensure `print_songs` runs successfully. We're using `pytest` and `pytest-django` so we can create the test data using a [pytest fixture](https://docs.pytest.org/en/stable/fixture.html). We must also mark our test with [django_db](https://pytest-django.readthedocs.io/en/latest/helpers.html#pytest-mark-django-db-request-database-access) to setup the database. Run the unit test. Notice it passes and our songs are printed to the terminal. Everything seems fine on the surface.

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

```python {hl_lines=[1,"4-5",7]}
from django.db import connection

@pytest.mark.django_db
def test_print_songs(settings, make_data):
    settings.DEBUG = True  # connection.queries is only available if DEBUG=True
    print_songs()
    print(len(connection.queries))

# ...
# 101
```

Why are we making so many queries? We make one query to fetch all `Song` objects in the database. Then, for every song, we make one query to fetch its `Artist` object.

Django's [select_related](https://docs.djangoproject.com/en/3.1/ref/models/querysets/#select-related) and [prefetch_related](https://docs.djangoproject.com/en/3.1/ref/models/querysets/#prefetch-related) queryset methods can easily fix this. `Song` to `Artist` is a Many-to-One relationship so we use `select_related`.

```python {hl_lines=[2]}
def print_songs():
    for song in Song.objects.select_related("artist"):
        print(f"{song.artist.name} - {song.name}")
```

If we run our unit test, we're down to a single db hit.

```python
@pytest.mark.django_db
def test_print_songs(settings, make_data):
    settings.DEBUG = True
    print_songs()
    print(len(connection.queries))

# ...
# 1
```

Now, how can we write our unit test to catch this blunder? I've traditionally used two strategies.

## Assert query count

We can assert the number of db hits at the end of the unit test. This is the simpler approach but doesn't scale very well.

```python
@pytest.mark.django_db
def test_print_songs(settings, make_data):
    settings.DEBUG = True
    print_songs()
    assert len(connection.queries) == 1
```

## nplusone

The [nplusone](https://github.com/jmcarp/nplusone) package automatically detects N+1 violations for you. It comes with a [generic profiler](https://github.com/jmcarp/nplusone#generic) which raises an exception when a violation is executed. We can create a fixture in our `conftest.py` file to wrap all of our tests in this profiler.

```python
# conftest.py
@pytest.fixture(autouse=True)
def _raise_nplusone(request):
    if request.node.get_closest_marker("skip_nplusone"):
        yield
    else:
        with Profiler():
            yield
```

Now an `NPlusOneError` will be raised in any unit test if it contains an N+1 violation. Here's the exception message for our old version of `print_songs` that did NOT use `select_related`.

```text
nplusone.core.exceptions.NPlusOneError: Potential n+1 query detected on `Song.artist`
```

There may be cases where you want to opt-out of the N+1 check. For example, the package may report a false positive or you don't want to fix a specific violation instance. That's where the `skip_nplusone` marker can be used.

## Conclusion

For any project with more than a few unit tests, I'd highly recommend trying out the `_raise_nplusone` fixture. It's a great way to optimize database performance.
