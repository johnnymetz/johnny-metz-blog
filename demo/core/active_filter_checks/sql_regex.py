"""SQL regex-based active filter check. Parses generated SQL for missing filters."""

import re
from collections import Counter

from django.core.exceptions import EmptyResultSet
from django.db.models.query import QuerySet

from .common import (
    ActiveFilterMissingError,
    _active_filter_check_enabled,
    _original_fetch_all,
)

# StoreProduct table (core app). JOIN/FROM with optional Django alias (e.g. U0, V1).
STORE_PRODUCT_JOIN_PATTERN = re.compile(
    r"\b(?:FROM|JOIN)\s+core_storeproduct(?:\s+(?:AS\s+)?(?P<alias>[A-Z]+[0-9]+))?",
    re.IGNORECASE,
)


def _active_filter_pattern(ref: str):
    """
    Match ref.active in filter context (= true, IS true, = 1, or bare after
    WHERE/AND/OR/().
    """
    return re.compile(
        rf"(?:\b{re.escape(ref)}\.active\s*(?:=\s*(?:true|1)|IS\s+true)|"
        rf"(?:WHERE|AND|OR|\()\s*{re.escape(ref)}\.active)\b",
        re.IGNORECASE,
    )


def enable_active_filter_query_check_sql_regex():
    """
    Monkeypatch QuerySet._fetch_all using SQL regex to detect missing active filters.
    Parses generated SQL - database-specific; may need updates for new SQL variants.
    """

    def _fetch_all_with_sql_regex_check(self):
        if not _active_filter_check_enabled.get():
            return _original_fetch_all(self)

        try:
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
                raise ActiveFilterMissingError(sql=str(self.query))

        return _original_fetch_all(self)

    QuerySet._fetch_all = _fetch_all_with_sql_regex_check  # noqa: SLF001
