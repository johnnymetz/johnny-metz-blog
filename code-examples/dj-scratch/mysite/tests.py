from django.db import OperationalError, connection

import pytest


def test_statement_timeout(settings):
    # Not working
    # settings.POSTGRES_STATEMENT_TIMEOUT = "1s"

    with connection.cursor() as cursor:
        with pytest.raises(OperationalError) as exc:
            cursor.execute("select pg_sleep(30)")

    assert "canceling statement due to statement timeout" in str(exc.value)
