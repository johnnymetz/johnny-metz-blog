# flake8: noqa F841

from django.contrib.auth.models import User
from django.db.models import F, Max, OuterRef, Prefetch, Subquery

from pytest_django.asserts import assertQuerySetEqual

from core.models import Todo
from core.tests.factories import TodoFactory, UserFactory


class TestFetchLatestTodo:
    def test_latest_per_queryset(self):
        user1 = UserFactory()
        todo1 = TodoFactory(user=user1)
        todo2 = TodoFactory(user=user1)
        todo3 = TodoFactory(user=user1)

        assert Todo.objects.latest("updated_at") == todo3
        assert Todo.objects.order_by("-updated_at").first() == todo3
        assert Todo.objects.order_by("-updated_at")[0] == todo3

        todo2.save()

        assert Todo.objects.latest("updated_at") == todo2
        assert Todo.objects.order_by("-updated_at").first() == todo2
        assert Todo.objects.order_by("-updated_at")[0] == todo2

    @staticmethod
    def _assert_approach_1(expected_todos):
        latest_todos = [
            max(user.todo_set.all(), key=lambda x: x.updated_at, default=None)
            for user in User.objects.prefetch_related("todo_set")
        ]
        assert set(latest_todos) == set(expected_todos)

    @staticmethod
    def _assert_approach_2(expected_todos):
        latest_todos = [
            user.todo_set.first()
            for user in User.objects.prefetch_related(
                Prefetch("todo_set", queryset=Todo.objects.order_by("-updated_at")),
            )
        ]
        assert set(latest_todos) == set(expected_todos)

    @staticmethod
    def _assert_approach_3(expected_todos):
        assertQuerySetEqual(
            Todo.objects.annotate(
                latest_updated_at=Max("user__todo__updated_at")
            ).filter(updated_at=F("latest_updated_at")),
            expected_todos,
            ordered=False,
        )

    @staticmethod
    def _assert_approach_4(expected_todos):
        users = User.objects.annotate(
            latest_todo_id=Subquery(
                Todo.objects.filter(user=OuterRef("id"))
                .order_by("-updated_at")
                .values("id")[:1]
            )
        )
        assert set({x.latest_todo_id for x in users}) == {x.id for x in expected_todos}

    @staticmethod
    def _assert_approach_5(expected_todos):
        qs = Todo.objects.order_by("user", "-updated_at").distinct("user")
        print(qs.query)
        assertQuerySetEqual(qs, expected_todos, ordered=False)

    def _assert_approaches(self, expected_todos, django_assert_num_queries):
        expected_num_queries_map = {
            self._assert_approach_1: 2,
            self._assert_approach_2: 2,
            self._assert_approach_3: 1,
            self._assert_approach_4: 1,
            self._assert_approach_5: 1,
        }

        for approach in [
            self._assert_approach_1,
            self._assert_approach_2,
            self._assert_approach_3,
            self._assert_approach_4,
            self._assert_approach_5,
        ]:
            with django_assert_num_queries(expected_num_queries_map[approach]):
                approach(expected_todos)

    def test_latest_per_user(self, django_assert_num_queries):
        user1 = UserFactory()
        user2 = UserFactory()
        user1_todo1 = TodoFactory(user=user1)
        user1_todo2 = TodoFactory(user=user1)
        user1_todo3 = TodoFactory(user=user1)
        user2_todo1 = TodoFactory(user=user2)
        user2_todo2 = TodoFactory(user=user2)

        self._assert_approaches(
            [user1_todo3, user2_todo2],
            django_assert_num_queries,
        )

        user1_todo2.save()
        user2_todo1.save()

        self._assert_approaches(
            [user1_todo2, user2_todo1],
            django_assert_num_queries,
        )

        user1_todo1.save()
        user2_todo2.save()

        self._assert_approaches(
            [user1_todo1, user2_todo2],
            django_assert_num_queries,
        )

    def test_latest_todo_per_user_priority_group(self):
        user1 = UserFactory()
        user2 = UserFactory()
        user1_high_todo1 = TodoFactory(user=user1, priority=Todo.Priority.HIGH)
        user1_high_todo2 = TodoFactory(user=user1, priority=Todo.Priority.HIGH)
        user1_high_todo3 = TodoFactory(user=user1, priority=Todo.Priority.HIGH)
        user1_med_todo1 = TodoFactory(user=user1, priority=Todo.Priority.MEDIUM)
        user1_med_todo2 = TodoFactory(user=user1, priority=Todo.Priority.MEDIUM)
        user2_high_todo1 = TodoFactory(user=user2, priority=Todo.Priority.MEDIUM)
        user2_high_todo2 = TodoFactory(user=user2, priority=Todo.Priority.MEDIUM)
        user2_low_todo1 = TodoFactory(user=user1, priority=Todo.Priority.LOW)
        user2_low_todo2 = TodoFactory(user=user1, priority=Todo.Priority.LOW)
        user2_low_todo3 = TodoFactory(user=user1, priority=Todo.Priority.LOW)

        assertQuerySetEqual(
            Todo.objects.order_by("user", "priority", "-updated_at").distinct(
                "user", "priority"
            ),
            [
                user1_high_todo3,
                user1_med_todo2,
                user2_high_todo2,
                user2_low_todo3,
            ],
            ordered=False,
        )

        user1_high_todo2.save()
        user1_med_todo1.save()
        user2_low_todo1.save()

        assertQuerySetEqual(
            Todo.objects.order_by("user", "priority", "-updated_at").distinct(
                "user", "priority"
            ),
            [
                user1_high_todo2,
                user1_med_todo1,
                user2_high_todo2,
                user2_low_todo1,
            ],
            ordered=False,
        )

    def test_latest_undone_todo_per_user_priority_group(self):
        # Disable black formatter
        # fmt: off
        user1 = UserFactory()
        user2 = UserFactory()
        user1_high_todo1 = TodoFactory(user=user1, priority=Todo.Priority.HIGH)
        user1_high_todo2 = TodoFactory(user=user1, priority=Todo.Priority.HIGH)
        user1_high_todo3 = TodoFactory(user=user1, priority=Todo.Priority.HIGH, is_done=True)
        user1_med_todo1 = TodoFactory(user=user1, priority=Todo.Priority.MEDIUM)
        user1_med_todo2 = TodoFactory(user=user1, priority=Todo.Priority.MEDIUM, is_done=True)
        user2_high_todo1 = TodoFactory(user=user2, priority=Todo.Priority.MEDIUM, is_done=True)
        user2_high_todo2 = TodoFactory(user=user2, priority=Todo.Priority.MEDIUM)
        user2_low_todo1 = TodoFactory(user=user1, priority=Todo.Priority.LOW)
        user2_low_todo2 = TodoFactory(user=user1, priority=Todo.Priority.LOW, is_done=True)
        user2_low_todo3 = TodoFactory(user=user1, priority=Todo.Priority.LOW)
        # fmt: on

        assertQuerySetEqual(
            Todo.objects.filter(is_done=False)
            .order_by("user", "priority", "-updated_at")
            .distinct("user", "priority"),
            [
                user1_high_todo2,
                user1_med_todo1,
                user2_high_todo2,
                user2_low_todo3,
            ],
            ordered=False,
        )

        todos_to_update = [
            user1_high_todo2,
            user1_med_todo1,
            user2_high_todo2,
            user2_low_todo3,
        ]
        for todo in todos_to_update:
            todo.is_done = True
            todo.save()

        assertQuerySetEqual(
            Todo.objects.filter(is_done=False)
            .order_by("user", "priority", "-updated_at")
            .distinct("user", "priority"),
            [user1_high_todo1, user2_low_todo1],
            ordered=False,
        )
