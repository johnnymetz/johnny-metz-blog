import re
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import EmptyResultSet
from django.db.models.query import QuerySet

_original_fetch_all = QuerySet._fetch_all  # noqa: SLF001

_active_filter_check_enabled = ContextVar("_active_filter_check_enabled", default=True)

# StoreProduct table (core app). JOIN/FROM with optional Django alias (e.g. U0, V1).
STORE_PRODUCT_JOIN_PATTERN = re.compile(
    r"\b(?:FROM|JOIN)\s+core_storeproduct(?:\s+(?:AS\s+)?(?P<alias>[A-Z]+[0-9]+))?",
    re.IGNORECASE,
)


def _active_filter_pattern(ref: str):
    """
    Regex: ref.active in filter context
    (= true, IS true, = 1, or bare after WHERE/AND/OR/().
    """
    return re.compile(
        rf"(?:\b{re.escape(ref)}\.active\s*(?:=\s*(?:true|1)|IS\s+true)|"
        rf"(?:WHERE|AND|OR|\()\s*{re.escape(ref)}\.active)\b",
        re.IGNORECASE,
    )


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
            # Remove all quotes to simplify regex matching
            sql = str(self.query).replace('"', "").replace("'", "")
        except EmptyResultSet:
            return _original_fetch_all(self)

        matches = list(STORE_PRODUCT_JOIN_PATTERN.finditer(sql))
        if not matches:
            return _original_fetch_all(self)

        ref_counts = Counter(m.group("alias") or "core_storeproduct" for m in matches)

        for ref, count in ref_counts.items():
            filter_re = _active_filter_pattern(ref)
            if len(filter_re.findall(sql)) < count:
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
