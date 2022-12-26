from zen_queries import fetch

from customsort.models import Todo
from customsort.tests.factories import TodoFactory
from mysite.profilers import timer

# step = 500_000
# n = 5_000_000
# Todo.objects.all().delete()
# with timer(f"inserted {n:,} objects"):
#     for i in range(0, n, step):
#         todos = TodoFactory.build_batch(step)
#         Todo.objects.bulk_create(todos)


qs = Todo.objects.order_by("priority", "title")
# qs = Todo.objects.order_by_priority()
print(qs.query)
print(qs.explain())


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
    print("Done.")
