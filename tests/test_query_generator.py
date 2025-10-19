"""Unit test for query generator module."""

from unittest import TestCase

from sql_generator.QueryObjects import AggFunction, Join, JoinType, SelectColumn, Table, TableJoinAttribute, ViaStep


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
        self.assertIsNone(table.joins)
        self.assertIsNone(table.alias)

    def test_table_with_direct_joins(self):
        """Test table with direct join definitions"""
        table = Table(
            "users",
            joins={"orders": TableJoinAttribute("id", "user_id"), "profiles": TableJoinAttribute("id", "user_id")},
        )

        self.assertEqual(table.name, "users")
        self.assertEqual(len(table.joins), 2)
        self.assertIn("orders", table.joins)
        self.assertIn("profiles", table.joins)

        orders_join = table.joins["orders"]
        self.assertEqual(orders_join.source_column, "id")
        self.assertEqual(orders_join.target_column, "user_id")
        self.assertIsNone(orders_join.table_name)

    def test_multiple_joins_same_table(self):
        """Test multiple joins to the same physical table"""
        table = Table(
            "users",
            joins={
                "billing_address": TableJoinAttribute("id", "user_id", table_name="addresses"),
                "shipping_address": TableJoinAttribute("id", "user_id", table_name="addresses"),
            },
        )

        billing = table.joins["billing_address"]
        shipping = table.joins["shipping_address"]

        self.assertEqual(billing.table_name, "addresses")
        self.assertEqual(shipping.table_name, "addresses")
        self.assertEqual(billing.target_column, "user_id")
        self.assertEqual(shipping.target_column, "user_id")

    def test_table_with_user_defined_alias(self):
        """Test creating a table with user-defined alias"""
        table = Table("users", alias="u")
        self.assertEqual(table.name, "users")
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
        self.assertEqual(table.alias, "u")
        self.assertEqual(len(table.joins), 2)
        self.assertIn("orders", table.joins)
        self.assertIn("profiles", table.joins)

    def test_table_alias_none_by_default(self):
        """Test that alias is None by default"""
        table = Table("users", joins={"orders": TableJoinAttribute("id", "user_id")})
        self.assertEqual(table.name, "users")
        self.assertIsNone(table.alias)
        self.assertIsNotNone(table.joins)

    def test_table_join_relationships(self):
        """Test that table join relationships are properly defined"""
        orders_table = Table("orders", joins={"order_items": TableJoinAttribute("id", "order_id")})

        order_items_table = Table("order_items", joins={"products": TableJoinAttribute("product_id", "id")})

        users_table = Table("users", joins={"orders": TableJoinAttribute("id", "user_id")})

        # Test that each table defines its direct relationships only
        self.assertEqual(len(users_table.joins), 1)
        self.assertEqual(len(orders_table.joins), 1)
        self.assertEqual(len(order_items_table.joins), 1)

        # Test join definitions
        users_orders = users_table.joins["orders"]
        self.assertEqual(users_orders.source_column, "id")
        self.assertEqual(users_orders.target_column, "user_id")

        orders_items = orders_table.joins["order_items"]
        self.assertEqual(orders_items.source_column, "id")
        self.assertEqual(orders_items.target_column, "order_id")


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
