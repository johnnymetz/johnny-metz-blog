---
title: Django's Time-Based Lookups Can Cripple Query Performance
date: 2026-01-19T00:00:00-07:00
tags:
  - Python
  - Django
  - PostgreSQL
  - SQL
ShowToc: true
cover:
  image: 'covers/django-postgresql.png'
---

[`Field lookups`](https://docs.djangoproject.com/en/6.0/topics/db/queries/#field-lookups-intro) are one of the best parts of Django's ORM, but time-based lookups can have an unexpected and severe performance impact by preventing your database from using an existing index and forcing a full table scan.

## A Slow Production Query

I ran into this while debugging a 10 second query on a large table (~25 million rows):

```python
class Event(models.Model):
    timestamp = models.DateTimeField(db_index=True)

Event.objects.filter(timestamp__date="2026-01-05")
```

It generates SQL like this:

```sql
SELECT * FROM event WHERE timestamp::date>'2026-01-05';
```

At first glance, it looked totally reasonable — a simple filter on an indexed field. But after checking the query plan, I discovered the issue: the database can't use the index and falls back to a full table scan because the query casts the field to a date.

## A Tempting Fix: Add an Expression Index

One option is to add an index that matches the query itself, known as an [expression index](https://www.postgresql.org/docs/current/indexes-expressional.html), which means indexing the `timestamp::date` expression.

```python
from django.db.models.functions import TruncDate

class Event(models.Model):
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(TruncDate("timestamp"), name="event_timestamp_date_idx")
        ]
```

This works, but comes with trade-offs. Extra indexes increase storage usage, slow down writes, and add operational complexity, especially on large tables.

Expression indexes are sometimes unavoidable. For example, case-insensitive lookups wrap the column in `UPPER()` on PostgreSQL, making the normal index unusable:

```python
Event.objects.filter(name__iexact="My Event")
```

```sql
-- SQL
SELECT * FROM event WHERE UPPER(name) = UPPER('My Event');
```

Time-based lookups are different. They don't require an expression index. There's a simpler and more efficient solution.

## The Better Fix: Rewrite the Query to Use the Existing Index

Instead of adding another index, we can rewrite the lookup so the database uses the existing `timestamp` index. Compute the date boundaries in Python and filter on the original `DateTimeField`:

```python
import datetime

start = datetime.datetime(2026, 1, 5, tzinfo=datetime.UTC)
end = start + datetime.timedelta(days=1)
Event.objects.filter(timestamp__gte=start, timestamp__lt=end)
```

```sql
-- SQL
SELECT * FROM event WHERE timestamp>='2026-01-05 00:00:00+00:00' and timestamp<'2026-01-06 00:00:00+00:00';
```

After rewriting the query this way, the result took less than a second.

Some notes about this Django query:

- **Timezone matters**: if your project has `USE_TZ=True`, you need timezone-aware datetimes, otherwise Django will warn:

  `RuntimeWarning: DateTimeField Event.timestamp received a naive datetime (2026-01-05 00:00:00) while time zone support is active.)`

- **Avoid `__range` for this**: Django's [`range` lookup](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#range) is inclusive on both ends, and for datetimes you typically want an inclusive lower bound and exclusive upper bound (`>= start` and `< end`) to avoid off-by-one and boundary bugs.

This also happens with aggregates. This Django query took ~30 seconds:

```python
from django.db.models import Min

Event.objects.aggregate(Min('timestamp__date'))
```

```sql
-- SQL
SELECT MIN(timestamp::date) FROM event;
```

The fix is the same idea: query using the original type, then convert in Python:

```python
from django.db.models import Min

result = Event.objects.aggregate(Min('timestamp'))
min_date = result['timestamp__min'].date()
```

```sql
-- SQL
SELECT MIN(timestamp) FROM event;
```

This change dropped the runtime to less than a second.

This isn't just `DateTimeField`. The same general issue can apply to other time-based fields, like `DateField` and `TimeField`, when a lookup requires the database to extract or transform part of the value and it can't use your existing index efficiently.
