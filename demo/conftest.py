import pytest

from core.active_filter_checks import enable_active_filter_query_check


@pytest.fixture(autouse=True, scope="session")
def _enable_active_filter_query_check():
    enable_active_filter_query_check(
        # implementation="inspection",
        implementation="sql_regex",
    )
