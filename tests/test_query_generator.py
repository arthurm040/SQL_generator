"""Unit test for query generator module."""

from unittest import TestCase

from src.sql_generator.query_generator import Joins, Table


class TestJoins(TestCase):

    def test_basic_join_creation(self):
        """Test creating a basic join with source and target columns"""
        join = Joins("id", "user_id")
        self.assertEqual(join.source_column, "id")
        self.assertEqual(join.target_column, "user_id")
        self.assertIsNone(join.table_name)
        self.assertIsNone(join.via)

    def test_join_with_table_name_override(self):
        """Test join with explicit table name different from join key"""
        join = Joins("id", "user_id", table_name="addresses")
        self.assertEqual(join.table_name, "addresses")

    def test_join_with_via_tables(self):
        """Test indirect join with via tables"""
        orders_table = Table("orders")
        order_items_table = Table("order_items")

        join = Joins("id", "product_id", via=[orders_table, order_items_table])
        self.assertEqual(len(join.via), 2)
        self.assertEqual(join.via[0].name, "orders")
        self.assertEqual(join.via[1].name, "order_items")

    def test_get_table_name_with_default(self):
        """Test get_table_name returns join_key when table_name is None"""
        join = Joins("id", "user_id")
        self.assertEqual(join.get_table_name("orders"), "orders")

    def test_get_table_name_with_override(self):
        """Test get_table_name returns table_name when specified"""
        join = Joins("id", "user_id", table_name="addresses")
        self.assertEqual(join.get_table_name("billing_address"), "addresses")

    def test_get_table_name_empty_string_table_name(self):
        """Test get_table_name with empty string table_name falls back to join_key"""
        join = Joins("id", "user_id", table_name="")
        self.assertEqual(join.get_table_name("orders"), "orders")


class TestTable(TestCase):

    def test_basic_table_creation(self):
        """Test creating a table with just a name"""
        table = Table("users")
        self.assertEqual(table.name, "users")
        self.assertIsNone(table.joins)

    def test_table_with_direct_joins(self):
        """Test table with direct join definitions"""
        table = Table("users", joins={"orders": Joins("id", "user_id"), "profiles": Joins("id", "user_id")})

        self.assertEqual(table.name, "users")
        self.assertEqual(len(table.joins), 2)
        self.assertIn("orders", table.joins)
        self.assertIn("profiles", table.joins)

        orders_join = table.joins["orders"]
        self.assertEqual(orders_join.source_column, "id")
        self.assertEqual(orders_join.target_column, "user_id")

    def test_table_with_indirect_joins(self):
        """Test table with via chain joins"""
        orders_table = Table("orders", joins={"order_items": Joins("id", "order_id")})

        order_items_table = Table("order_items", joins={"products": Joins("id", "product_id")})

        users_table = Table(
            "users",
            joins={
                "orders": Joins("id", "user_id"),
                "products": Joins("id", "product_id", via=[orders_table, order_items_table]),
            },
        )

        products_join = users_table.joins["products"]
        self.assertEqual(len(products_join.via), 2)
        self.assertEqual(products_join.via[0].name, "orders")
        self.assertEqual(products_join.via[1].name, "order_items")

    def test_multiple_joins_same_table(self):
        """Test multiple joins to the same physical table"""
        table = Table(
            "users",
            joins={
                "billing_address": Joins("id", "user_id", table_name="addresses"),
                "shipping_address": Joins("id", "user_id", table_name="addresses"),
            },
        )

        billing = table.joins["billing_address"]
        shipping = table.joins["shipping_address"]

        self.assertEqual(billing.table_name, "addresses")
        self.assertEqual(shipping.table_name, "addresses")
        self.assertEqual(billing.target_column, "user_id")
        self.assertEqual(shipping.target_column, "user_id")
