import pytest
from pytest_django.asserts import assertQuerysetEqual
from zen_queries import fetch

from customsort.models import Todo
from customsort.tests.factories import TodoFactory
from mysite.profilers import timer


class TestCustomSort:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.todo1 = Todo.objects.create(
            title="Add linters", priority=Todo.Priority.MEDIUM, done=True
        )
        self.todo2 = Todo.objects.create(title="Fix bug", priority=Todo.Priority.HIGH)
        self.todo3 = Todo.objects.create(
            title="Increase test coverage", priority=Todo.Priority.MEDIUM
        )
        self.todo4 = Todo.objects.create(
            title="Refactor views", priority=Todo.Priority.LOW
        )
        self.todo5 = Todo.objects.create(
            title="Run tests in CI", priority=Todo.Priority.HIGH, done=True
        )

        self.expected = [
            self.todo2,
            self.todo5,
            self.todo1,
            self.todo3,
            self.todo4,
        ]

        # Verify records aren't already sorted in DB
        assert list(Todo.objects.all()) != self.expected

    def test_sort_list(self):
        preference = {
            Todo.Priority.HIGH: 1,
            Todo.Priority.MEDIUM: 2,
            Todo.Priority.LOW: 3,
        }

        preferred = sorted(
            Todo.objects.all(),
            key=lambda x: [preference[x.priority], x.title],
        )
        assert preferred == self.expected

    def test_sort_in_db_by_integer_choices(self):
        assertQuerysetEqual(
            Todo.objects.order_by("priority", "title"), self.expected, ordered=False
        )

    def test_sort_in_db_by_conditional_expression(self):
        """Test sort by conditional expression using queryset methods"""
        assertQuerysetEqual(
            Todo.objects.all().order_by_priority(), self.expected, ordered=False
        )
        assertQuerysetEqual(
            Todo.objects.filter(done=False).order_by_priority(),
            [x for x in self.expected if x.done is False],
            ordered=False,
        )
        assertQuerysetEqual(
            Todo.objects.exclude(priority=Todo.Priority.LOW).order_by_priority(),
            [x for x in self.expected if x.priority != Todo.Priority.LOW],
            ordered=False,
        )

    def test_manager_method(self):
        assertQuerysetEqual(
            Todo.objects.order_by_priority(), self.expected, ordered=False
        )

    # @pytest.mark.skip(reason="Slow test")
    def test_benchmark(self):
        n = 5_000_000

        with timer(f"build {n:,} objects without saving"):
            todos = TodoFactory.build_batch(n)

        with timer("bulk create objects"):
            Todo.objects.bulk_create(todos)

        with timer("order in DB with integer choices", decimals=1):
            fetch(Todo.objects.order_by("priority", "title"))

        with timer("order in DB with conditional expression", decimals=1):
            fetch(Todo.objects.order_by_priority())

        with timer("order in Python", decimals=1):
            preference = {
                Todo.Priority.HIGH: 1,
                Todo.Priority.MEDIUM: 2,
                Todo.Priority.LOW: 3,
            }
            sorted(
                Todo.objects.all(),
                key=lambda x: [preference[x.priority], x.title],
            )
