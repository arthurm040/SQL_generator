"""SQL Query Builder - Dynamic SQL query construction with automatic table aliasing.

A Python library for building SQL queries dynamically using a constructor-based API.
Eliminates complex if/else logic for dynamic WHERE clauses and JOINs.
"""

from sql_generator.QueryObjects import (
    AggFunction,
    GroupBy,
    Join,
    JoinType,
    Operator,
    OrderBy,
    SelectColumn,
    Table,
    TableJoinAttribute,
    ViaStep,
    WhereCondition,
)
from sql_generator.select_query_generator import QueryBuilder

__all__ = [
    "QueryBuilder",
    "Table",
    "TableJoinAttribute",
    "SelectColumn",
    "Join",
    "ViaStep",
    "JoinType",
    "WhereCondition",
    "GroupBy",
    "OrderBy",
    "AggFunction",
    "Operator",
]

__version__ = "0.1.0"
