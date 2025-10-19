from sql_generator.QueryObjects import Join, JoinType, SelectColumn, Table


class QueryBuilder:
    def __init__(
        self,
        tables: list[Table],
        select: list[str | SelectColumn],
        joins: list[str] | Join | None = None,
        where: list[dict] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
    ):
        """Build SQL queries using constructor arguments.

        Args:
            tables: List of Table objects, first table becomes FROM clause
            select: List of column references like ['users.name', 'orders.total']
            joins: List of join keys to include (optional)
            where: List of condition dictionaries for OR logic (optional)
            order_by: List of columns to order by (optional)
            limit: Maximum number of rows to return (optional)

        """
        self._validate_unique_table_names(tables)
        self.tables = {table.name: table for table in tables}
        self.joins = joins or []
        self.where = where or []
        self.order_by = order_by or []
        self.limit = limit

        self._table_aliases = {}
        self._column_aliases = {}
        self._generate_table_aliases(tables)
        self._convert_columns_to_aliases(select)

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

    def _convert_columns_to_aliases(self, columns: list[str]):
        """Convert table.column references to alias.column

        Raises:
            ValueError: If a referenced table is not found in the tables list

        """
        aliased_columns = []

        for column in columns:
            if isinstance(column, SelectColumn):
                aliased_columns.append(column.to_sql(self._table_aliases))
            else:
                if "." in column:
                    table_name, col_name = column.split(".", 1)
                    if table_name in self._table_aliases:
                        aliased_columns.append(f"{self._table_aliases[table_name]}.{col_name}")
                    else:
                        raise ValueError(
                            f"Table '{table_name}' not found in tables list. "
                            f"Available tables: {list(self._table_aliases.keys())}"
                        )
                else:
                    aliased_columns.append(column)  # No table prefix

        self._column_aliases = aliased_columns

    @staticmethod
    def _find_join_to_table(from_table: Table, to_table_name: str) -> str:
        """Find join key from from_table to to_table_name"""
        for key, join_def in from_table.joins.items():
            if join_def.get_table_name(key) == to_table_name:
                return key
        raise ValueError(f"No join found from '{from_table.name}' to '{to_table_name}'")

    @staticmethod
    def _parse_join_string(join_str: str) -> tuple[str, str]:
        """Parse join string to extract join type and table name

        Supports formats:
        - "orders" -> ("INNER JOIN", "orders")
        - "left join orders" -> ("LEFT JOIN", "orders")
        """
        parts = join_str.rsplit(" ", 1)

        if len(parts) == 1:
            # No spaces, just table name
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
        join_clauses = []
        current_table = primary_table

        for via_step in join_obj.via_steps:
            # Validate via table exists
            if via_step.table_name not in self._table_aliases:
                raise ValueError(f"Via table '{via_step.table_name}' not found in tables list")

            # Find join key from current table to via table
            via_join_key = self._find_join_to_table(current_table, via_step.table_name)

            # Build join clause with specified join type
            join_clause = self._build_direct_join(current_table, via_join_key, via_step.join_type.value)
            join_clauses.append(join_clause)

            # Move to next table in chain
            current_table = self.tables[via_step.table_name]

        return join_clauses

    def _generate_join_clauses(self) -> list[str]:
        """Generate JOIN clauses - handles both direct joins and via chains"""
        join_clauses = []
        primary_table = list(self.tables.values())[0]

        if isinstance(self.joins, list):
            for join_item in self.joins:
                if isinstance(join_item, Join):
                    if join_item.via_steps:
                        # Handle via chain with custom join types
                        via_clauses = self._build_via_join_with_steps(primary_table, join_item)
                        join_clauses.extend(via_clauses)
                    else:
                        join_clause = self._build_direct_join(primary_table, join_item.join_key, JoinType.INNER.value)
                        join_clauses.append(join_clause)
                else:
                    # String join - parse for join type
                    join_type, join_key = self._parse_join_string(join_item)
                    join_clause = self._build_direct_join(primary_table, join_key, join_type)
                    join_clauses.append(join_clause)
        else:
            if self.joins.via_steps:
                # Handle via chain with custom join types
                via_clauses = self._build_via_join_with_steps(primary_table, self.joins)
                join_clauses.extend(via_clauses)
            else:
                join_clause = self._build_direct_join(primary_table, self.joins.join_key, JoinType.INNER.value)
                join_clauses.append(join_clause)

        return join_clauses

    def build(self) -> tuple[str, dict]:
        """Generate SQL query and parameters"""
        # Build all clause components
        select_clause = f"SELECT {', '.join(self._column_aliases)}"

        primary_table = list(self.tables.values())[0]
        primary_alias = self._table_aliases[primary_table.name]
        from_clause = f"FROM {primary_table.name} {primary_alias}"

        # Collect all clauses in order
        clauses = [select_clause, from_clause]

        # Add JOIN clauses
        join_clauses = self._generate_join_clauses()
        if join_clauses:
            clauses.extend(join_clauses)

        # TODO: Add WHERE clauses
        # where_clauses = self._generate_where_clauses()
        # if where_clauses:
        #     clauses.append(f"WHERE {where_clauses}")

        # TODO: Add ORDER BY
        # if self.order_by:
        #     clauses.append(f"ORDER BY {', '.join(self.order_by)}")

        # TODO: Add LIMIT
        # if self.limit:
        #     clauses.append(f"LIMIT {self.limit}")

        sql = " ".join(clauses)
        params = {}

        return sql, params
