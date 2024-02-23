from django.db.models import F

from core.models import Product, TeamUser
from core.tests import factories


def test_x():
    user1 = factories.UserFactory()
    team1 = factories.TeamFactory()
    team2 = factories.TeamFactory()
    TeamUser.objects.create(team=team1, user=user1, points=3)
    TeamUser.objects.create(team=team1, user=user1, points=4)
    TeamUser.objects.create(team=team2, user=user1, points=5)
    TeamUser.objects.create(team=team2, user=user1, points=6)

    qs = user1.teamuser_set.select_related("team").annotate(team__points=F("points"))

    for x in qs:
        print(x.team.name, x.team__points, x.team.points)


def test_product():
    product = Product.objects.create(name="product1")
    assert product.name == "product1"
