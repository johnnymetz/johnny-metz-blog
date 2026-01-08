# flake8: noqa F841

from django.db.models import Exists, OuterRef
from django.db.utils import ProgrammingError

import pytest
from pytest_django.asserts import assertQuerySetEqual

from core.models import Author, Book
from core.tests.factories import AuthorFactory, BookFactory


class TestAvoidDuplicateRecords:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.charlie = AuthorFactory(name="Charlie")
        self.alice = AuthorFactory(name="Alice")
        self.zoe = AuthorFactory(name="Zoe")

        BookFactory(title="Book A", author=self.charlie)
        BookFactory(title="Book B", author=self.alice)
        BookFactory(title="Book C", author=self.alice)
        BookFactory(title="Novel D", author=self.zoe)

    def test_avoid_duplicates(self):
        authors = Author.objects.filter(books__title__startswith="Book")
        assertQuerySetEqual(
            authors, [self.charlie, self.alice, self.alice], ordered=False
        )
        assertQuerySetEqual(
            authors.distinct(), [self.charlie, self.alice], ordered=False
        )
        assertQuerySetEqual(
            authors.distinct("id"), [self.charlie, self.alice], ordered=False
        )
        assertQuerySetEqual(
            Author.objects.filter(id__in=authors.distinct("id")).order_by("name"),
            [self.alice, self.charlie],
        )

        assertQuerySetEqual(
            authors.order_by("name").distinct("name"), [self.alice, self.charlie]
        )

        assertQuerySetEqual(
            Author.objects.filter(
                Exists(
                    Book.objects.filter(author=OuterRef("id"), title__startswith="Book")
                )
            ).order_by("name"),
            [self.alice, self.charlie],
        )

        with pytest.raises(
            ProgrammingError,
            match="SELECT DISTINCT ON expressions must match initial ORDER BY expressions",
        ):
            list(authors.order_by("name").distinct("id"))
