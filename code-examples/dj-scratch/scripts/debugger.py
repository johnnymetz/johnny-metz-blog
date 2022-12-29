import logging

from django.core.management import call_command
from django.db import connection

from zen_queries import fetch

from customsort.models import Todo
from customsort.tests.factories import TodoFactory
from mysite.profilers import timer

logger = logging.getLogger(__name__)


step = 500_000
total = 1_000_000
Todo.objects.all().delete()
call_command("migrate", "customsort")
with timer(logger, name=f"inserted {total:,} objects"):
    quotient, remainder = divmod(total, step)
    for i in range(quotient):
        logger.debug(f"Inserting {i * step:,} to {(i + 1) * step:,}")
        todos = TodoFactory.build_batch(step)
        Todo.objects.bulk_create(todos)
    if remainder:
        logger.debug(f"Inserting {total - remainder:,} to {total:,}")
        todos = TodoFactory.build_batch(remainder)
        Todo.objects.bulk_create(todos)
count = Todo.objects.count()
assert count == total, f"{count:,} != {total:,}"

with timer(logger, name="order in Python", decimals=1):
    preference = {
        Todo.Priority.HIGH: 1,
        Todo.Priority.MEDIUM: 2,
        Todo.Priority.LOW: 3,
    }
    sorted(
        Todo.objects.iterator(),
        key=lambda x: [preference[x.priority], x.title],
    )

call_command("migrate", "customsort")
with timer(logger, name="order in DB with integer choices", decimals=1):
    qs = Todo.objects.order_by("priority", "title")
    logger.debug(qs.explain())
    list(qs.iterator())
with timer(logger, name="order in DB with conditional expression", decimals=1):
    qs = Todo.objects.order_by_priority()
    logger.debug(qs.explain())
    list(qs.iterator())

with connection.cursor() as cursor:
    cursor.execute(
        "SELECT indexname FROM pg_indexes WHERE tablename='customsort_todo' ORDER BY tablename, indexname"
    )
    rows = cursor.fetchall()
    print(rows)
call_command("migrate", "customsort", "0001")
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT indexname FROM pg_indexes WHERE tablename='customsort_todo' ORDER BY tablename, indexname"
    )
    rows = cursor.fetchall()
    print(rows)

with timer(logger, name="order in DB with integer choices w/o index", decimals=1):
    qs = Todo.objects.order_by("priority", "title")
    logger.debug(qs.explain())
    list(qs.iterator())
with timer(
    logger, name="order in DB with conditional expression w/o index", decimals=1
):
    qs = Todo.objects.order_by_priority()
    logger.debug(qs.explain())
    list(qs.iterator())


def run():
    logger.debug("Done.")