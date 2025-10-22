import re
from typing import Any

from sql_generator.QueryObjects import GroupBy, Join, JoinType, Operator, OrderBy, SelectColumn, Table, WhereCondition

_operator_map = {
    "eq": Operator.EQ,
    "ne": Operator.NE,
    "lt": Operator.LT,
    "le": Operator.LE,
    "gt": Operator.GT,
    "ge": Operator.GE,
    "like": Operator.LIKE,
    "ilike": Operator.ILIKE,
    "in": Operator.IN,
    "not_in": Operator.NOT_IN,
    "is_null": Operator.IS_NULL,
    "is_not_null": Operator.IS_NOT_NULL,
    "between": Operator.BETWEEN,
}


class QueryBuilder:
    """SQL query builder using constructor-based API.

    Creates dynamic SQL queries with automatic table aliasing and relationship management.
    Eliminates complex if/else logic for dynamic WHERE clauses and JOINs. Perfect for APIs,
    admin interfaces, reporting systems, and any application that needs dynamic SQL generation.

    Features:
        - Constructor-based API (no method chaining required)
        - Automatic table aliasing with conflict resolution
        - Django-style WHERE conditions with logical operators
        - Flexible JOIN system with via chains
        - Parameterized queries for SQL injection protection
        - Hybrid input support (strings or objects)

    Examples:
        Basic query generation:

        >>> from sql_generator import QueryBuilder, Table
        >>> qb = QueryBuilder([Table('users')], ['users.name', 'users.email'])
        >>> sql, params = qb.build()
        >>> print(sql)
        SELECT use.name, use.email
        FROM users use
        >>> print(params)
        []

        Query with WHERE conditions and parameters:

        >>> qb = QueryBuilder(
        ...     [Table('users')],
        ...     ['users.name'],
        ...     where={'users.active__eq': True, 'users.age__gt': 18}
        ... )
        >>> sql, params = qb.build()
        >>> print(sql)
        SELECT use.name
        FROM users use
        WHERE use.active = %s AND use.age > %s
        >>> print(params)
        [True, 18]

        Query with JOINs:

        >>> from sql_generator import TableJoinAttribute
        >>> users = Table('users', joins={'orders': TableJoinAttribute('id', 'user_id')})
        >>> orders = Table('orders')
        >>> qb = QueryBuilder([users, orders], ['users.name', 'orders.total'], joins=['orders'])
        >>> sql, params = qb.build()
        >>> print(sql)
        SELECT use.name, ord.total
        FROM users use
        INNER JOIN orders ord ON use.id = ord.user_id

        Complex query with aggregation and all clauses:

        >>> from sql_generator import SelectColumn, AggFunction
        >>> qb = QueryBuilder(
        ...     [users, orders],
        ...     ['users.name', SelectColumn('COUNT(*)', alias='order_count')],
        ...     joins=['orders'],
        ...     where={'users.active__eq': True, 'orders.total__gt': 100},
        ...     group_by=['users.id', 'users.name'],
        ...     order_by=['order_count DESC'],
        ...     limit=50
        ... )
        >>> sql, params = qb.build()
        >>> print(sql)
        SELECT use.name, COUNT(*) AS order_count
        FROM users use
        INNER JOIN orders ord ON use.id = ord.user_id
        WHERE use.active = %s AND ord.total > %s
        GROUP BY use.id, use.name
        ORDER BY order_count DESC
        LIMIT 50
        >>> print(params)
        [True, 100]

        Logical operators in WHERE conditions:

        >>> qb = QueryBuilder(
        ...     [Table('users')],
        ...     ['users.name'],
        ...     where={'users.active__eq': True, 'or__users.role__eq': 'admin'}
        ... )
        >>> sql, params = qb.build()
        >>> print(sql)
        SELECT use.name
        FROM users use
        WHERE use.active = %s OR use.role = %s
        >>> print(params)
        [True, 'admin']

        Dynamic query generation for APIs:

        >>> def get_users(filters=None, include_orders=False, sort_by=None):
        ...     tables = [Table('users')]
        ...     select_cols = ['users.name', 'users.email']
        ...     joins = []
        ...
        ...     if include_orders:
        ...         tables.append(Table('orders'))
        ...         select_cols.append('orders.total')
        ...         joins.append('orders')
        ...
        ...     return QueryBuilder(
        ...         tables=tables,
        ...         select=select_cols,
        ...         joins=joins or None,
        ...         where=filters,
        ...         order_by=[sort_by] if sort_by else None
        ...     ).build()
        >>>
        >>> sql, params = get_users(
        ...     filters={'users.active__eq': True},
        ...     include_orders=True,
        ...     sort_by='users.name ASC'
        ... )

    Note:
        - Table aliases are auto-generated (first 3+ characters) with conflict resolution
        - All string inputs are normalized to objects during initialization
        - First table in tables list becomes the FROM clause
        - JOIN deduplication removes exact duplicate JOIN strings while preserving order

    """

    def __init__(
        self,
        tables: list[Table],
        select: list[str | SelectColumn],
        joins: list[str | Join] | None = None,
        where: dict[str, Any] | list[WhereCondition] | None = None,
        group_by: list[str | GroupBy] | None = None,
        order_by: list[str | OrderBy] | None = None,
        limit: int | None = None,
    ):
        """Initialize QueryBuilder with SQL query components.

        Args:
            tables: List of Table objects defining database tables and relationships.
            select: List of columns to select (strings or SelectColumn objects).
            joins: Optional list of joins (strings or Join objects).
            where: Optional WHERE conditions (dict or list of WhereCondition objects).
            group_by: Optional GROUP BY columns (strings or GroupBy objects).
            order_by: Optional ORDER BY columns (strings or OrderBy objects).
            limit: Optional maximum number of rows to return.

        Raises:
            ValueError: If duplicate table names, invalid limit, or invalid WHERE format.

        """
        self._validate_unique_table_names(tables)
        if limit is not None and limit <= 0:
            raise ValueError("Limit must be a positive integer greater than 0")

        self.select = self._normalize_select(select)
        self.tables = {table.name: table for table in tables}
        self.joins = self._normalize_joins(joins or [])
        self.where = self._normalize_where(where or [])
        self.group_by = self._normalize_group_by(group_by or [])
        self.order_by = self._normalize_order_by(order_by or [])
        self.limit = limit

        self._table_aliases = {}
        self._generate_table_aliases(tables)

    @staticmethod
    def _validate_unique_table_names(tables: list[Table]) -> None:
        """Validate that all table names in the list are unique.

        Args:
            tables: List of Table objects to validate

        Raises:
            ValueError: If duplicate table names are found

        """
        table_names = [table.name for table in tables]
        if len(table_names) != len(set(table_names)):
            duplicates = [name for name in table_names if table_names.count(name) > 1]
            raise ValueError(f"Duplicate table names found: {set(duplicates)}")

    @staticmethod
    def _parse_table_column(item: str) -> tuple[str | None, str]:
        """Parse 'table.column' or 'column' format, handling SQL functions"""
        if "CASE" in item.upper():
            return None, item

        if "(" in item and ")" in item:
            table_match = re.search(r"(\w+)\.", item)
            if table_match:
                table_name = table_match.group(1)
                return table_name, item
            else:
                return None, item
        elif "." in item:
            table_name, col_name = item.split(".", 1)
            return table_name, col_name
        else:
            return None, item

    def _get_select_aliases(self) -> set[str]:
        """Extract aliases from SELECT columns"""
        return {col.alias for col in self.select if col.alias}

    def _normalize_select(self, select: list[str | SelectColumn]) -> list[SelectColumn]:
        """Convert string select to SelectColumn objects"""
        normalized = []
        for item in select:
            if isinstance(item, SelectColumn):
                normalized.append(item)
            else:
                table_name, col_name = self._parse_table_column(item)
                normalized.append(SelectColumn(col_name, table=table_name))
        return normalized

    def _normalize_joins(self, joins: list[str | Join]) -> list[Join]:
        """Convert string joins to Join objects"""
        normalized = []
        for join_item in joins:
            if isinstance(join_item, Join):
                normalized.append(join_item)
            else:
                join_type, join_key = self._parse_join_string(join_item)
                normalized.append(Join(join_key))
        return normalized

    def _normalize_where(self, where: dict[str, Any] | list[WhereCondition] | None) -> list[WhereCondition]:
        """Convert dict where to list of WhereCondition objects"""
        if where is None:
            return []

        if isinstance(where, dict):
            conditions = []
            for key, value in where.items():
                parts = key.split("__")

                if len(parts) == 2:
                    # Format: "column__operator" - default to AND
                    column_part, operator_suffix = parts
                    logical_op = "AND"
                elif len(parts) == 3:
                    # Format: "logical__column__operator"
                    logical_part, column_part, operator_suffix = parts
                    if logical_part.upper() not in ("AND", "OR"):
                        raise ValueError(f"Invalid logical operator '{logical_part}', must be 'and' or 'or'")
                    logical_op = logical_part.upper()
                else:
                    raise ValueError(
                        f"Invalid WHERE key format '{key}', expected 'column__operator' or 'logical__column__operator'"
                    )

                if operator_suffix not in _operator_map:
                    raise ValueError(f"Unknown operator suffix '{operator_suffix}'")

                table_name, col_name = self._parse_table_column(column_part)

                conditions.append(
                    WhereCondition(
                        column=col_name,
                        operator=_operator_map[operator_suffix],
                        value=value,
                        table=table_name,
                        logical_operator=logical_op,
                    )
                )
            return conditions
        return where

    def _normalize_group_by(self, group_by: list[str | GroupBy]) -> list[GroupBy]:
        """Convert string group_by to GroupBy objects"""
        normalized = []
        for item in group_by:
            if isinstance(item, GroupBy):
                normalized.append(item)
            else:
                table_name, col_name = self._parse_table_column(item)
                normalized.append(GroupBy(col_name, table=table_name))

        return normalized

    def _normalize_order_by(self, order_by: list[str | OrderBy]) -> list[OrderBy]:
        """Convert string order_by to OrderBy objects"""
        normalized = []
        for item in order_by:
            if isinstance(item, OrderBy):
                normalized.append(item)
            else:
                # Parse string: "users.name DESC" or "name" or "users.name"
                parts = item.split()
                if len(parts) == 1:
                    column = parts[0]
                    direction = "ASC"
                elif len(parts) == 2:
                    column, direction = parts
                    if direction.upper() not in ("ASC", "DESC"):
                        raise ValueError(f"Invalid ORDER BY direction '{direction}'")
                    direction = direction.upper()
                else:
                    raise ValueError(f"Invalid ORDER BY format '{item}', expected 'column' or 'column ASC/DESC'")

                table_name, col_name = self._parse_table_column(column)
                normalized.append(OrderBy(col_name, table=table_name, direction=direction))

        return normalized

    def _generate_table_aliases(self, tables: list[Table]):
        """Generate unique aliases for tables that don't have user-defined aliases"""
        aliases = {}
        used_aliases = set()

        # First pass: collect user-defined aliases
        for table in tables:
            if table.alias:
                if table.alias in used_aliases:
                    raise ValueError(f"Duplicate alias '{table.alias}' found")
                aliases[table.name] = table.alias
                used_aliases.add(table.alias)

        # Second pass: generate aliases for tables without user-defined ones
        for table in tables:
            if not table.alias:
                alias_length = 3
                alias = table.name[:alias_length]

                while alias in used_aliases:
                    alias_length += 1
                    alias = table.name[:alias_length]

                aliases[table.name] = alias
                used_aliases.add(alias)

        self._table_aliases = aliases

    @staticmethod
    def _parse_join_string(join_str: str) -> tuple[str, str]:
        """Parse join string to extract join type and table name

        Supports formats:
        - "orders" -> ("INNER JOIN", "orders")
        - "left join orders" -> ("LEFT JOIN", "orders")
        """
        parts = join_str.rsplit(" ", 1)

        if len(parts) == 1:
            return "INNER JOIN", parts[0]

        join_part, table_name = parts
        join_type_upper = join_part.upper()

        return join_type_upper, table_name

    def _build_direct_join(self, primary_table: Table, join_key: str, join_type: str) -> str:
        """Build a direct JOIN clause (no via chains)"""
        # Look up join definition
        if join_key not in primary_table.joins:
            raise ValueError(f"Join '{join_key}' not found in table '{primary_table.name}' joins")

        join_def = primary_table.joins[join_key]

        # Get target table name and validate it exists
        target_table_name = join_def.get_table_name(join_key)
        if target_table_name not in self._table_aliases:
            raise ValueError(f"Target table '{target_table_name}' not found in tables list")

        # Get aliases
        primary_alias = self._table_aliases[primary_table.name]
        target_alias = self._table_aliases[target_table_name]

        # Build JOIN condition
        join_condition = f"{primary_alias}.{join_def.source_column} = {target_alias}.{join_def.target_column}"

        # Return complete JOIN clause
        return f"{join_type} {target_table_name} {target_alias} ON {join_condition}"

    def _build_via_join_with_steps(self, primary_table: Table, join_obj: Join) -> list[str]:
        """Build JOIN clauses using ViaStep objects with custom join types"""

        def _find_join_to_table(from_table: Table, to_table_name: str) -> str:
            """Find join key from from_table to to_table_name"""
            for key, join_def in from_table.joins.items():
                if join_def.get_table_name(key) == to_table_name:
                    return key
            raise ValueError(f"No join found from '{from_table.name}' to '{to_table_name}'")

        join_clauses = []
        current_table = primary_table

        for via_step in join_obj.via_steps:
            if via_step.table_name not in self._table_aliases:
                raise ValueError(f"Via table '{via_step.table_name}' not found in tables list")

            via_join_key = _find_join_to_table(current_table, via_step.table_name)

            join_clause = self._build_direct_join(current_table, via_join_key, via_step.join_type.value)
            join_clauses.append(join_clause)

            # Move to next table in chain
            current_table = self.tables[via_step.table_name]

        return join_clauses

    def _generate_join_clauses(self) -> list[str]:
        """Generate JOIN clauses - now only handles Join objects"""
        join_clauses = []
        primary_table = list(self.tables.values())[0]

        for join_obj in self.joins:
            if join_obj.via_steps:
                via_clauses = self._build_via_join_with_steps(primary_table, join_obj)
                join_clauses.extend(via_clauses)
            else:
                join_clause = self._build_direct_join(primary_table, join_obj.join_key, JoinType.INNER.value)
                join_clauses.append(join_clause)

        return join_clauses

    def _generate_where_clauses(self) -> tuple[str, list]:
        """Generate WHERE clause with parameters and logical operators"""
        if not self.where:
            return "", []

        where_parts = []
        all_params = []

        for i, condition in enumerate(self.where):
            sql_part, params = condition.to_sql(self._table_aliases)

            if i > 0:
                sql_part = f"{condition.logical_operator} {sql_part}"

            where_parts.append(sql_part)

            if params is not None:
                if isinstance(params, list):
                    all_params.extend(params)
                else:
                    all_params.append(params)

        where_clause = " ".join(where_parts)
        return where_clause, all_params

    def _process_group_by(self) -> list[str]:
        """Process GROUP BY items"""
        if not self.group_by:
            return []

        select_aliases = self._get_select_aliases()
        return [item.to_sql(self._table_aliases, select_aliases) for item in self.group_by]

    def _process_order_by(self) -> list[str]:
        """Process ORDER BY items"""
        if not self.order_by:
            return []

        select_aliases = self._get_select_aliases()
        return [item.to_sql(self._table_aliases, select_aliases) for item in self.order_by]

    def build(self) -> tuple[str, list]:
        """Generate SQL query string and parameters from QueryBuilder configuration.

        Constructs a complete SQL SELECT statement using all components provided during
        initialization. Automatically handles table aliasing, JOIN deduplication, and
        parameterized queries for safe execution.

        Returns:
            tuple[str, list]: A tuple containing:
                - str: Complete SQL query string with newline-separated clauses
                - list: List of parameter values for parameterized query execution

        Examples:
            Basic query generation:

            >>> from sql_generator import QueryBuilder, Table
            >>> qb = QueryBuilder([Table('users')], ['users.name', 'users.email'])
            >>> sql, params = qb.build()
            >>> print(sql)
            SELECT use.name, use.email
            FROM users use
            >>> print(params)
            []

            Query with parameters:

            >>> qb = QueryBuilder(
            ...     [Table('users')],
            ...     ['users.name'],
            ...     where={'users.active__eq': True, 'users.age__gt': 18}
            ... )
            >>> sql, params = qb.build()
            >>> print(sql)
            SELECT use.name
            FROM users use
            WHERE use.active = %s AND use.age > %s
            >>> print(params)
            [True, 18]

            Complex query with all clauses:

            >>> from sql_generator import TableJoinAttribute, SelectColumn
            >>> users = Table('users', joins={'orders': TableJoinAttribute('id', 'user_id')})
            >>> orders = Table('orders')
            >>> qb = QueryBuilder(
            ...     [users, orders],
            ...     ['users.name', SelectColumn('COUNT(*)', alias='order_count')],
            ...     joins=['orders'],
            ...     where={'users.active__eq': True, 'orders.total__gt': 100},
            ...     group_by=['users.id', 'users.name'],
            ...     order_by=['order_count DESC'],
            ...     limit=50
            ... )
            >>> sql, params = qb.build()
            >>> print(sql)
            SELECT use.name, COUNT(*) AS order_count
            FROM users use
            INNER JOIN orders ord ON use.id = ord.user_id
            WHERE use.active = %s AND ord.total > %s
            GROUP BY use.id, use.name
            ORDER BY order_count DESC
            LIMIT 50
            >>> print(params)
            [True, 100]

            Using the generated SQL with database connections:

            >>> import psycopg
            >>> sql, params = qb.build()
            >>> cursor.execute(sql, params)
            >>> results = cursor.fetchall()

        Note:
            - Parameters use %s placeholders for PostgreSQL/MySQL compatibility
            - For SQLite, replace %s with ? in the returned SQL string
            - JOIN clauses are deduplicated while preserving order
            - Table aliases are automatically applied throughout the query
            - All clauses follow standard SQL order: SELECT, FROM, JOIN, WHERE, GROUP BY, ORDER BY, LIMIT

        """
        select_sql = [col.to_sql(self._table_aliases) for col in self.select]
        select_clause = f"SELECT {', '.join(select_sql)}"

        primary_table = list(self.tables.values())[0]
        primary_alias = self._table_aliases[primary_table.name]
        from_clause = f"FROM {primary_table.name} {primary_alias}"

        clauses = [select_clause, from_clause]
        all_params = []

        join_clauses = self._generate_join_clauses()
        join_clauses = list(dict.fromkeys(join_clauses))
        if join_clauses:
            clauses.extend(join_clauses)

        where_clause, where_params = self._generate_where_clauses()
        if where_clause:
            clauses.append(f"WHERE {where_clause}")
            all_params.extend(where_params)

        group_by_clauses = self._process_group_by()
        if group_by_clauses:
            clauses.append(f"GROUP BY {', '.join(group_by_clauses)}")

        order_by_clauses = self._process_order_by()
        if order_by_clauses:
            clauses.append(f"ORDER BY {', '.join(order_by_clauses)}")

        if self.limit:
            clauses.append(f"LIMIT {self.limit}")

        sql = "\n".join(clauses)
        return sql, all_params
