from unittest import TestCase

from sql_generator.QueryObjects import AggFunction, SelectColumn, Table
from sql_generator.select_query_generator import QueryBuilder
from tests.utils import _normalize_sql


class TestSelect(TestCase):

    def setUp(self):
        """Set up fictional database tables for testing"""
        self.users = Table("users", primary_key="id")
        self.orders = Table("orders", primary_key="id")
        self.profiles = Table("profiles", primary_key="profile_id")

    def test_simple_select_all_single_table(self):
        """Test SELECT * FROM single table"""
        qb = QueryBuilder(tables=[self.users], select=["*"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT * FROM users use")
        self.assertEqual(params, [])

    def test_simple_select_specific_columns_single_table(self):
        """Test SELECT specific columns FROM single table"""
        qb = QueryBuilder(tables=[self.users], select=["name", "email"])

        sql, params = qb.build()
        self.assertEqual(_normalize_sql(sql), "SELECT name, email FROM users use")
        self.assertEqual(params, [])

    def test_simple_select_with_table_prefix(self):
        """Test SELECT with explicit table.column format"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "users.email", "users.age"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, use.email, use.age FROM users use")
        self.assertEqual(params, [])

    def test_select_mixed_table_prefixed_and_unprefixed(self):
        """Test SELECT with mix of table.column and column formats"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "email", "users.age"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, email, use.age FROM users use")
        self.assertEqual(params, [])

    def test_select_with_expressions(self):
        """Test SELECT with SQL expressions"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "NOW()", "UPPER(users.email)"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, NOW(), UPPER(use.email) FROM users use")
        self.assertEqual(params, [])

    def test_select_duplicate_columns(self):
        """Test SELECT with duplicate column references"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "name", "users.name"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, name, use.name FROM users use")
        self.assertEqual(params, [])

    def test_select_non_standard_primary_key_table(self):
        """Test SELECT from table with non-standard primary key"""
        qb = QueryBuilder(tables=[self.profiles], select=["profiles.user_id", "profiles.bio"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT pro.user_id, pro.bio FROM profiles pro")
        self.assertEqual(params, [])

    def test_select_complex_expressions(self):
        """Test SELECT with complex SQL expressions and nested functions"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[
                "CONCAT(users.first_name, ' ', users.last_name)",
                "COALESCE(users.phone, 'N/A')",
                "LENGTH(users.email)",
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT CONCAT(use.first_name, ' ', use.last_name), "
            "COALESCE(use.phone, 'N/A'), LENGTH(use.email) FROM users use",
        )
        self.assertEqual(params, [])

    def test_select_expressions_without_table_references(self):
        """Test SELECT with expressions that don't reference table columns"""
        qb = QueryBuilder(tables=[self.users], select=["users.name", "CURRENT_DATE", "'Active' as status", "42"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, CURRENT_DATE, 'Active' as status, 42 FROM users use")
        self.assertEqual(params, [])

    def test_select_case_expressions(self):
        """Test SELECT with CASE expressions containing table references"""
        qb = QueryBuilder(
            tables=[self.users], select=["users.name", "CASE WHEN users.age >= 18 THEN 'Adult' ELSE 'Minor' END"]
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.name, CASE WHEN users.age >= 18 THEN 'Adult' ELSE 'Minor' END FROM users use",
        )
        self.assertEqual(params, [])

    def test_select_mathematical_expressions(self):
        """Test SELECT with mathematical expressions using table columns"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=["orders.id", "orders.total * 1.08", "ROUND(orders.total / orders.quantity, 2)"],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT ord.id, ord.total * 1.08, ROUND(ord.total / ord.quantity, 2) FROM orders ord"
        )
        self.assertEqual(params, [])

    def test_select_alias_generation_short_table_name(self):
        """Test table alias generation for short table names"""
        # Create a table with a name shorter than 3 chars to test edge case
        short_table = Table("ab", primary_key="id")

        qb = QueryBuilder(tables=[short_table], select=["ab.name"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT ab.name FROM ab ab")
        self.assertEqual(params, [])

    def test_select_column_with_aggregation(self):
        """Test SelectColumn with aggregate functions"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[
                SelectColumn("id", table="users", agg_function=AggFunction.COUNT),
                SelectColumn("age", table="users", agg_function=AggFunction.AVG),
                SelectColumn("name", table="users", agg_function=AggFunction.COUNT_DISTINCT),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT COUNT(use.id), AVG(use.age), COUNT(DISTINCT use.name) FROM users use"
        )
        self.assertEqual(params, [])

    def test_select_column_with_alias(self):
        """Test SelectColumn with aliases"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[
                SelectColumn("name", table="users", alias="full_name"),
                SelectColumn("email", table="users", alias="contact_email"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name AS full_name, use.email AS contact_email FROM users use")
        self.assertEqual(params, [])

    def test_select_column_with_distinct(self):
        """Test SelectColumn with DISTINCT"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[
                SelectColumn("status", table="users", distinct=True),
                SelectColumn("department", table="users", distinct=True),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT DISTINCT use.status, DISTINCT use.department FROM users use")
        self.assertEqual(params, [])

    def test_select_column_aggregation_with_alias(self):
        """Test SelectColumn with both aggregation and alias"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("id", table="orders", agg_function=AggFunction.COUNT, alias="total_orders"),
                SelectColumn("total", table="orders", agg_function=AggFunction.SUM, alias="revenue"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT COUNT(ord.id) AS total_orders, SUM(ord.total) AS revenue FROM orders ord"
        )
        self.assertEqual(params, [])

    def test_select_mixed_strings_and_select_columns(self):
        """Test mixing string columns and SelectColumn objects"""
        qb = QueryBuilder(
            tables=[self.users],
            select=[
                "users.name",
                SelectColumn("id", table="users", agg_function=AggFunction.COUNT, alias="user_count"),
                "users.email",
            ],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name, COUNT(use.id) AS user_count, use.email FROM users use")
        self.assertEqual(params, [])

    def test_select_column_without_table_reference(self):
        """Test SelectColumn without table specification"""
        qb = QueryBuilder(
            tables=[self.users], select=[SelectColumn("name"), SelectColumn("COUNT(*)", alias="total_count")]
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT name, COUNT(*) AS total_count FROM users use")
        self.assertEqual(params, [])

    def test_select_all_aggregate_functions(self):
        """Test all available aggregate functions"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=[
                SelectColumn("total", table="orders", agg_function=AggFunction.MIN),
                SelectColumn("total", table="orders", agg_function=AggFunction.MAX),
                SelectColumn("id", table="orders", agg_function=AggFunction.SUM),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT MIN(ord.total), MAX(ord.total), SUM(ord.id) FROM orders ord")
        self.assertEqual(params, [])

    def test_select_table_not_found_in_aliases(self):
        """Test SELECT with table reference not in query raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["nonexistent_table.name"])
            qb.build()

        self.assertIn("Table 'nonexistent_table' not found in aliases", str(context.exception))

    def test_select_column_object_table_not_found(self):
        """Test SelectColumn with table reference not in query raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=[SelectColumn("name", table="nonexistent_table")])
            qb.build()

        self.assertIn("Table 'nonexistent_table' not found in aliases", str(context.exception))
