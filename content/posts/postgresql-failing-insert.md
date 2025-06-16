---
title: 'Avoiding PostgreSQL Pitfalls: The Hidden Cost of Failing Inserts'
date: 2025-06-15T18:00:00-07:00
ShowToc: true
tags:
  - Python
  - Django
  - PostgreSQL
---

A simple insert query turned into a silent performance killer.

Our frontend pings our server every few minutes to track device activity. Each ping attempts to insert a row into a `DevicePingDaily` table, which has a unique constraint on `(device_id, date)` to ensure only one record per device per day.

In Django, the logic looked like this:

```python
try:
    DevicePingDaily.objects.create(device=device, date=today)
except IntegrityError:
    pass
```

It seemed harmless. But as traffic grew, latency spiked and API timeouts increased. Observability tools quickly pointed to the culprit:

> Over a 14-hour window, this single INSERT accounted for 10 minutes of total database time. The next highest query took just 6 seconds.

What looked like a simple, low-risk query had become the system's top performance bottleneck.

## Root Cause: Failing Inserts at Scale

At high volume, failing inserts introduce surprising overhead.

In this case, most insert attempts conflicted with an existing `(device_id, date)` record. Each failure created two downstream problems:

### 1. Transaction Rollbacks

In SQL, all writes run inside a transaction to satisfy ACID guarantees. When an insert fails, PostgreSQL rolls back the transaction. A single rollback is cheap, but doing this repeatedly is expensive, especially when combined Django's exception handling.

### 2. Dead Tuples and Table Bloat

Each failed insert leaves behind a **dead tuple** — a row that's invisible to queries but still occupies space on disk. These accumulate over time, bloating both the table and its indexes. That bloat slows down inserts, lookups, constraint checks and triggers frequent autovacuum runs.

In our case, autovacuum ran over 1,200 times in two weeks — a clear sign that PostgreSQL was struggling to keep up with the churn.

To check autovacuum stats:

```sql
SELECT relname, last_autovacuum, autovacuum_count
FROM pg_stat_user_tables
WHERE relname='device_ping_daily';
```

## The Fix: Let PostgreSQL Handle Conflicts

PostgreSQL provides a clean solution: `ON CONFLICT DO NOTHING`. This skips the insert if a conflict occurs — no exception, no rollback, no dead tuple.

There are two good ways to use it in Django.

### Option 1: `bulk_create(..., ignore_conflicts=True)`

While Django doesn't support `ON CONFLICT DO NOTHING` for a single `create()` call, it does expose it through `bulk_create`:

```python
DevicePingDaily.objects.bulk_create(
    [DevicePingDaily(device=device, date=today)],
    ignore_conflicts=True,
)
```

Under the hood, this generates `INSERT ... ON CONFLICT DO NOTHING`. It's ORM-friendly and easy to read. However, even for one row, Django wraps the call in a transaction, which adds slight overhead. For most use cases, this tradeoff is negligible and the solution is perfectly sufficient.

### Option 2: Raw SQL

For maximum performance, the insert can be issued directly:

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        f"""
        INSERT INTO {DevicePingDaily._meta.db_table} (device_id, date)
        VALUES (%s, %s) ON CONFLICT (device_id, date) DO NOTHING;
        """,
        [device.id, today],
    )
```

This avoids ORM overhead and transaction wrapping, making it ideal for high-throughput paths. It also allows finer control over conflict handling beyond what `bulk_create` currently supports, such as referencing specific constraints. It requires more care and SQL expertise, but in our case, it was the right choice for scale and flexibility.

After deploying the change, the results were clear:

- Total time spent on the query dropped from 10 minutes to a few seconds
- Autovacuum activity on the table dropped to zero
- API timeouts disappeared

May your inserts be fast and your autovacuums quiet.
