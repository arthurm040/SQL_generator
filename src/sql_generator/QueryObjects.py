"""Core data classes and enums for SQL query construction.

This module provides the foundational building blocks for constructing SQL queries
in a type-safe, object-oriented manner. It includes data classes for representing
tables, columns, joins, and WHERE conditions, along with enums for operators and
aggregate functions.

Key Components:
    Table: Represents database tables with relationship definitions
    SelectColumn: Handles SELECT clause columns with aggregation and aliasing
    Join/ViaStep: Manages table joins including complex via chains
    WhereCondition: Represents WHERE clause conditions with logical operators
    GroupBy/OrderBy: Column references for GROUP BY and ORDER BY clauses

Enums:
    JoinType: SQL join types (INNER, LEFT, RIGHT, FULL OUTER)
    AggFunction: Aggregate functions (COUNT, SUM, AVG, MIN, MAX, COUNT_DISTINCT)
    Operator: Comparison operators for WHERE clauses (=, <, >, LIKE, IN, etc.)

Example:
    >>> from sql_generator.QueryObjects import Table, TableJoinAttribute, SelectColumn, AggFunction
    >>>
    >>> # Define table relationships
    >>> users = Table("users", joins={"orders": TableJoinAttribute("id", "user_id")})
    >>>
    >>> # Create SELECT columns with aggregation
    >>> name_col = SelectColumn("name", table="users")
    >>> count_col = SelectColumn("id", table="orders", agg_function=AggFunction.COUNT, alias="order_count")

Note:
    These classes are typically used through the QueryBuilder interface rather than
    directly. They provide the internal representation for SQL query components.

"""

import re
from dataclasses import dataclass
from enum import Enum


def _resolve_column_with_alias(column: str, table: str | None, table_aliases: dict[str, str]) -> str:
    """Resolve column name with table alias if specified."""
    if table:
        if table in table_aliases:
            return f"{table_aliases[table]}.{column}"
        else:
            raise ValueError(f"Table '{table}' not found in aliases")
    else:
        return column


class JoinType(Enum):
    """SQL join types for table relationships.

    Defines the different ways tables can be joined in SQL queries, determining
    which rows are included in the result set based on matching conditions.

    Join Types:
        INNER: Returns only rows that have matching values in both tables
        LEFT: Returns all rows from left table, matching rows from right table (NULL if no match)
        RIGHT: Returns all rows from right table, matching rows from left table (NULL if no match)
        FULL: Returns all rows from both tables, with NULLs where no match exists

    Examples:
        # Inner join - only users with orders
        ViaStep("orders", JoinType.INNER)

        # Left join - all users, with order data if available
        ViaStep("orders", JoinType.LEFT)

        # Right join - all orders, with user data if available
        ViaStep("users", JoinType.RIGHT)

        # Full outer join - all users and all orders
        ViaStep("orders", JoinType.FULL)

    """

    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"


class AggFunction(Enum):
    """Common SQL aggregate functions for use in SELECT clauses.

    Supported functions:
        COUNT: Count rows or non-null values
        SUM: Sum numeric values
        AVG: Calculate average of numeric values
        MIN: Find minimum value
        MAX: Find maximum value
        COUNT_DISTINCT: Count unique non-null values

    Examples:
        SelectColumn("id", table="orders", agg_function=AggFunction.COUNT)
        SelectColumn("total", table="orders", agg_function=AggFunction.SUM)
        SelectColumn("category", table="products", agg_function=AggFunction.COUNT_DISTINCT)

    """

    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    COUNT_DISTINCT = "COUNT(DISTINCT"


class Operator(Enum):
    """SQL comparison operators for WHERE clauses.

    Provides type-safe access to SQL comparison operators for building WHERE conditions.
    Supports equality, inequality, range, pattern matching, list membership, and null checks.

    Comparison Operators:
        EQ: Equal to (=) - exact match
        NE: Not equal to (!=) - excludes exact matches
        LT: Less than (<) - numeric/date comparison
        LE: Less than or equal (<=) - numeric/date comparison
        GT: Greater than (>) - numeric/date comparison
        GE: Greater than or equal (>=) - numeric/date comparison

    Pattern Matching:
        LIKE: Case-sensitive pattern matching with wildcards (% and _)
        ILIKE: Case-insensitive pattern matching

    List Operations:
        IN: Value exists in list of options
        NOT_IN: Value does not exist in list of options

    Range Operations:
        BETWEEN: Value falls within inclusive range (requires 2-element list/tuple)

    Null Checks:
        IS_NULL: Column value is NULL (no value parameter needed)
        IS_NOT_NULL: Column value is not NULL (no value parameter needed)

    Examples:
        # Equality and comparison
        WhereCondition("age", Operator.EQ, 25)          # age = 25
        WhereCondition("price", Operator.GT, 100.0)     # price > 100.0

        # Pattern matching
        WhereCondition("name", Operator.LIKE, "%john%")  # name LIKE '%john%'

        # List membership
        WhereCondition("status", Operator.IN, ["active", "pending"])  # status IN ('active', 'pending')

        # Range queries
        WhereCondition("age", Operator.BETWEEN, [18, 65])  # age BETWEEN 18 AND 65

        # Null checks
        WhereCondition("deleted_at", Operator.IS_NULL)   # deleted_at IS NULL

    """

    EQ = "="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    LIKE = "LIKE"
    ILIKE = "ILIKE"
    IN = "IN"
    NOT_IN = "NOT IN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    BETWEEN = "BETWEEN"


@dataclass
class TableJoinAttribute:
    """Defines how to join from a source table to a target table.

    Attributes:
        source_column: Column name on the source table (e.g., 'id')
        target_column: Column name on the target table (e.g., 'user_id')
        table_name: Override target table name if different from join key

    Examples:
        # Direct join: users.id = orders.user_id
        TableJoinAttribute("id", "user_id")

        # Join with table name override
        TableJoinAttribute("id", "user_id", table_name="addresses")

    """

    source_column: str
    target_column: str
    table_name: str | None = None

    def get_table_name(self, join_key: str) -> str:
        """Return table_name if specified, otherwise defaults to join_key.

        Args:
            join_key (str): The join key name to use as fallback table name

        Returns:
            str: The table_name attribute if set, otherwise the join_key parameter

        """
        return self.table_name or join_key


@dataclass
class Table:
    """Represents a database table and its relationships to other tables.

    Attributes:
        name: Database table name
        primary_key: Primary key column name (optional, defaults to "id")
        alias: User-defined alias (optional, auto-generated if not provided)
        joins: Dictionary mapping join keys to Join definitions

    Examples:
        Table("users", joins={
            "orders": TableJoinAttribute("id", "user_id"),
            "profiles": TableJoinAttribute("id", "user_id")
        })

        # With custom primary key
        Table("products", primary_key="product_id", joins={
            "categories": TableJoinAttribute("category_id", "id")
        })

    """

    name: str
    primary_key: str | None = None
    alias: str | None = None
    joins: dict[str, TableJoinAttribute] | None = None


@dataclass
class SelectColumn:
    """Represents a column in a SELECT clause with optional aggregation and aliasing.

    Attributes:
        column: Column name or expression (e.g., 'name', '*', 'NOW()')
        table: Table name for column reference (optional)
        alias: Column alias for AS clause (optional)
        agg_function: Aggregate function to apply (optional)
        distinct: Whether to apply DISTINCT to the column (optional)

    Examples:
        # Simple column
        SelectColumn("name", table="users")

        # Column with alias
        SelectColumn("created_at", table="orders", alias="order_date")

        # Aggregate function
        SelectColumn("id", table="orders", agg_function=AggFunction.COUNT, alias="total_orders")

        # Distinct values
        SelectColumn("status", table="users", distinct=True)

        # Expression without table
        SelectColumn("NOW()", alias="current_time")

    """

    column: str
    table: str | None = None
    alias: str | None = None
    agg_function: AggFunction | None = None
    distinct: bool = False

    def to_sql(self, table_aliases: dict[str, str]) -> str:
        """Convert to complete SQL string with table alias replacement"""
        if "(" in self.column and ")" in self.column and self.table:
            if self.table in table_aliases:
                alias = table_aliases[self.table]
                sql_column = re.sub(rf"\b{re.escape(self.table)}\.", f"{alias}.", self.column)
            else:
                sql_column = self.column
        else:
            sql_column = _resolve_column_with_alias(self.column, self.table, table_aliases)

        if self.agg_function:
            if self.agg_function == AggFunction.COUNT_DISTINCT:
                sql_expr = f"COUNT(DISTINCT {sql_column})"
            else:
                sql_expr = f"{self.agg_function.value}({sql_column})"
        elif self.distinct:
            sql_expr = f"DISTINCT {sql_column}"
        else:
            sql_expr = sql_column

        if self.alias:
            return f"{sql_expr} AS {self.alias}"
        return sql_expr


@dataclass
class ViaStep:
    """Represents a single step in a multi-table join chain (via path).

    Used to define intermediate tables and join types when joining tables that don't
    have direct relationships. Each ViaStep specifies one hop in the join chain,
    allowing complex multi-table joins with different join types at each step.

    Attributes:
        table_name: Name of the intermediate table to join through
        join_type: Type of SQL join to use for this step (defaults to INNER)

    Examples:
        # Simple via step with default INNER join
        ViaStep("orders")

        # Via step with explicit LEFT join
        ViaStep("order_items", JoinType.LEFT)

        # Building a complete via chain: users -> orders -> order_items -> products
        Join("products", via_steps=[
            ViaStep("orders", JoinType.INNER),      # users INNER JOIN orders
            ViaStep("order_items", JoinType.LEFT),  # orders LEFT JOIN order_items
            ViaStep("products", JoinType.INNER)     # order_items INNER JOIN products
        ])

    Note:
        ViaStep objects are typically used within Join objects to define multi-hop
        join paths. The join chain starts from the primary table and follows each
        ViaStep in sequence to reach the target table.

    """

    table_name: str
    join_type: JoinType = JoinType.INNER


@dataclass
class Join:
    """Specifies a join operation with optional via chain.

    Attributes:
        join_key: Key from table's joins dictionary
        via_steps: Optional via chain with join types for each step.
                  If not provided, uses INNER JOIN for direct joins.

    """

    join_key: str
    via_steps: list[ViaStep] | None = None


@dataclass
class ColumnReference:
    """Base class for column references with table alias resolution.

    Provides common functionality for referencing database columns in SQL clauses,
    with automatic table alias resolution and SELECT alias recognition.

    Attributes:
        column: Column name to reference
        table: Table name for column reference (optional)

    Note:
        This is a base class - use GroupBy or OrderBy subclasses instead.

    """

    column: str
    table: str | None = None

    def to_sql(self, table_aliases: dict[str, str], select_aliases: set[str]) -> str:
        """Convert to SQL with table alias resolution

        Args:
            table_aliases: Mapping of table names to their aliases
            select_aliases: Set of column aliases from SELECT clause

        Returns:
            SQL column reference with proper table alias or SELECT alias

        """
        if self.column in select_aliases:
            return self.column
        return _resolve_column_with_alias(self.column, self.table, table_aliases)


@dataclass
class GroupBy(ColumnReference):
    """Represents a column in GROUP BY clause.

    Inherits from ColumnReference to provide table alias resolution and SELECT alias
    recognition. Used to group query results by one or more columns.

    Examples:
        # Group by table column
        GroupBy("category", table="products")  # → pro.category

        # Group by column without table (assumes single table or unambiguous)
        GroupBy("status")  # → status

        # Group by SELECT alias (from aggregate or computed column)
        GroupBy("total_orders")  # → total_orders (if it's a SELECT alias)

    Note:
        Automatically resolves table aliases and recognizes SELECT column aliases.
        When a column name matches a SELECT alias, the alias is used directly.

    """

    pass


@dataclass
class OrderBy(ColumnReference):
    """Represents a column in ORDER BY clause with sort direction.

    Inherits from ColumnReference to provide table alias resolution and SELECT alias
    recognition. Adds sort direction (ASC/DESC) for ordering query results.

    Attributes:
        column: Column name to sort by (inherited from ColumnReference)
        table: Table name for column reference (inherited, optional)
        direction: Sort direction - "ASC" (ascending) or "DESC" (descending)

    Examples:
        # Order by table column, default ascending
        OrderBy("name", table="users")  # → u.name ASC

        # Order by column with explicit direction
        OrderBy("price", table="products", direction="DESC")  # → pro.price DESC

        # Order by SELECT alias
        OrderBy("total_orders", direction="DESC")  # → total_orders DESC

        # Case-insensitive direction (automatically normalized)
        OrderBy("created_at", direction="desc")  # → created_at DESC

    Note:
        Direction is automatically normalized to uppercase and validated.
        Supports both table columns and SELECT aliases for ordering.

    """

    direction: str = "ASC"

    def __post_init__(self):
        """Validate direction is ASC or DESC"""
        if self.direction.upper() not in ("ASC", "DESC"):
            raise ValueError(f"Direction must be 'ASC' or 'DESC', got '{self.direction}'")
        self.direction = self.direction.upper()

    def to_sql(self, table_aliases: dict[str, str], select_aliases: set[str]) -> str:
        """Convert to SQL ORDER BY clause with direction

        Args:
            table_aliases: Mapping of table names to their aliases
            select_aliases: Set of column aliases from SELECT clause

        Returns:
            SQL ORDER BY clause with column reference and direction

        """
        column_sql = super().to_sql(table_aliases, select_aliases)
        return f"{column_sql} {self.direction}"


@dataclass
class WhereCondition:
    """Represents a WHERE clause condition with logical operator support.

    Attributes:
        column: Column name to filter on
        operator: Comparison operator (=, <, >, LIKE, IN, etc.)
        value: Value to compare against (None for IS NULL/IS NOT NULL)
        table: Table name for column reference (optional)
        logical_operator: How to join with previous condition ("AND" or "OR", defaults to "AND")

    Examples:
        # Basic equality condition
        WhereCondition("age", Operator.GE, 18, table="users")
        # → users.age >= 18

        # String pattern matching
        WhereCondition("name", Operator.LIKE, "%john%", table="users")
        # → users.name LIKE '%john%'

        # List membership
        WhereCondition("status", Operator.IN, ["active", "pending"])
        # → status IN ('active', 'pending')

        # Null checks
        WhereCondition("deleted_at", Operator.IS_NULL)
        # → deleted_at IS NULL

        # Range conditions
        WhereCondition("price", Operator.BETWEEN, [10.0, 100.0], table="products")
        # → products.price BETWEEN 10.0 AND 100.0

        # With logical operators
        WhereCondition("age", Operator.LT, 65, logical_operator="OR")
        # → OR age < 65

        # From dict format examples:
        # {"id__eq": 1} → WhereCondition("id", Operator.EQ, 1, logical_operator="AND")
        # {"or__age__lt": 35} → WhereCondition("age", Operator.LT, 35, logical_operator="OR")
        # {"and__status__in": ["active"]} → WhereCondition("status", Operator.IN, ["active"], logical_operator="AND")

    """

    column: str
    operator: Operator
    value: any = None
    table: str | None = None
    logical_operator: str = "AND"

    def to_sql(self, table_aliases: dict[str, str]) -> tuple[str, any]:
        """Convert to SQL WHERE condition with parameterized value.

        Args:
            table_aliases (dict[str, str]): Mapping of table names to their aliases

        Returns:
            tuple[str, any]: A tuple containing the SQL condition string with %s placeholders
                and the parameter values for safe parameterized queries. Parameters may be
                None (for IS NULL/IS NOT NULL), a single value, or a list of values.

        """
        if self.logical_operator not in ("AND", "OR"):
            raise ValueError("Invalid logical operator. Expected AND or OR")
        sql_column = _resolve_column_with_alias(self.column, self.table, table_aliases)

        if self.operator in (Operator.IS_NULL, Operator.IS_NOT_NULL):
            return f"{sql_column} {self.operator.value}", None
        elif self.operator == Operator.BETWEEN:
            if not isinstance(self.value, (list, tuple)) or len(self.value) != 2:
                raise ValueError("BETWEEN operator requires a list/tuple of 2 values")
            return f"{sql_column} BETWEEN %s AND %s", self.value
        elif self.operator in (Operator.IN, Operator.NOT_IN):
            if not isinstance(self.value, (list, tuple)):
                raise ValueError(f"{self.operator.name} operator requires a list/tuple of values")
            placeholders = ", ".join(["%s"] * len(self.value))
            return f"{sql_column} {self.operator.value} ({placeholders})", list(self.value)
        else:
            return f"{sql_column} {self.operator.value} %s", self.value
