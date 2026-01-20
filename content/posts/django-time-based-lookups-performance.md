---
title: 'Django Time-Based Lookups: A Performance Trap'
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

Django's [`field lookups`](https://docs.djangoproject.com/en/6.0/topics/db/queries/#field-lookups-intro) are one of the ORM's best features, but time-based lookups can quietly bypass database indexes, turning fast queries into expensive full table scans.

## A Slow Production Query

I ran into this while debugging a 30 second query on a large table (~25 million rows):

```python
class Event(models.Model):
    timestamp = models.DateTimeField(db_index=True)

Event.objects.filter(timestamp__date=datetime.date(2026, 1, 5)).count()
```

It generates SQL like this:

```sql
SELECT COUNT(*) FROM event
WHERE timestamp::date='2026-01-05';
```

At first glance, it looked totally reasonable — a simple filter on an indexed field. But after checking the query plan, I discovered the issue: the query can't use the index and falls back to a full table scan because it casts the field to a date.

## A Tempting Fix: Add an Expression Index

One option is to create an [expression index](https://www.postgresql.org/docs/current/indexes-expressional.html) on `timestamp::date`, so the query can use an index.

```python
from django.db.models.functions import TruncDate

class Event(models.Model):
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(TruncDate("timestamp"), name="event_timestamp_date_idx")
        ]
```

However, each new index increases storage usage, slows down writes, and adds operational complexity, especially on large tables.

Expression indexes are sometimes unavoidable. For example, case-insensitive lookups wrap the column in `UPPER()` on PostgreSQL, making the normal index unusable:

```python
Event.objects.filter(name__iexact="My Event").count()
```

```sql
-- SQL
SELECT COUNT(*) FROM event
WHERE UPPER(name) = UPPER('My Event');
```

Time-based lookups don't require an expression index. There's a simpler and more efficient solution.

## The Better Fix: Rewrite the Query to Use the Existing Index

Instead of adding another index, rewrite the lookup so it uses the existing `timestamp` index. Compute the date boundaries in Python and filter on the `DateTimeField`:

```python
import datetime

start = datetime.datetime(2026, 1, 5, tzinfo=datetime.UTC)
end = start + datetime.timedelta(days=1)

Event.objects.filter(timestamp__gte=start, timestamp__lt=end).count()
```

```sql
-- SQL
SELECT COUNT(*) FROM event
WHERE timestamp>='2026-01-05 00:00:00+00:00'
  and timestamp<'2026-01-06 00:00:00+00:00';
```

This turns the query into an index only scan and dropped runtime from 30 seconds to less than 1 second.

A few important details:

- **Timezone awareness**: If your project has `USE_TZ=True`, your boundary values must be timezone-aware or Django will warn.
- **Avoid `__range`**: Django's [`range`](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#range) lookup is inclusive on both ends, which can cause boundary bugs.

The same issue shows up with aggregates. This query took 40 seconds:

```python
from django.db.models import Min

Event.objects.aggregate(Min('timestamp__date'))
```

```sql
-- SQL
SELECT MIN(timestamp::date) FROM event;
```

The fix is to aggregate on the original field, then convert the result to a date in Python:

```python
result = Event.objects.aggregate(Min('timestamp'))
min_date = result['timestamp__min'].date()
```

```sql
-- SQL
SELECT MIN(timestamp) FROM event;
```

Again, this allows the query to use an index only scan and brings execution time down to under 1 second.

This pattern isn't limited to `DateTimeField`. Any lookup that extracts or transforms part of a time-based column can prevent index usage unless it's rewritten to operate on the raw column.

May your time-based queries stay index-friendly.
