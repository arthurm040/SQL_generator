from unittest import TestCase

from sql_generator.QueryObjects import Join, JoinType, Table, TableJoinAttribute, ViaStep
from sql_generator.select_query_generator import QueryBuilder
from tests.utils import _normalize_sql


class TestJoins(TestCase):

    def setUp(self):
        """Set up fictional database tables for testing"""
        self.users = Table("users", primary_key="id")
        self.orders = Table("orders", primary_key="id")
        self.products = Table("products", primary_key="id")
        self.order_items = Table("order_items", primary_key="id")
        self.categories = Table("categories", primary_key="id")
        self.profiles = Table("profiles", primary_key="profile_id")

        self.users.joins = {
            "orders": TableJoinAttribute(self.users.primary_key, "user_id"),
            "profiles": TableJoinAttribute(self.users.primary_key, "user_id"),
        }

        self.orders.joins = {
            "order_items": TableJoinAttribute(self.orders.primary_key, "order_id"),
            "users": TableJoinAttribute("user_id", self.users.primary_key),
        }

        self.products.joins = {
            "order_items": TableJoinAttribute(self.products.primary_key, "product_id"),
            "categories": TableJoinAttribute("category_id", self.categories.primary_key),
        }

        self.order_items.joins = {
            "orders": TableJoinAttribute("order_id", self.orders.primary_key),
            "products": TableJoinAttribute("product_id", self.products.primary_key),
        }

        self.categories.joins = {"products": TableJoinAttribute(self.categories.primary_key, "category_id")}

        self.profiles.joins = {"users": TableJoinAttribute("user_id", self.users.primary_key)}

    def test_simple_inner_join_string(self):
        """Test simple INNER JOIN using string join key"""
        qb = QueryBuilder(tables=[self.users, self.orders], select=["users.name", "orders.total"], joins=["orders"])

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.name, ord.total FROM users use INNER JOIN orders ord ON use.id = ord.user_id",
        )
        self.assertEqual(params, [])

    def test_simple_inner_join_object(self):
        """Test simple INNER JOIN using Join object"""
        qb = QueryBuilder(
            tables=[self.users, self.orders], select=["users.name", "orders.total"], joins=[Join("orders")]
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.name, ord.total FROM users use INNER JOIN orders ord ON use.id = ord.user_id",
        )
        self.assertEqual(params, [])

    def test_multiple_direct_joins(self):
        """Test multiple direct JOINs where each table connects to primary table"""
        qb = QueryBuilder(
            tables=[self.users, self.orders, self.profiles],
            select=["users.name", "orders.total", "profiles.bio"],
            joins=["orders", "profiles"],
        )

        sql, params = qb.build()

        expected = (
            "SELECT use.name, ord.total, pro.bio FROM users use "
            "INNER JOIN orders ord ON use.id = ord.user_id "
            "INNER JOIN profiles pro ON use.id = pro.user_id"
        )
        self.assertEqual(_normalize_sql(sql), expected)
        self.assertEqual(params, [])

    def test_join_with_different_join_types(self):
        """Test JOINs with explicit join types"""
        qb = QueryBuilder(
            tables=[self.users, self.orders],
            select=["users.name", "orders.total"],
            joins=[Join("orders", via_steps=[ViaStep("orders", JoinType.LEFT)])],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.name, ord.total FROM users use LEFT JOIN orders ord ON use.id = ord.user_id",
        )
        self.assertEqual(params, [])

    def test_join_via_chain(self):
        """Test JOIN through intermediate tables (via chain)"""
        qb = QueryBuilder(
            tables=[self.users, self.orders, self.order_items, self.products],
            select=["users.name", "products.name"],
            joins=[Join("products", via_steps=[ViaStep("orders"), ViaStep("order_items"), ViaStep("products")])],
        )

        sql, params = qb.build()

        expected = (
            "SELECT use.name, pro.name FROM users use "
            "INNER JOIN orders ord ON use.id = ord.user_id "
            "INNER JOIN order_items orde ON ord.id = orde.order_id "
            "INNER JOIN products pro ON orde.product_id = pro.id"
        )
        self.assertEqual(_normalize_sql(sql), expected)
        self.assertEqual(params, [])
