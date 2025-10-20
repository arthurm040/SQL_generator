from unittest import TestCase

from sql_generator.QueryObjects import AggFunction, OrderBy, SelectColumn, Table
from sql_generator.select_query_generator import QueryBuilder
from tests.utils import _normalize_sql


class TestLimit(TestCase):

    def setUp(self):
        """Set up fictional database tables for testing"""
        self.users = Table("users", primary_key="id")
        self.orders = Table("orders", primary_key="id")

    def test_limit_basic(self):
        """Test basic LIMIT clause"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "users.email"], limit=10)

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, use.email FROM users use LIMIT 10")
        self.assertEqual(params, [])

    def test_limit_with_order_by(self):
        """Test LIMIT with ORDER BY clause"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "users.age"], order_by=["users.age DESC"], limit=5)

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, use.age FROM users use ORDER BY use.age DESC LIMIT 5")
        self.assertEqual(params, [])

    def test_limit_with_where_clause(self):
        """Test LIMIT with WHERE clause"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"users.age__ge": 18}, limit=20)

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use WHERE use.age >= %s LIMIT 20")
        self.assertEqual(params, [18])

    def test_limit_with_aggregation_and_group_by(self):
        """Test LIMIT with GROUP BY and aggregation"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("user_id", table="orders"),
                SelectColumn("total", table="orders", agg_function=AggFunction.SUM, alias="total_spent"),
            ],
            group_by=["orders.user_id"],
            order_by=[OrderBy("total_spent", direction="DESC")],
            limit=10,
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT ord.user_id, SUM(ord.total) AS total_spent FROM orders ord "
            "GROUP BY ord.user_id ORDER BY total_spent DESC LIMIT 10",
        )
        self.assertEqual(params, [])

    def test_limit_one(self):
        """Test LIMIT 1 (common use case)"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], order_by=["users.created_at DESC"], limit=1)

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use ORDER BY use.created_at DESC LIMIT 1")
        self.assertEqual(params, [])

    def test_limit_large_number(self):
        """Test LIMIT with large number"""
        qb = QueryBuilder(tables=[self.users], select=["users.id"], limit=1000000)

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.id FROM users use LIMIT 1000000")
        self.assertEqual(params, [])

    def test_no_limit_clause(self):
        """Test query without LIMIT clause"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use")
        self.assertEqual(params, [])

    # Negative tests
    def test_limit_zero_raises_error(self):
        """Test LIMIT 0 raises error"""
        with self.assertRaises(ValueError) as context:
            QueryBuilder(tables=[self.users], select=["users.name"], limit=0)

        self.assertIn("Limit must be a positive integer greater than 0", str(context.exception))

    def test_limit_negative_raises_error(self):
        """Test negative LIMIT raises error"""
        with self.assertRaises(ValueError) as context:
            QueryBuilder(tables=[self.users], select=["users.name"], limit=-5)

        self.assertIn("Limit must be a positive integer greater than 0", str(context.exception))

    def test_limit_none_is_valid(self):
        """Test LIMIT None is valid (no limit)"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], limit=None)

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use")
        self.assertEqual(params, [])
