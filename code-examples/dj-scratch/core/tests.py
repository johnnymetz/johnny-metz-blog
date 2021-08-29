import pytest
from pytest_django.asserts import assertQuerysetEqual

from core.models import Book


@pytest.mark.django_db()
def test_x():
    """
    What we want:
    Out of the latest books, give me the ones with a release year.

    What we're getting:
    Out of the books with a release year, give me the latest ones.
    """
    book1 = Book.objects.create(name="Django tips", edition=1, release_year=2020)
    book2 = Book.objects.create(name="Django tips", edition=2, release_year=2022)
    book3 = Book.objects.create(name="Django tips", edition=3, release_year=None)
    book4 = Book.objects.create(name="Golf swings", edition=1, release_year=2018)
    book5 = Book.objects.create(name="Golf swings", edition=2, release_year=2021)

    for qs, expected_result in [
        (Book.objects.order_by("name", "-edition").distinct("name"), [book3, book5]),
        (
            Book.objects.filter(release_year__isnull=False)
            .order_by("name", "-edition")
            .distinct("name"),
            [book2, book5],
        ),
        # GOTCHA
        (
            Book.objects.order_by("name", "-edition")
            .distinct("name")
            .filter(release_year__isnull=False),
            [book2, book5],
        ),
        # HOW TO FIX IT
        (
            Book.objects.filter(
                # Don't need .values_list("pk", flat=True)
                pk__in=Book.objects.order_by("name", "-edition")
                .distinct("name")
                .values_list("pk", flat=True),
                release_year__isnull=False,
            ),
            [book5],
        ),
    ]:
        # print(qs.query)
        # print(qs)
        assertQuerysetEqual(
            qs, expected_result, ordered=False if len(expected_result) > 1 else True
        )

    # # 2019
    # parasite = Movie.objects.create(name="Parasite", year_released=2019, rating=93)
    # toy_story4 = Movie.objects.create(name="Toy Story 4", year_released=2019, rating=63)
    # the_irishmen = Movie.objects.create(
    #     name="The Irishman", year_released=2019, rating=78
    # )
    # avengers_endgame = Movie.objects.create(
    #     name="Avengers: Endgame", year_released=2019, rating=85
    # )
    # knives_out = Movie.objects.create(name="Knives Out", year_released=2019, rating=51)

    # # 2021
    # space_jam = Movie.objects.create(
    #     name="Space Jam: A New Legacy", year_released=2021, rating=68
    # )
    # tom_and_jerry = Movie.objects.create(
    #     name="Tom & Jerry", year_released=2021, rating=44
    # )
    # quiet_place2 = Movie.objects.create(
    #     name="A Quiet Place Part 2", year_released=2021, rating=81
    # )
    # x = Movie.objects.create(name="X", year_released=2021, rating=76)
    # y = Movie.objects.create(name="Y", year_released=2021, rating=52)

    # for qs in [
    #     Movie.objects.filter(year_released=2019).order_by("-rating")[:3],
    #     Movie.objects.filter(
    #         pk__in=Movie.objects.order_by("-rating")[:3], year_released=2019
    #     ),
    #     Movie.objects.order_by("rating")[:3].filter(year_released=2021),
    # ]:
    #     print(qs.query)
    #     print(qs)

    # Tool.objects.create(name="Hammer", version=1)
    # Tool.objects.create(name="Hammer", version=2)
    # Tool.objects.create(name="Hammer", version=3)
    # tool1 = Tool.objects.create(created_on=timezone.now())
    # tool2 = Tool.objects.create(created_on=timezone.now() - timedelta(days=1))
    # tool3 = Tool.objects.create(created_on=timezone.now() - timedelta(days=2))

    # assert Tool.objects.order_by("-created_on").first() == tool1
    # print(Tool.objects.order_by("-created_on").exclude().first())
