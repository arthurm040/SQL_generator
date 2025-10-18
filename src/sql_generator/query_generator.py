from dataclasses import dataclass


@dataclass
class Joins:
    """Defines how to join from a source table to a target table.

    Attributes:
        source_column: Column name on the source table (e.g., 'id')
        target_column: Column name on the target table (e.g., 'user_id')
        table_name: Override target table name if different from join key
        via: List of intermediate tables to traverse for indirect joins

    Examples:
        # Direct join: users.id = orders.user_id
        Joins("id", "user_id")

        # Indirect join: users -> orders -> order_items
        Joins("id", "product_id", via=[orders_table, order_items_table])

    """

    source_column: str
    target_column: str
    table_name: str | None = None
    via: list["Table"] | None = None

    def get_table_name(self, join_key: str) -> str:
        """Return table_name if specified, otherwise defaults to join_key."""
        return self.table_name or join_key


@dataclass
class Table:
    """Represents a database table and its relationships to other tables.

    Attributes:
        name: Database table name
        joins: Dictionary mapping join keys to Join definitions

    Examples:
        Table("users", joins={
            "orders": Joins("id", "user_id"),
            "profiles": Joins("id", "user_id")
        })

    """

    name: str
    joins: dict[str, Joins] | None = None

# TODO: Implement circular dependency detection for table relationships
# - Build dependency map from table joins and via chains
# - Detect bidirectional relationships (A → B and B → A)
# - Decide whether to error or warn on circular dependencies


