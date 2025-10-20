from unittest import TestCase

from sql_generator.QueryObjects import AggFunction, GroupBy, SelectColumn, Table
from sql_generator.select_query_generator import QueryBuilder
from tests.utils import _normalize_sql


class TestGroupBy(TestCase):

    def setUp(self):
        """Set up fictional database tables for testing"""
        self.users = Table("users", primary_key="id")
        self.orders = Table("orders", primary_key="id")

    def test_group_by_string_without_table_prefix(self):
        """Test GROUP BY using string without table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[SelectColumn("status"), SelectColumn("id", agg_function=AggFunction.COUNT, alias="count")],
            group_by=["status"],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT status, COUNT(id) AS count FROM users use GROUP BY status")
        self.assertEqual(params, [])

    def test_group_by_string_with_table_prefix(self):
        """Test GROUP BY using string with table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[
                SelectColumn("status", table="users"),
                SelectColumn("id", table="users", agg_function=AggFunction.COUNT, alias="count"),
            ],
            group_by=["users.status", "users.department"],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.status, COUNT(use.id) AS count FROM users use GROUP BY use.status, use.department",
        )
        self.assertEqual(params, [])

    def test_group_by_string_mixed_prefix(self):
        """Test GROUP BY mixing prefixed and non-prefixed columns"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("status"),
                SelectColumn("total", table="orders", agg_function=AggFunction.SUM, alias="total_revenue"),
            ],
            group_by=["status", "orders.user_id"],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT status, SUM(ord.total) AS total_revenue FROM orders ord GROUP BY status, ord.user_id",
        )
        self.assertEqual(params, [])

    def test_group_by_multiple_columns_string(self):
        """Test GROUP BY with multiple columns using strings"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("status", table="orders"),
                SelectColumn("user_id", table="orders"),
                SelectColumn("id", table="orders", agg_function=AggFunction.COUNT, alias="order_count"),
            ],
            group_by=["orders.status", "orders.user_id"],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT ord.status, ord.user_id, COUNT(ord.id) "
            "AS order_count FROM orders ord GROUP BY ord.status, ord.user_id",
        )
        self.assertEqual(params, [])

    def test_group_by_object_without_table_prefix(self):
        """Test GROUP BY using GroupBy objects without table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[SelectColumn("status"), SelectColumn("id", agg_function=AggFunction.COUNT, alias="count")],
            group_by=[GroupBy("status")],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT status, COUNT(id) AS count FROM users use GROUP BY status")
        self.assertEqual(params, [])

    def test_group_by_object_with_table_prefix(self):
        """Test GROUP BY using GroupBy objects with table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[
                SelectColumn("status", table="users"),
                SelectColumn("id", table="users", agg_function=AggFunction.COUNT, alias="count"),
            ],
            group_by=[GroupBy("status", table="users"), GroupBy("department", table="users")],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.status, COUNT(use.id) AS count FROM users use GROUP BY use.status, use.department",
        )
        self.assertEqual(params, [])

    def test_group_by_object_mixed_prefix(self):
        """Test GROUP BY using GroupBy objects with mixed table prefixes"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("status"),
                SelectColumn("total", table="orders", agg_function=AggFunction.AVG, alias="avg_total"),
            ],
            group_by=[GroupBy("status"), GroupBy("user_id", table="orders")],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT status, AVG(ord.total) AS avg_total FROM orders ord GROUP BY status, ord.user_id",
        )
        self.assertEqual(params, [])

    def test_group_by_with_select_alias_reference(self):
        """Test GROUP BY referencing SELECT column aliases"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("YEAR(created_at)", alias="order_year"),
                SelectColumn("id", agg_function=AggFunction.COUNT, alias="count"),
            ],
            group_by=[GroupBy("order_year")],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT YEAR(created_at) AS order_year, COUNT(id) AS count FROM orders ord GROUP BY order_year",
        )
        self.assertEqual(params, [])

    def test_group_by_mixed_strings_and_objects(self):
        """Test GROUP BY mixing string columns and GroupBy objects"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("status"),
                SelectColumn("user_id", table="orders"),
                SelectColumn("id", agg_function=AggFunction.COUNT, alias="count"),
            ],
            group_by=["status", GroupBy("user_id", table="orders"), "orders.created_date"],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT status, ord.user_id, COUNT(id) "
            "AS count FROM orders ord GROUP BY status, ord.user_id, ord.created_date",
        )
        self.assertEqual(params, [])

    def test_group_by_table_not_found_in_aliases(self):
        """Test GROUP BY with table reference not in query raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(
                tables=[self.users],
                select=[SelectColumn("status"), SelectColumn("id", agg_function=AggFunction.COUNT)],
                group_by=["nonexistent_table.status"],
            )
            qb.build()

        self.assertIn("Table 'nonexistent_table' not found in aliases", str(context.exception))

    def test_group_by_object_table_not_found_in_aliases(self):
        """Test GroupBy object with table reference not in query raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(
                tables=[self.users],
                select=[SelectColumn("status"), SelectColumn("id", agg_function=AggFunction.COUNT)],
                group_by=[GroupBy("status", table="nonexistent_table")],
            )
            qb.build()

        self.assertIn("Table 'nonexistent_table' not found in aliases", str(context.exception))

    def test_group_by_without_aggregate_functions(self):
        """Test GROUP BY without aggregate functions in SELECT (should work but might be logically questionable)"""
        qb = QueryBuilder(
            tables=[self.users], select=[SelectColumn("status"), SelectColumn("name")], group_by=["status"]
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT status, name FROM users use GROUP BY status")
        self.assertEqual(params, [])

    def test_group_by_column_not_in_select_or_aggregate(self):
        """Test GROUP BY with column not in SELECT clause (valid SQL but might be confusing)"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[SelectColumn("id", agg_function=AggFunction.COUNT, alias="count")],
            group_by=["status"],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT COUNT(id) AS count FROM users use GROUP BY status")
        self.assertEqual(params, [])
