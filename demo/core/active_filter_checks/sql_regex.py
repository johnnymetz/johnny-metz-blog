"""SQL regex-based active filter check."""

import re
from collections import Counter

from django.core.exceptions import EmptyResultSet
from django.db.models.query import QuerySet

from core.models import StoreProduct

from .common import (
    ActiveFilterMissingError,
    _active_filter_check_enabled,
    _original_fetch_all,
)

TABLE_NAME = StoreProduct._meta.db_table  # noqa: SLF001

# Pattern 1: find table references (FROM/JOIN {table} [alias])
TABLE_REF = re.compile(
    rf"(?:FROM|JOIN)\s+{re.escape(TABLE_NAME)}(?:\s+(?:AS\s+)?(?P<alias>[A-Z]+\d+))?",
    re.IGNORECASE,
)


# Pattern 2: find ref.active in filter context (exclude SELECT ref.active, via (?!,))
def active_filter_for(ref: str):
    return re.compile(rf"\b{ref}\.active(?!,)\b", re.IGNORECASE)


def enable_active_filter_query_check_sql_regex():
    """Monkeypatch QuerySet._fetch_all to check SQL for missing active filters."""

    def check(self):
        if not _active_filter_check_enabled.get():
            return _original_fetch_all(self)
        try:
            # Remove all quotes to simplify regex matching
            sql = str(self.query).replace('"', "").replace("'", "")
        except EmptyResultSet:
            return _original_fetch_all(self)
        refs = Counter(m.group("alias") or TABLE_NAME for m in TABLE_REF.finditer(sql))
        for ref, count in refs.items():
            matches = active_filter_for(ref).findall(sql)
            if len(matches) < count:
                raise ActiveFilterMissingError(sql=sql)
        return _original_fetch_all(self)

    QuerySet._fetch_all = check  # noqa: SLF001
