import pytest


# https://pytest-django.readthedocs.io/en/latest/faq.html
# #how-can-i-give-database-access-to-all-my-tests-without-the-django-db-marker
@pytest.fixture(autouse=True)
def _enable_db_access(db):
    pass
