"""Unit test for query generator module."""

from unittest import TestCase

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


class TestJoins(TestCase):

    def test_basic_join_creation(self):
        """Test creating a basic join with source and target columns"""
        join = TableJoinAttribute("id", "user_id")
        self.assertEqual(join.source_column, "id")
        self.assertEqual(join.target_column, "user_id")
        self.assertIsNone(join.table_name)

    def test_join_with_table_name_override(self):
        """Test join with explicit table name different from join key"""
        join = TableJoinAttribute("id", "user_id", table_name="addresses")
        self.assertEqual(join.table_name, "addresses")

    def test_get_table_name_with_default(self):
        """Test get_table_name returns join_key when table_name is None"""
        join = TableJoinAttribute("id", "user_id")
        self.assertEqual(join.get_table_name("orders"), "orders")

    def test_get_table_name_with_override(self):
        """Test get_table_name returns table_name when specified"""
        join = TableJoinAttribute("id", "user_id", table_name="addresses")
        self.assertEqual(join.get_table_name("billing_address"), "addresses")

    def test_get_table_name_empty_string_table_name(self):
        """Test get_table_name with empty string table_name falls back to join_key"""
        join = TableJoinAttribute("id", "user_id", table_name="")
        self.assertEqual(join.get_table_name("orders"), "orders")


class TestJoinObjects(TestCase):
    """Test the new Join and ViaStep classes"""

    def test_basic_join_creation(self):
        """Test creating a basic Join object"""
        from sql_generator.QueryObjects import Join

        join = Join("orders")
        self.assertEqual(join.join_key, "orders")
        self.assertIsNone(join.via_steps)

    def test_join_with_via_steps(self):
        """Test Join with ViaStep objects"""
        from sql_generator.QueryObjects import Join, JoinType, ViaStep

        join = Join(
            "products",
            via_steps=[
                ViaStep("orders", JoinType.INNER),
                ViaStep("order_items", JoinType.LEFT),
                ViaStep("products", JoinType.INNER),
            ],
        )

        self.assertEqual(join.join_key, "products")
        self.assertEqual(len(join.via_steps), 3)
        self.assertEqual(join.via_steps[0].table_name, "orders")
        self.assertEqual(join.via_steps[0].join_type, JoinType.INNER)
        self.assertEqual(join.via_steps[1].table_name, "order_items")
        self.assertEqual(join.via_steps[1].join_type, JoinType.LEFT)

    def test_via_step_creation(self):
        """Test creating ViaStep objects"""
        from sql_generator.QueryObjects import JoinType, ViaStep

        # Default INNER join
        step1 = ViaStep("orders")
        self.assertEqual(step1.table_name, "orders")
        self.assertEqual(step1.join_type, JoinType.INNER)

        # Explicit LEFT join
        step2 = ViaStep("profiles", JoinType.LEFT)
        self.assertEqual(step2.table_name, "profiles")
        self.assertEqual(step2.join_type, JoinType.LEFT)


class TestTable(TestCase):

    def test_basic_table_creation(self):
        """Test creating a table with just a name"""
        table = Table("users")
        self.assertEqual(table.name, "users")
        self.assertEqual(table.primary_key, None)
        self.assertIsNone(table.joins)
        self.assertIsNone(table.alias)

    def test_table_with_custom_primary_key(self):
        """Test creating a table with custom primary key"""
        table = Table("products", primary_key="product_id")
        self.assertEqual(table.name, "products")
        self.assertEqual(table.primary_key, "product_id")
        self.assertIsNone(table.joins)
        self.assertIsNone(table.alias)

    def test_table_with_direct_joins(self):
        """Test table with direct join definitions"""
        table = Table(
            "users",
            joins={"orders": TableJoinAttribute("id", "user_id"), "profiles": TableJoinAttribute("id", "user_id")},
        )

        self.assertEqual(table.name, "users")
        self.assertEqual(table.primary_key, None)
        self.assertEqual(len(table.joins), 2)
        self.assertIn("orders", table.joins)
        self.assertIn("profiles", table.joins)

        orders_join = table.joins["orders"]
        self.assertEqual(orders_join.source_column, "id")
        self.assertEqual(orders_join.target_column, "user_id")
        self.assertIsNone(orders_join.table_name)

    def test_table_with_user_defined_alias(self):
        """Test creating a table with user-defined alias"""
        table = Table("users", alias="u")
        self.assertEqual(table.name, "users")
        self.assertEqual(table.primary_key, None)
        self.assertEqual(table.alias, "u")
        self.assertIsNone(table.joins)

    def test_table_with_alias_and_joins(self):
        """Test table with both alias and join definitions"""
        table = Table(
            "users",
            alias="u",
            joins={"orders": TableJoinAttribute("id", "user_id"), "profiles": TableJoinAttribute("id", "user_id")},
        )

        self.assertEqual(table.name, "users")
        self.assertEqual(table.primary_key, None)
        self.assertEqual(table.alias, "u")
        self.assertEqual(len(table.joins), 2)
        self.assertIn("orders", table.joins)
        self.assertIn("profiles", table.joins)

    def test_table_alias_none_by_default(self):
        """Test that alias is None by default"""
        table = Table("users", joins={"orders": TableJoinAttribute("id", "user_id")})
        self.assertEqual(table.name, "users")
        self.assertEqual(table.primary_key, None)
        self.assertIsNone(table.alias)
        self.assertIsNotNone(table.joins)


class TestSelectColumn(TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.table_aliases = {"users": "u", "orders": "ord", "products": "pro"}

    def test_simple_column_with_table(self):
        """Test basic column with table reference"""
        col = SelectColumn("name", table="users")
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "u.name")

    def test_column_without_table(self):
        """Test column without table reference"""
        col = SelectColumn("NOW()")
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "NOW()")

    def test_column_with_alias(self):
        """Test column with alias"""
        col = SelectColumn("name", table="users", alias="user_name")
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "u.name AS user_name")

    def test_column_with_count_aggregate(self):
        """Test column with COUNT aggregate function"""
        col = SelectColumn("id", table="orders", agg_function=AggFunction.COUNT)
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "COUNT(ord.id)")

    def test_column_with_sum_aggregate_and_alias(self):
        """Test column with SUM aggregate and alias"""
        col = SelectColumn("total", table="orders", agg_function=AggFunction.SUM, alias="total_sales")
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "SUM(ord.total) AS total_sales")

    def test_column_with_count_distinct(self):
        """Test column with COUNT DISTINCT aggregate"""
        col = SelectColumn("category", table="products", agg_function=AggFunction.COUNT_DISTINCT)
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "COUNT(DISTINCT pro.category)")

    def test_column_with_distinct(self):
        """Test column with DISTINCT modifier"""
        col = SelectColumn("status", table="users", distinct=True)
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "DISTINCT u.status")

    def test_column_with_distinct_and_alias(self):
        """Test column with DISTINCT and alias"""
        col = SelectColumn("status", table="users", distinct=True, alias="unique_statuses")
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "DISTINCT u.status AS unique_statuses")

    def test_wildcard_column(self):
        """Test wildcard column selection"""
        col = SelectColumn("*", table="users")
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "u.*")

    def test_invalid_table_raises_error(self):
        """Test that invalid table name raises ValueError"""
        col = SelectColumn("name", table="invalid_table")
        with self.assertRaises(ValueError) as context:
            col.to_sql(self.table_aliases)
        self.assertIn("Table 'invalid_table' not found in aliases", str(context.exception))

    def test_all_aggregate_functions(self):
        """Test all supported aggregate functions"""
        test_cases = [
            (AggFunction.COUNT, "COUNT(u.id)"),
            (AggFunction.SUM, "SUM(u.id)"),
            (AggFunction.AVG, "AVG(u.id)"),
            (AggFunction.MIN, "MIN(u.id)"),
            (AggFunction.MAX, "MAX(u.id)"),
        ]

        for agg_func, expected in test_cases:
            with self.subTest(agg_func=agg_func):
                col = SelectColumn("id", table="users", agg_function=agg_func)
                result = col.to_sql(self.table_aliases)
                self.assertEqual(result, expected)

    def test_expression_without_table(self):
        """Test complex expression without table reference"""
        col = SelectColumn("CURRENT_TIMESTAMP", alias="now")
        result = col.to_sql(self.table_aliases)
        self.assertEqual(result, "CURRENT_TIMESTAMP AS now")


class TestViaStep(TestCase):
    """Test ViaStep dataclass"""

    def test_via_step_defaults(self):
        """Test ViaStep with default INNER join"""
        step = ViaStep("orders")
        self.assertEqual(step.table_name, "orders")
        self.assertEqual(step.join_type, JoinType.INNER)

    def test_via_step_explicit_join_type(self):
        """Test ViaStep with explicit join type"""
        step = ViaStep("profiles", JoinType.LEFT)
        self.assertEqual(step.table_name, "profiles")
        self.assertEqual(step.join_type, JoinType.LEFT)


class TestJoin(TestCase):
    """Test Join dataclass"""

    def test_join_without_via_steps(self):
        """Test Join with just join_key"""
        join = Join("orders")
        self.assertEqual(join.join_key, "orders")
        self.assertIsNone(join.via_steps)

    def test_join_with_via_steps(self):
        """Test Join with via_steps"""
        via_steps = [ViaStep("orders"), ViaStep("order_items", JoinType.LEFT)]
        join = Join("products", via_steps)

        self.assertEqual(join.join_key, "products")
        self.assertEqual(len(join.via_steps), 2)
        self.assertEqual(join.via_steps[0].table_name, "orders")
        self.assertEqual(join.via_steps[1].join_type, JoinType.LEFT)


class TestGroupBy(TestCase):
    """Test GroupBy dataclass"""

    def setUp(self):
        """Set up test fixtures"""
        self.table_aliases = {"users": "u", "orders": "ord"}
        self.select_aliases = {"total_orders"}

    def test_group_by_with_table(self):
        """Test GroupBy with table reference"""
        group_by = GroupBy("name", table="users")
        result = group_by.to_sql(self.table_aliases, self.select_aliases)
        self.assertEqual(result, "u.name")

    def test_group_by_without_table(self):
        """Test GroupBy without table reference"""
        group_by = GroupBy("category")
        result = group_by.to_sql(self.table_aliases, self.select_aliases)
        self.assertEqual(result, "category")

    def test_group_by_with_select_alias(self):
        """Test GroupBy using SELECT alias"""
        group_by = GroupBy("total_orders")
        result = group_by.to_sql(self.table_aliases, self.select_aliases)
        self.assertEqual(result, "total_orders")


class TestOrderBy(TestCase):
    """Test OrderBy dataclass"""

    def setUp(self):
        """Set up test fixtures"""
        self.table_aliases = {"users": "u", "orders": "ord"}
        self.select_aliases = {"total_orders"}

    def test_order_by_default_direction(self):
        """Test OrderBy with default ASC direction"""
        order_by = OrderBy("name", table="users")
        result = order_by.to_sql(self.table_aliases, self.select_aliases)
        self.assertEqual(result, "u.name ASC")

    def test_order_by_desc_direction(self):
        """Test OrderBy with DESC direction"""
        order_by = OrderBy("name", table="users", direction="DESC")
        result = order_by.to_sql(self.table_aliases, self.select_aliases)
        self.assertEqual(result, "u.name DESC")

    def test_order_by_invalid_direction(self):
        """Test OrderBy with invalid direction raises error"""
        with self.assertRaises(ValueError) as context:
            OrderBy("name", direction="INVALID")
        self.assertIn("Direction must be 'ASC' or 'DESC'", str(context.exception))

    def test_order_by_case_insensitive_direction(self):
        """Test OrderBy normalizes direction to uppercase"""
        order_by = OrderBy("name", direction="desc")
        self.assertEqual(order_by.direction, "DESC")

    def test_order_by_with_select_alias(self):
        """Test OrderBy using SELECT alias"""
        order_by = OrderBy("total_orders", direction="DESC")
        result = order_by.to_sql(self.table_aliases, self.select_aliases)
        self.assertEqual(result, "total_orders DESC")


class TestWhereCondition(TestCase):
    """Test WhereCondition class thoroughly"""

    def setUp(self):
        """Set up test fixtures"""
        self.table_aliases = {"users": "u", "orders": "ord", "products": "pro"}

    def test_basic_equality_condition(self):
        """Test basic equality condition"""
        condition = WhereCondition("age", Operator.EQ, 25, table="users")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "u.age = %s")
        self.assertEqual(params, 25)

    def test_condition_without_table(self):
        """Test condition without table reference"""
        condition = WhereCondition("status", Operator.EQ, "active")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "status = %s")
        self.assertEqual(params, "active")

    def test_greater_than_condition(self):
        """Test greater than condition"""
        condition = WhereCondition("price", Operator.GT, 100.0, table="products")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "pro.price > %s")
        self.assertEqual(params, 100.0)

    def test_like_condition(self):
        """Test LIKE pattern matching"""
        condition = WhereCondition("name", Operator.LIKE, "%john%", table="users")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "u.name LIKE %s")
        self.assertEqual(params, "%john%")

    def test_in_condition_with_list(self):
        """Test IN condition with list of values"""
        condition = WhereCondition("status", Operator.IN, ["active", "pending", "verified"])
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "status IN (%s, %s, %s)")
        self.assertEqual(params, ["active", "pending", "verified"])

    def test_in_condition_with_tuple(self):
        """Test IN condition with tuple of values"""
        condition = WhereCondition("id", Operator.IN, (1, 2, 3), table="users")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "u.id IN (%s, %s, %s)")
        self.assertEqual(params, [1, 2, 3])

    def test_not_in_condition(self):
        """Test NOT IN condition"""
        condition = WhereCondition("role", Operator.NOT_IN, ["admin", "super_admin"], table="users")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "u.role NOT IN (%s, %s)")
        self.assertEqual(params, ["admin", "super_admin"])

    def test_between_condition_with_list(self):
        """Test BETWEEN condition with list"""
        condition = WhereCondition("age", Operator.BETWEEN, [18, 65], table="users")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "u.age BETWEEN %s AND %s")
        self.assertEqual(params, [18, 65])

    def test_between_condition_with_tuple(self):
        """Test BETWEEN condition with tuple"""
        condition = WhereCondition("price", Operator.BETWEEN, (10.0, 100.0), table="products")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "pro.price BETWEEN %s AND %s")
        self.assertEqual(params, (10.0, 100.0))

    def test_is_null_condition(self):
        """Test IS NULL condition"""
        condition = WhereCondition("deleted_at", Operator.IS_NULL)
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "deleted_at IS NULL")
        self.assertIsNone(params)

    def test_is_not_null_condition(self):
        """Test IS NOT NULL condition"""
        condition = WhereCondition("email", Operator.IS_NOT_NULL, table="users")
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "u.email IS NOT NULL")
        self.assertIsNone(params)

    def test_logical_operator_defaults_to_and(self):
        """Test that logical_operator defaults to AND"""
        condition = WhereCondition("age", Operator.GE, 18)
        self.assertEqual(condition.logical_operator, "AND")

    def test_explicit_logical_operator(self):
        """Test setting explicit logical operator"""
        condition = WhereCondition("age", Operator.LT, 65, logical_operator="OR")
        self.assertEqual(condition.logical_operator, "OR")

    def test_invalid_table_raises_error(self):
        """Test that invalid table name raises ValueError"""
        condition = WhereCondition("name", Operator.EQ, "test", table="invalid_table")
        with self.assertRaises(ValueError) as context:
            condition.to_sql(self.table_aliases)
        self.assertIn("Table 'invalid_table' not found in aliases", str(context.exception))

    def test_between_with_wrong_number_of_values_raises_error(self):
        """Test BETWEEN with wrong number of values raises error"""
        # Too few values
        condition = WhereCondition("age", Operator.BETWEEN, [18])
        with self.assertRaises(ValueError) as context:
            condition.to_sql(self.table_aliases)
        self.assertIn("BETWEEN operator requires a list/tuple of 2 values", str(context.exception))

        # Too many values
        condition = WhereCondition("age", Operator.BETWEEN, [18, 25, 65])
        with self.assertRaises(ValueError) as context:
            condition.to_sql(self.table_aliases)
        self.assertIn("BETWEEN operator requires a list/tuple of 2 values", str(context.exception))

    def test_between_with_non_list_raises_error(self):
        """Test BETWEEN with non-list/tuple raises error"""
        condition = WhereCondition("age", Operator.BETWEEN, 25)
        with self.assertRaises(ValueError) as context:
            condition.to_sql(self.table_aliases)
        self.assertIn("BETWEEN operator requires a list/tuple of 2 values", str(context.exception))

    def test_in_with_non_list_raises_error(self):
        """Test IN with non-list/tuple raises error"""
        condition = WhereCondition("status", Operator.IN, "active")
        with self.assertRaises(ValueError) as context:
            condition.to_sql(self.table_aliases)
        self.assertIn("IN operator requires a list/tuple of values", str(context.exception))

    def test_not_in_with_non_list_raises_error(self):
        """Test NOT_IN with non-list/tuple raises error"""
        condition = WhereCondition("role", Operator.NOT_IN, "admin")
        with self.assertRaises(ValueError) as context:
            condition.to_sql(self.table_aliases)
        self.assertIn("NOT_IN operator requires a list/tuple of values", str(context.exception))

    def test_empty_in_list(self):
        """Test IN condition with empty list"""
        condition = WhereCondition("status", Operator.IN, [])
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "status IN ()")
        self.assertEqual(params, [])

    def test_single_item_in_list(self):
        """Test IN condition with single item"""
        condition = WhereCondition("status", Operator.IN, ["active"])
        sql, params = condition.to_sql(self.table_aliases)
        self.assertEqual(sql, "status IN (%s)")
        self.assertEqual(params, ["active"])

    def test_all_comparison_operators(self):
        """Test all comparison operators"""
        operators_tests = [
            (Operator.EQ, "="),
            (Operator.NE, "!="),
            (Operator.LT, "<"),
            (Operator.LE, "<="),
            (Operator.GT, ">"),
            (Operator.GE, ">="),
            (Operator.LIKE, "LIKE"),
            (Operator.ILIKE, "ILIKE"),
        ]

        for operator, expected_sql_op in operators_tests:
            with self.subTest(operator=operator):
                condition = WhereCondition("column", operator, "value")
                sql, params = condition.to_sql(self.table_aliases)
                self.assertEqual(sql, f"column {expected_sql_op} %s")
                self.assertEqual(params, "value")
