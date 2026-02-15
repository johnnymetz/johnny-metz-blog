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
    table_name = model._meta.db_table.lower()  # noqa: SLF001
    return {
        alias
        for alias, obj in query.alias_map.items()
        if obj.table_name.lower() == table_name
    }


def _collect_active_filter_aliases(node, result: set) -> None:
    """Recursively find (alias, "active") column refs in WHERE and annotations."""
    for child in getattr(node, "children", None) or []:
        _collect_active_filter_aliases(child, result)
    if lhs := getattr(node, "lhs", None):
        _collect_active_filter_aliases(lhs, result)
    if rhs := getattr(node, "rhs", None):
        _collect_active_filter_aliases(rhs, result)
    getter = getattr(node, "get_source_expressions", None)
    if getter is not None:
        for expr in getter():
            if expr is not None:
                _collect_active_filter_aliases(expr, result)
    if (
        isinstance(node, Col)
        and getattr(node.target, "column", None) == "active"
        and (alias := getattr(node, "alias", None))
    ):
        result.add(alias)


def _get_subqueries(node, result: list) -> None:
    """Recursively find Subquery/Query nodes that need validation."""
    inner_query = getattr(node, "query", None)
    if inner_query is not None and hasattr(inner_query, "alias_map"):
        result.append(inner_query)
    elif hasattr(node, "alias_map") and hasattr(node, "where"):
        result.append(node)
    for child in getattr(node, "children", None) or []:
        _get_subqueries(child, result)
    if lhs := getattr(node, "lhs", None):
        _get_subqueries(lhs, result)
    if rhs := getattr(node, "rhs", None):
        _get_subqueries(rhs, result)
    getter = getattr(node, "get_source_expressions", None)
    if getter is not None:
        for expr in getter():
            if expr is not None:
                _get_subqueries(expr, result)


def _collect_from_query(query, result: set) -> None:
    """Collect active filter aliases from a query's WHERE and annotations."""
    _collect_active_filter_aliases(query.where, result)
    for annotation in getattr(query, "annotations", {}).values():
        if annotation is not None:
            _collect_active_filter_aliases(annotation, result)


def _query_has_active_filter_for_all_store_product_aliases(query) -> bool:
    """Return True if every StoreProduct alias in the query has an active filter."""
    store_product_aliases = _get_model_aliases_in_query(query, StoreProduct)
    if store_product_aliases:
        active_filter_aliases: set[str] = set()
        _collect_from_query(query, active_filter_aliases)
        if not (store_product_aliases <= active_filter_aliases):
            return False

    subqueries: list = []
    _get_subqueries(query.where, subqueries)
    for annotation in getattr(query, "annotations", {}).values():
        if annotation is not None:
            _get_subqueries(annotation, subqueries)
    for subquery in subqueries:
        if not _query_has_active_filter_for_all_store_product_aliases(subquery):
            return False

    return True


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
