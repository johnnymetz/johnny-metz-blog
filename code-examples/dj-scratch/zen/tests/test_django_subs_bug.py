from typing import TypedDict

from django.contrib.auth.models import Group, User
from django.db.models import Count

import pytest
from django_stubs_ext import WithAnnotations


class AnnotatedUser(TypedDict):
    group_count: int


# WithAnnotations[User, AnnotatedUser] breaks something
# https://github.com/typeddjango/django-stubs/issues/763
def print_user_group_count(user: WithAnnotations[User]):
    print(f"{user} belongs to {user.group_count} groups")


@pytest.mark.django_db()
def test_bug():
    group1 = Group.objects.create(name="Group 1")
    group2 = Group.objects.create(name="Group 2")
    group3 = Group.objects.create(name="Group 3")

    user1 = User.objects.create_user(username="user1")
    user2 = User.objects.create_user(username="user2")
    User.objects.create_user(username="user3")

    user1.groups.add(group1, group2, group3)
    user2.groups.add(group1)

    # users = User.objects.all()
    users = User.objects.annotate(group_count=Count("groups"))
    for user in users:
        print_user_group_count(user)
