import pytest

from core.models import TeamUser
from core.tests import factories


def test_create_team_users(django_assert_num_queries):
    user = factories.UserFactory()
    team = factories.TeamFactory()
    assert team.total_points == 0

    with django_assert_num_queries(1):
        TeamUser.objects.create(team=team, user=user, points=2)
    assert team.total_points == 2

    with django_assert_num_queries(1):
        TeamUser.objects.create(team=team, user=user, points=3)
    assert team.total_points == 5


@pytest.mark.xfail(reason="team.total_points is not invalidated by signal")
def test_delete_all_team_users(django_assert_num_queries):
    user = factories.UserFactory()
    team = factories.TeamFactory()
    for _ in range(10):
        TeamUser.objects.create(team=team, user=user, points=2)
    assert team.total_points == 20

    with django_assert_num_queries(2):
        TeamUser.objects.all().delete()
    # Cache is not invalidated so this is still 20
    assert team.total_points == 0


def test_delete_all_team_users_and_clear_cache(django_assert_num_queries):
    user = factories.UserFactory()
    team = factories.TeamFactory()
    for _ in range(10):
        TeamUser.objects.create(team=team, user=user, points=2)
    assert team.total_points == 20

    with django_assert_num_queries(2):
        team.teamuser_set.all().delete()
    assert team.total_points == 0
