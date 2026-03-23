"""
Active filter query checks for StoreProduct.

Two implementations are available:
- query_inspection: Walks Django's query AST (database-agnostic)
- sql_regex: Parses generated SQL (simpler but database-specific)
"""

from .common import (
    ActiveFilterMissingError,
    disable_active_filter_query_check,
)
from .query_inspection import enable_active_filter_query_check_inspection
from .sql_regex import enable_active_filter_query_check_sql_regex

__all__ = [
    "ActiveFilterMissingError",
    "disable_active_filter_query_check",
    "enable_active_filter_query_check",
    "enable_active_filter_query_check_inspection",
    "enable_active_filter_query_check_sql_regex",
]


def enable_active_filter_query_check(implementation: str):
    """
    Enable the active filter query check.

    Args:
        implementation: "inspection" or "sql_regex"
    """
    if implementation == "sql_regex":
        enable_active_filter_query_check_sql_regex()
    elif implementation == "inspection":
        enable_active_filter_query_check_inspection()
    else:
        raise ValueError(f"Unknown implementation: {implementation}")
