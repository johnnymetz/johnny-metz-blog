from subqueries.models import Book

Book.objects.get_or_create(name="Django tips", edition=1, release_year=2020)
Book.objects.get_or_create(name="Django tips", edition=2, release_year=2022)
Book.objects.get_or_create(name="Django tips", edition=3, release_year=None)
Book.objects.get_or_create(name="Golf swings", edition=1, release_year=2018)
Book.objects.get_or_create(name="Golf swings", edition=2, release_year=2021)

print(Book.objects.count())


def run():
    pass
