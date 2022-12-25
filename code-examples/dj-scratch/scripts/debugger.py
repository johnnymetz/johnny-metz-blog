from customsort.models import Todo
from customsort.tests.factories import TodoFactory
from mysite.profilers import timer

n = 5_000_000
with timer(f"build {n:,} objects without saving"):
    todos = TodoFactory.build_batch(n)
with timer("bulk create objects"):
    Todo.objects.bulk_create(todos)


# qs = Todo.objects.order_by("priority", "title")
# print(qs.query)
# print(qs.explain())


def run():
    print("Done.")
