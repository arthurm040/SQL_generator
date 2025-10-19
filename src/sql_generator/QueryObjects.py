from dataclasses import dataclass
from enum import Enum


class JoinType(Enum):
    """SQL join types for table relationships."""

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
        """Return table_name if specified, otherwise defaults to join_key."""
        return self.table_name or join_key


@dataclass
class Table:
    """Represents a database table and its relationships to other tables.

    Attributes:
        name: Database table name
        alias: User-defined alias (optional, auto-generated if not provided)
        joins: Dictionary mapping join keys to Join definitions

    Examples:
        Table("users", alias="u", joins={
            "orders": Joins("id", "user_id"),
            "profiles": Joins("id", "user_id")
        })

    """

    name: str
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
        if self.table:
            if self.table in table_aliases:
                sql_column = f"{table_aliases[self.table]}.{self.column}"
            else:
                raise ValueError(f"Table '{self.table}' not found in aliases")
        else:
            sql_column = self.column

        # Apply aggregate function
        if self.agg_function:
            if self.agg_function == AggFunction.COUNT_DISTINCT:
                sql_expr = f"COUNT(DISTINCT {sql_column})"
            else:
                sql_expr = f"{self.agg_function.value}({sql_column})"
        elif self.distinct:
            sql_expr = f"DISTINCT {sql_column}"
        else:
            sql_expr = sql_column

        # Apply alias
        if self.alias:
            return f"{sql_expr} AS {self.alias}"
        return sql_expr


@dataclass
class ViaStep:
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
