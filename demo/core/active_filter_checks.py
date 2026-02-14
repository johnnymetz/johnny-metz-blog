from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import EmptyResultSet
from django.db.models.expressions import Col
from django.db.models.query import QuerySet

from core.models import StoreProduct

_original_fetch_all = QuerySet._fetch_all  # noqa: SLF001

_active_filter_check_enabled = ContextVar("_active_filter_check_enabled", default=True)


def _get_model_aliases_in_query(query, model) -> set:
    """Return aliases that reference a model."""
    return {
        alias
        for alias, obj in query.alias_map.items()
        if obj.table_name == model._meta.db_table  # noqa: SLF001
    }


def _collect_active_filter_aliases(node, result: set) -> None:
    """Recursively find (alias, "active") column refs in the WHERE clause."""
    for child in getattr(node, "children", None) or []:
        _collect_active_filter_aliases(child, result)
    if lhs := getattr(node, "lhs", None):
        _collect_active_filter_aliases(lhs, result)
    if rhs := getattr(node, "rhs", None):
        _collect_active_filter_aliases(rhs, result)
    if (
        isinstance(node, Col)
        and getattr(node.target, "column", None) == "active"
        and (alias := getattr(node, "alias", None))
    ):
        result.add(alias)


def _query_has_active_filter_for_all_store_product_aliases(query) -> bool:
    """Return True if every StoreProduct alias in the query has an active filter."""
    store_product_aliases = _get_model_aliases_in_query(query, StoreProduct)
    if not store_product_aliases:
        return True

    active_filter_aliases: set[str] = set()
    _collect_active_filter_aliases(query.where, active_filter_aliases)

    return store_product_aliases <= active_filter_aliases


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


def enable_active_filter_query_check():
    """
    Monkeypatch QuerySet._fetch_all so that any query joining StoreProduct
    must include a filter on the active column; otherwise ActiveFilterMissingError
    is raised before the query runs.
    """

    def _fetch_all_with_active_filter_check(self):
        if not _active_filter_check_enabled.get():
            return _original_fetch_all(self)

        try:
            sql = str(self.query)
        except EmptyResultSet:
            return _original_fetch_all(self)

        if not _query_has_active_filter_for_all_store_product_aliases(self.query):
            raise ActiveFilterMissingError(sql=sql)

        return _original_fetch_all(self)

    QuerySet._fetch_all = _fetch_all_with_active_filter_check  # noqa: SLF001


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
