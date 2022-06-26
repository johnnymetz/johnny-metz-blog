import pytest
from pytest_django.asserts import assertQuerysetEqual

from customsort.models import Todo
from customsort.tests.factories import TodoFactory
from mysite.profilers import timer


class TestCustomChoiceSort:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.todo1 = TodoFactory(priority=Todo.Priority.MEDIUM)
        self.todo2 = TodoFactory(priority=Todo.Priority.HIGH)
        self.todo3 = TodoFactory(priority=Todo.Priority.LOW)
        self.todo4 = TodoFactory(priority=Todo.Priority.MEDIUM)
        self.todo5 = TodoFactory(priority=Todo.Priority.LOW)
        self.todo6 = TodoFactory(priority=Todo.Priority.HIGH)

        self.expected = [
            self.todo2,
            self.todo6,
            self.todo1,
            self.todo4,
            self.todo3,
            self.todo5,
        ]

        # Verify records aren't already sorted in DB
        assert list(Todo.objects.all()) != self.expected
        assert (
            sorted(
                Todo.objects.all(),
                key=lambda x: (x.priority, x.id),
            )
            != self.expected
        )

    def test_sort_list(self):
        preference = {
            Todo.Priority.HIGH: 1,
            Todo.Priority.MEDIUM: 2,
            Todo.Priority.LOW: 3,
        }

        preferred = sorted(
            Todo.objects.all(),
            # Sort by id also just so it's consistent if there's a tie
            key=lambda x: [preference[x.priority], x.id],
        )
        assert preferred == self.expected

    def test_sort_in_db(self):
        assertQuerysetEqual(
            Todo.objects.exclude(priority=Todo.Priority.LOW).order_by_priority(),
            [x for x in self.expected if x.priority != Todo.Priority.LOW],
            ordered=False,
        )

    def test_manager_method(self):
        assertQuerysetEqual(
            Todo.objects.order_by_priority(), self.expected, ordered=False
        )

    def test_queryset_method(self):
        assertQuerysetEqual(
            Todo.objects.all().order_by_priority(), self.expected, ordered=False
        )

    @pytest.mark.skip(reason="Slow test")
    def test_sort_many_todos(self):
        with timer("build objects without saving"):
            todos = TodoFactory.build_batch(10_000_000)
            # todos = TodoFactory.build_batch(1000)

        with timer("bulk create objects"):
            Todo.objects.bulk_create(todos)

        with timer("order in DB", decimals=1):
            qs = Todo.objects.all().order_by_priority()

        with timer("order in Python", decimals=1):
            preference = {
                Todo.Priority.HIGH: 1,
                Todo.Priority.MEDIUM: 2,
                Todo.Priority.LOW: 3,
            }
            lst = sorted(
                Todo.objects.all(),
                # Sort by id also just so it's consistent if there's a tie
                key=lambda x: [preference[x.priority], x.id],
            )

        assertQuerysetEqual(qs, lst, ordered=False)
