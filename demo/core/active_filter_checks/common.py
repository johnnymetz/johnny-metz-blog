from contextlib import contextmanager
from contextvars import ContextVar

from django.db.models.query import QuerySet

# Capture original before any patching
_original_fetch_all = QuerySet._fetch_all  # noqa: SLF001

_active_filter_check_enabled = ContextVar("_active_filter_check_enabled", default=True)


class ActiveFilterMissingError(AssertionError):
    """
    Raised when a query joins StoreProduct without filtering on active.
    Nested/reverse relation filters bypass the model's default manager,
    so inactive rows can be included unless you filter explicitly.
    """

    def __init__(self, sql: str):
        self.sql = sql.strip()
        super().__init__(
            "Unsafe ORM query: joined StoreProduct without active filter.\n"
            "Add a filter like storeproduct__active=True (or the appropriate "
            "relation prefix and active field).\n"
            "To allow this query intentionally, wrap the code in "
            "disable_active_filter_query_check().\n\n"
            f"SQL:\n{self.sql}"
        )


@contextmanager
def disable_active_filter_query_check():
    """
    Temporarily disable the active-filter query check in this context.
    Thread- and greenlet-safe (ContextVar).
    """
    token = _active_filter_check_enabled.set(False)
    try:
        yield
    finally:
        _active_filter_check_enabled.reset(token)
