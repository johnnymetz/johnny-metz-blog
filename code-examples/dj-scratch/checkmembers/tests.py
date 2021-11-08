from django.contrib.auth.models import Group, User
from django.db import connection, reset_queries
from django.db.models import Count, Exists, OuterRef

import pytest
from pytest_django.asserts import assertQuerysetEqual


@pytest.mark.django_db()
class TestCheckMembers:
    @pytest.fixture()
    def users_with_groups(self):
        group1 = Group.objects.create(name="Group 1")
        group2 = Group.objects.create(name="Group 2")
        group3 = Group.objects.create(name="Group 3")

        user1 = User.objects.create_user(username="user1")
        user2 = User.objects.create_user(username="user2")
        User.objects.create_user(username="user3")
        User.objects.create_user(username="user4")

        user1.groups.add(group1, group2, group3)
        user2.groups.add(group1)

        reset_queries()

        return [user1, user2]

    def test_prefetch(self, users_with_groups):
        """
        Cons:
        - Don't get queryset back
        - 2 db queries
        """
        users = []
        for user in User.objects.prefetch_related("groups"):
            if user.groups.exists():
                users.append(user)

        assert users == users_with_groups
        assert len(connection.queries) == 2

    def test_prefetch_query_counts(self, users_with_groups):
        reset_queries()
        list(User.objects.all())
        assert len(connection.queries) == 1

        reset_queries()
        list(User.objects.prefetch_related("groups"))
        assert len(connection.queries) == 2

        reset_queries()
        list(User.objects.prefetch_related("groups__permissions"))
        assert len(connection.queries) == 3

        reset_queries()
        list(User.objects.prefetch_related("groups", "user_permissions"))
        assert len(connection.queries) == 3

    def test_isnull(self, users_with_groups):
        """Con: have to remember to use distinct()"""
        users = User.objects.filter(groups__isnull=False).distinct()

        # Without distinct we get:
        # <QuerySet [<User: user1>, <User: user1>, <User: user2>]>
        # Each user is returned based on the number of groups it belongs to

        assertQuerysetEqual(users, users_with_groups, ordered=False)
        assert len(connection.queries) == 1

    def test_dunder_count(self, users_with_groups):
        """Con: couting more objects than we need"""
        users = User.objects.filter(groups__count__gt=0)

        assertQuerysetEqual(users, users_with_groups, ordered=False)
        assert len(connection.queries) == 1

    def test_annotate_count(self, users_with_groups):
        """Con: couting more objects than we need"""
        users = User.objects.annotate(group_count=Count("groups")).filter(
            group_count__gt=0
        )

        assertQuerysetEqual(users, users_with_groups, ordered=False)
        assert len(connection.queries) == 1

    def test_annotate_exists(self, users_with_groups):
        users = User.objects.annotate(
            has_group=Exists(Group.objects.filter(user=OuterRef("pk")))
        ).filter(has_group=True)

        assertQuerysetEqual(users, users_with_groups, ordered=False)
        assert len(connection.queries) == 1

    def test_direct_exists(self, users_with_groups):
        """https://docs.djangoproject.com/en/3.2/ref/models/expressions/#filtering-on-a-subquery-or-exists-expressions"""
        users = User.objects.filter(Exists(Group.objects.filter(user=OuterRef("pk"))))

        assertQuerysetEqual(users, users_with_groups, ordered=False)
        assert len(connection.queries) == 1
