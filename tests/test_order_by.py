from unittest import TestCase

from sql_generator.QueryObjects import AggFunction, OrderBy, SelectColumn, Table
from sql_generator.select_query_generator import QueryBuilder
from tests.utils import _normalize_sql


class TestOrderBy(TestCase):

    def setUp(self):
        """Set up fictional database tables for testing"""
        self.users = Table("users", primary_key="id")
        self.orders = Table("orders", primary_key="id")

    def test_order_by_string_without_table_prefix_default_asc(self):
        """Test ORDER BY using string without table prefix, default ASC"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "users.age"], order_by=["name"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, use.age FROM users use ORDER BY name ASC")
        self.assertEqual(params, [])

    def test_order_by_string_with_explicit_direction(self):
        """Test ORDER BY using string with explicit ASC/DESC"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "users.age"], order_by=["name ASC", "age DESC"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, use.age FROM users use ORDER BY name ASC, age DESC")
        self.assertEqual(params, [])

    def test_order_by_string_with_table_prefix(self):
        """Test ORDER BY using string with table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name", "users.age"],
            order_by=["users.name DESC", "users.created_at ASC"],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name, use.age FROM users use ORDER BY use.name DESC, use.created_at ASC"
        )
        self.assertEqual(params, [])

    def test_order_by_string_mixed_prefix(self):
        """Test ORDER BY mixing prefixed and non-prefixed columns"""
        qb = QueryBuilder(
            tables=[self.orders], select=["orders.id", "orders.total"], order_by=["total DESC", "orders.created_at ASC"]
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT ord.id, ord.total FROM orders ord ORDER BY total DESC, ord.created_at ASC"
        )
        self.assertEqual(params, [])

    def test_order_by_object_without_table_prefix(self):
        """Test ORDER BY using OrderBy objects without table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name", "users.age"],
            order_by=[OrderBy("name"), OrderBy("age", direction="DESC")],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, use.age FROM users use ORDER BY name ASC, age DESC")
        self.assertEqual(params, [])

    def test_order_by_object_with_table_prefix(self):
        """Test ORDER BY using OrderBy objects with table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name", "users.age"],
            order_by=[
                OrderBy("name", table="users", direction="DESC"),
                OrderBy("created_at", table="users", direction="ASC"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name, use.age " "FROM users use ORDER BY use.name DESC, use.created_at ASC"
        )
        self.assertEqual(params, [])

    def test_order_by_object_mixed_prefix(self):
        """Test ORDER BY using OrderBy objects with mixed table prefixes"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=["orders.id", "orders.total"],
            order_by=[OrderBy("total", direction="DESC"), OrderBy("user_id", table="orders", direction="ASC")],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT ord.id, ord.total " "FROM orders ord ORDER BY total DESC, ord.user_id ASC"
        )
        self.assertEqual(params, [])

    def test_order_by_with_select_alias_reference(self):
        """Test ORDER BY referencing SELECT column aliases"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("total", table="orders", agg_function=AggFunction.SUM, alias="total_revenue"),
                SelectColumn("user_id", table="orders"),
            ],
            group_by=["orders.user_id"],
            order_by=[OrderBy("total_revenue", direction="DESC")],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT SUM(ord.total) AS total_revenue, ord.user_id "
            "FROM orders ord GROUP BY ord.user_id ORDER BY total_revenue DESC",
        )
        self.assertEqual(params, [])

    def test_order_by_mixed_strings_and_objects(self):
        """Test ORDER BY mixing string columns and OrderBy objects"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=["orders.id", "orders.total", "orders.status"],
            order_by=[
                "status ASC",  # String with direction
                OrderBy("total", direction="DESC"),
                "orders.created_at DESC",
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT ord.id, ord.total, ord.status "
            "FROM orders ord ORDER BY status ASC, total DESC, ord.created_at DESC",
        )
        self.assertEqual(params, [])

    def test_order_by_case_insensitive_direction(self):
        """Test ORDER BY with case-insensitive direction parsing"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], order_by=["name desc", "users.age ASC"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use ORDER BY name DESC, use.age ASC")
        self.assertEqual(params, [])

    def test_order_by_string_invalid_direction(self):
        """Test ORDER BY string with invalid direction raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], order_by=["name INVALID"])
            qb.build()

        self.assertIn("Invalid ORDER BY direction 'INVALID'", str(context.exception))

    def test_order_by_string_too_many_parts(self):
        """Test ORDER BY string with too many parts raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], order_by=["name ASC EXTRA PARTS"])
            qb.build()

        self.assertIn("Invalid ORDER BY format", str(context.exception))

    def test_order_by_object_invalid_direction(self):
        """Test OrderBy object with invalid direction raises error"""
        with self.assertRaises(ValueError) as context:
            OrderBy("name", direction="INVALID")

        self.assertIn("Direction must be 'ASC' or 'DESC'", str(context.exception))

    def test_order_by_table_not_found_in_aliases(self):
        """Test ORDER BY with table reference not in query raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], order_by=["nonexistent_table.name ASC"])
            qb.build()

        self.assertIn("Table 'nonexistent_table' not found in aliases", str(context.exception))

    def test_order_by_object_table_not_found_in_aliases(self):
        """Test OrderBy object with table reference not in query raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(
                tables=[self.users], select=["users.name"], order_by=[OrderBy("name", table="nonexistent_table")]
            )
            qb.build()

        self.assertIn("Table 'nonexistent_table' not found in aliases", str(context.exception))

    def test_order_by_empty_string(self):
        """Test ORDER BY with empty string raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], order_by=[""])
            qb.build()

        self.assertIn("Invalid ORDER BY format", str(context.exception))
