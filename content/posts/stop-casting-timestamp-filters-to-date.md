---
title: 'Stop Casting Timestamp Fields to date in Django'
date: 2026-01-12T00:00:00-07:00
tags:
  - Python
  - Django
  - PostgreSQL
  - SQL
ShowToc: true
cover:
  image: 'covers/django-postgresql.png'
---

When working with timestamp fields in Django, it's tempting to cast them to dates directly in your queries using Django's [`__date`](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#date) lookup. However, this prevents PostgreSQL from using indexes, leading to dramatically slower queries on large tables.

## A 2.5 Min Query

I ran into this while debugging a Django query that took over 2.5 minutes on a table with roughly 25 million rows. The model was simple and the `timestamp` column was indexed:

```python
from django.db import models


class Event(models.Model):
    timestamp = models.DateTimeField(db_index=True)
```

The ORM code looked innocent enough:

```python
from django.db.models import Min

result = Event.objects.aggregate(Min('timestamp__date'))
```

This generates SQL like:

```sql
SELECT MIN(timestamp::date) FROM event;
```

At first glance, this should be fast—the table had an index on `timestamp`. But after checking the query plan, I discovered the issue: casting the timestamp to a date prevents PostgreSQL from using the index. The database had to scan all 25 million rows and cast each value, resulting in a full table scan instead of an index-only scan.

## Query the Timestamp, Extract the Date in Python

Instead of casting in SQL, query on the timestamp field and extract the date in Python:

```python
from django.db.models import Min

# Fast: Uses the timestamp index
result = Event.objects.aggregate(Min('timestamp'))
min_date = result['timestamp__min'].date()
```

This generates SQL like:

```sql
SELECT MIN(timestamp) FROM event;
```

This query completes in under 2 milliseconds. PostgreSQL can satisfy it with an index-only scan on the timestamp index.

## The Same Problem Shows Up in Filters

This issue isn't limited to aggregates. Django's `__date` lookup causes the same problem in `WHERE` clauses.

```python
# Slow: Can't use index
Event.objects.filter(timestamp__date=date(2026, 1, 1))
```

Use date range queries:

```python
from datetime import datetime, timezone

# Fast: Uses index
start = datetime(2026, 1, 1, tzinfo=timezone.utc)
end = datetime(2026, 1, 2, tzinfo=timezone.utc)
Event.objects.filter(timestamp__gte=start, timestamp__lt=end)
```

This generates SQL that can use the index:

```sql
SELECT * FROM event
WHERE timestamp >= '2026-01-01 00:00:00+00'
  AND timestamp < '2026-01-02 00:00:00+00';
```

Always query on the indexed column (the timestamp), then extract or filter by date in Python or using range queries. This ensures PostgreSQL can use your indexes efficiently.
