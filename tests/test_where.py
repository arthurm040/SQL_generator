from unittest import TestCase

from sql_generator.QueryObjects import Operator, Table, WhereCondition
from sql_generator.select_query_generator import QueryBuilder
from tests.utils import _normalize_sql


class TestWhere(TestCase):

    def setUp(self):
        """Set up fictional database tables for testing"""
        self.users = Table("users", primary_key="id")
        self.orders = Table("orders", primary_key="id")

    def test_simple_where_dict_equality(self):
        """Test simple WHERE with equality operator using dict"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"users.id__eq": 1})

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use WHERE use.id = %s")
        self.assertEqual(params, [1])

    def test_where_dict_without_table_prefix(self):
        """Test WHERE without table prefix - column only"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"id__eq": 1, "age__ge": 18})

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use WHERE id = %s AND age >= %s")
        self.assertEqual(params, [1, 18])

    def test_where_dict_with_table_prefix(self):
        """Test WHERE with table prefix"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where={"users.id__eq": 1, "users.age__ge": 18, "users.status__eq": "active"},
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.name FROM users use WHERE use.id = %s AND use.age >= %s AND use.status = %s",
        )
        self.assertEqual(params, [1, 18, "active"])

    def test_where_dict_mixed_prefix_and_no_prefix(self):
        """Test WHERE mixing prefixed and non-prefixed columns"""
        qb = QueryBuilder(
            tables=[self.users], select=["users.name"], where={"users.id__eq": 1, "age__ge": 18, "status__eq": "active"}
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name FROM users use WHERE use.id = %s AND age >= %s AND status = %s"
        )
        self.assertEqual(params, [1, 18, "active"])

    def test_where_dict_with_or_conditions(self):
        """Test WHERE with OR conditions using dict"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"users.id__eq": 1, "or__age__lt": 25})

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use WHERE use.id = %s OR age < %s")
        self.assertEqual(params, [1, 25])

    def test_where_dict_comparison_operators(self):
        """Test WHERE with various comparison operators using dict"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=["orders.id"],
            where={"orders.total__gt": 100, "orders.quantity__le": 5, "status__ne": "cancelled"},
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT ord.id FROM orders ord WHERE ord.total > %s AND ord.quantity <= %s AND status != %s",
        )
        self.assertEqual(params, [100, 5, "cancelled"])

    def test_where_dict_like_operator(self):
        """Test WHERE with LIKE operator using dict"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where={"users.name__like": "%john%", "email__ilike": "%@gmail.com"},
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name FROM users use WHERE use.name LIKE %s AND email ILIKE %s"
        )
        self.assertEqual(params, ["%john%", "%@gmail.com"])

    def test_where_dict_in_operator(self):
        """Test WHERE with IN operator using dict"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where={"status__in": ["active", "pending"], "users.role__not_in": ["admin", "super_admin"]},
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name FROM users use WHERE status IN (%s, %s) AND use.role NOT IN (%s, %s)"
        )
        self.assertEqual(params, ["active", "pending", "admin", "super_admin"])

    def test_where_dict_between_operator(self):
        """Test WHERE with BETWEEN operator using dict"""
        qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"users.age__between": [18, 65]})

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use WHERE use.age BETWEEN %s AND %s")
        self.assertEqual(params, [18, 65])

    def test_where_dict_null_operators(self):
        """Test WHERE with NULL operators using dict"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where={"deleted_at__is_null": None, "users.phone__is_not_null": None},
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name FROM users use WHERE deleted_at IS NULL AND use.phone IS NOT NULL"
        )
        self.assertEqual(params, [])

    def test_where_condition_object_basic(self):
        """Test WHERE using WhereCondition objects"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where=[WhereCondition("id", Operator.EQ, 1, table="users"), WhereCondition("age", Operator.GE, 18)],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use WHERE use.id = %s AND age >= %s")
        self.assertEqual(params, [1, 18])

    def test_where_condition_object_with_or_logic(self):
        """Test WHERE using WhereCondition objects with OR logic"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where=[
                WhereCondition("id", Operator.EQ, 1, table="users"),
                WhereCondition("age", Operator.LT, 25, logical_operator="OR"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT use.name FROM users use WHERE use.id = %s OR age < %s")
        self.assertEqual(params, [1, 25])

    def test_where_condition_object_all_operators(self):
        """Test WHERE using WhereCondition objects with various operators"""
        qb = QueryBuilder(
            tables=[self.orders],
            select=["orders.id"],
            where=[
                WhereCondition("total", Operator.GT, 100, table="orders"),
                WhereCondition("status", Operator.IN, ["active", "pending"]),
                WhereCondition("created_at", Operator.BETWEEN, ["2023-01-01", "2023-12-31"], table="orders"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT ord.id FROM orders ord WHERE ord.total > %s "
            "AND status IN (%s, %s) AND ord.created_at BETWEEN %s AND %s",
        )
        self.assertEqual(params, [100, "active", "pending", "2023-01-01", "2023-12-31"])

    def test_where_condition_object_null_operators(self):
        """Test WHERE using WhereCondition objects with NULL operators"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where=[
                WhereCondition("deleted_at", Operator.IS_NULL),
                WhereCondition("phone", Operator.IS_NOT_NULL, table="users"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name FROM users use WHERE deleted_at IS NULL AND use.phone IS NOT NULL"
        )
        self.assertEqual(params, [])

    def test_where_condition_object_like_operators(self):
        """Test WHERE using WhereCondition objects with LIKE operators"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where=[
                WhereCondition("name", Operator.LIKE, "%john%", table="users"),
                WhereCondition("email", Operator.ILIKE, "%@GMAIL.COM"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql), "SELECT use.name FROM users use WHERE use.name LIKE %s AND email ILIKE %s"
        )
        self.assertEqual(params, ["%john%", "%@GMAIL.COM"])

    def test_where_condition_complex_logical_combinations(self):
        """Test complex logical combinations with WhereCondition objects"""
        qb = QueryBuilder(
            tables=[self.users],
            select=["users.name"],
            where=[
                WhereCondition("age", Operator.GE, 18, table="users"),
                WhereCondition("status", Operator.EQ, "active"),
                WhereCondition("role", Operator.IN, ["user", "moderator"], logical_operator="OR"),
                WhereCondition("created_at", Operator.GT, "2023-01-01", table="users", logical_operator="AND"),
            ],
        )

        sql, params = qb.build()

        self.assertEqual(
            _normalize_sql(sql),
            "SELECT use.name FROM users use WHERE use.age >= %s "
            "AND status = %s OR role IN (%s, %s) AND use.created_at > %s",
        )
        self.assertEqual(params, [18, "active", "user", "moderator", "2023-01-01"])

    def test_where_dict_invalid_operator_suffix(self):
        """Test WHERE with invalid operator suffix raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"id__invalid": 1})
            qb.build()

        self.assertIn("Unknown operator suffix 'invalid'", str(context.exception))

    def test_where_dict_invalid_logical_operator(self):
        """Test WHERE with invalid logical operator raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"invalid__id__eq": 1})
            qb.build()

        self.assertIn("Invalid logical operator 'invalid'", str(context.exception))

    def test_where_dict_invalid_key_format(self):
        """Test WHERE with invalid key format raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"id__eq__extra__parts": 1})
            qb.build()

        self.assertIn("Invalid WHERE key format", str(context.exception))

    def test_where_dict_between_invalid_value_type(self):
        """Test BETWEEN operator with invalid value type raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"age__between": 25})
            qb.build()

        self.assertIn("BETWEEN operator requires a list/tuple of 2 values", str(context.exception))

    def test_where_dict_between_wrong_number_of_values(self):
        """Test BETWEEN operator with wrong number of values raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"age__between": [18, 25, 65]})
            qb.build()

        self.assertIn("BETWEEN operator requires a list/tuple of 2 values", str(context.exception))

    def test_where_dict_in_operator_invalid_value_type(self):
        """Test IN operator with invalid value type raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"status__in": "active"})
            qb.build()

        self.assertIn("IN operator requires a list/tuple of values", str(context.exception))

    def test_where_dict_not_in_operator_invalid_value_type(self):
        """Test NOT_IN operator with invalid value type raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"role__not_in": "admin"})
            qb.build()

        self.assertIn("NOT_IN operator requires a list/tuple of values", str(context.exception))

    def test_where_condition_object_invalid_direction(self):
        """Test WhereCondition with invalid logical operator"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(
                tables=[self.users],
                select=["users.name"],
                where=[WhereCondition("id", Operator.EQ, 1, logical_operator="INVALID")],
            )
            qb.build()
        self.assertIn("Invalid logical operator. Expected AND or OR", str(context.exception))

    def test_where_dict_table_not_found_in_aliases(self):
        """Test WHERE with table reference not in query raises error"""
        with self.assertRaises(ValueError) as context:
            qb = QueryBuilder(tables=[self.users], select=["users.name"], where={"nonexistent_table.id__eq": 1})
            qb.build()

        self.assertIn("Table 'nonexistent_table' not found in aliases", str(context.exception))
