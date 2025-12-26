# flake8: noqa F841

from django.contrib.auth.models import Group, User
from django.db.models import Exists, OuterRef
from django.db.utils import ProgrammingError

import pytest
from pytest_django.asserts import assertQuerySetEqual

from core.tests.factories import GroupFactory, UserFactory


class TestAvoidDuplicateRecords:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user1 = UserFactory(email="z@company.com")
        self.user2 = UserFactory(email="a@company.com")

        # Set self.groups to a queryset instead of a list because that's what we have in practice
        GroupFactory.create_batch(2)
        self.groups = Group.objects.all()

        self.user1.groups.add(*self.groups)
        self.user2.groups.add(self.groups[0])

    def test_avoid_duplicates(self):
        users = User.objects.filter(groups__in=self.groups)
        assertQuerySetEqual(users, [self.user1, self.user1, self.user2], ordered=False)
        assertQuerySetEqual(users.distinct(), [self.user1, self.user2], ordered=False)
        assertQuerySetEqual(
            users.distinct("id"), [self.user1, self.user2], ordered=False
        )
        assertQuerySetEqual(
            User.objects.filter(id__in=users.distinct("id")).order_by("email"),
            [self.user2, self.user1],
        )
        assertQuerySetEqual(
            users.order_by("email").distinct("email"), [self.user2, self.user1]
        )

        assertQuerySetEqual(
            User.objects.filter(
                Exists(Group.objects.filter(user=OuterRef("id"), id__in=self.groups))
            ).order_by("email"),
            [self.user2, self.user1],
        )
        print(users)

        with pytest.raises(
            ProgrammingError,
            match="SELECT DISTINCT ON expressions must match initial ORDER BY expressions",
        ):
            list(users.order_by("email").distinct("id"))
