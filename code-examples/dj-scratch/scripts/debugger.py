import logging

from django.core.management import call_command
from django.db import connection

from zen_queries import fetch

from customsort.models import Todo
from customsort.tests.factories import TodoFactory
from mysite.profilers import timer

logger = logging.getLogger(__name__)

Todo.objects.all().delete()
call_command("migrate", "customsort")

step = 500_000
total = 100_000
with timer(logger, name=f"inserted {total:,} objects"):
    for i in range(0, total, step):
        end = min(i + step, total)
        logger.debug(f"Inserting {i:,} to {end:,}")
        todos = TodoFactory.build_batch(end)
        Todo.objects.bulk_create(todos)

with timer(logger, name="order in DB with integer choices", decimals=1):
    qs = Todo.objects.order_by("priority", "title")
    logger.debug(qs.explain())
    fetch(qs)

with timer(logger, name="order in DB with conditional expression", decimals=1):
    qs = Todo.objects.order_by_priority()
    logger.debug(qs.explain())
    fetch(qs)

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
    fetch(qs)

with timer(
    logger, name="order in DB with conditional expression w/o index", decimals=1
):
    qs = Todo.objects.order_by_priority()
    logger.debug(qs.explain())
    fetch(qs)

with timer(logger, name="order in Python", decimals=1):
    preference = {
        Todo.Priority.HIGH: 1,
        Todo.Priority.MEDIUM: 2,
        Todo.Priority.LOW: 3,
    }
    sorted(
        Todo.objects.all(),
        key=lambda x: [preference[x.priority], x.title],
    )


# PRIORITY_ORDER = {
#     Todo.Priority.HIGH: 1,
#     Todo.Priority.MEDIUM: 2,
#     Todo.Priority.LOW: 3,
# }
# with timer("get todos", decimals=1):
#     todos = list(Todo.objects.all())
# with timer("sort in Python", decimals=1):
#     # todos = sorted(todos, key=lambda x: [PRIORITY_ORDER[x.priority], x.title])
#     todos.sort(key=lambda x: [PRIORITY_ORDER[x.priority], x.title])


def run():
    logger.debug("Done.")
