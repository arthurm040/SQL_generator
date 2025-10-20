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
from sql_generator.select_query_generator import QueryBuilder
from tests.utils import _normalize_sql


class TestQueryBuilderIntegration(TestCase):

    def setUp(self):
        """Set up comprehensive fictional database for integration testing"""
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

    def test_comprehensive_query_with_all_features(self):
        """Test complex query using every QueryBuilder feature"""
        qb = QueryBuilder(
            tables=[self.users, self.orders, self.order_items, self.products, self.categories, self.profiles],
            select=[
                "users.name",
                SelectColumn("email", table="users", alias="user_email"),
                SelectColumn("total", table="orders", agg_function=AggFunction.SUM, alias="total_spent"),
                SelectColumn("id", table="order_items", agg_function=AggFunction.COUNT, alias="item_count"),
                SelectColumn("name", table="categories", distinct=True),
                "UPPER(products.name)",
                SelectColumn("YEAR(orders.created_at)", alias="order_year"),
                "profiles.bio",
            ],
            joins=[
                "orders",
                Join("profiles", via_steps=[ViaStep("profiles", JoinType.LEFT)]),
                Join(
                    "products",
                    via_steps=[
                        ViaStep("orders", JoinType.INNER),
                        ViaStep("order_items", JoinType.LEFT),
                        ViaStep("products", JoinType.INNER),
                    ],
                ),
                Join(
                    "categories",
                    via_steps=[
                        ViaStep("orders"),
                        ViaStep("order_items"),
                        ViaStep("products"),
                        ViaStep("categories", JoinType.LEFT),
                    ],
                ),
            ],
            where=[
                WhereCondition("age", Operator.GE, 18, table="users"),
                WhereCondition("status", Operator.IN, ["active", "premium"], table="users"),
                WhereCondition("total", Operator.BETWEEN, [100.0, 1000.0], table="orders", logical_operator="AND"),
                WhereCondition("name", Operator.LIKE, "%electronics%", table="categories", logical_operator="OR"),
                WhereCondition("deleted_at", Operator.IS_NULL, table="users", logical_operator="AND"),
                WhereCondition("price", Operator.GT, 50.0, table="products", logical_operator="AND"),
                WhereCondition("quantity", Operator.NE, 0, table="order_items", logical_operator="AND"),
                WhereCondition("description", Operator.ILIKE, "%premium%", table="products", logical_operator="OR"),
            ],
            group_by=[
                "users.name",
                GroupBy("email", table="users"),
                "order_year",
                GroupBy("name", table="categories"),
            ],
            order_by=[
                "total_spent DESC",
                OrderBy("item_count", direction="DESC"),
                "users.name ASC",
                OrderBy("order_year", direction="ASC"),
            ],
            limit=50,
        )

        sql, params = qb.build()
        print(sql)

        expected_sql = """SELECT use.name, use.email AS user_email, SUM(ord.total) AS total_spent, 
        COUNT(orde.id) AS item_count, 
        DISTINCT cat.name, UPPER(pro.name), YEAR(orders.created_at) AS order_year, prof.bio
        FROM users use
        INNER JOIN orders ord ON use.id = ord.user_id
        LEFT JOIN profiles prof ON use.id = prof.user_id
        LEFT JOIN order_items orde ON ord.id = orde.order_id
        INNER JOIN products pro ON orde.product_id = pro.id
        INNER JOIN order_items orde ON ord.id = orde.order_id
        LEFT JOIN categories cat ON pro.category_id = cat.id
        WHERE use.age >= %s AND use.status IN (%s, %s) AND ord.total BETWEEN %s AND %s OR cat.name LIKE %s 
        AND use.deleted_at IS NULL AND pro.price > %s AND orde.quantity != %s OR pro.description ILIKE %s
        GROUP BY use.name, use.email, order_year, cat.name
        ORDER BY total_spent DESC, item_count DESC, use.name ASC, order_year ASC
        LIMIT 50"""

        expected_params = [18, "active", "premium", 100.0, 1000.0, "%electronics%", 50.0, 0, "%premium%"]

        self.assertEqual(_normalize_sql(sql), _normalize_sql(expected_sql))
        self.assertEqual(params, expected_params)

    def test_minimal_query_for_comparison(self):
        """Test minimal query to contrast with comprehensive one"""
        qb = QueryBuilder(tables=[self.users], select=["*"])

        sql, params = qb.build()

        self.assertEqual(_normalize_sql(sql), "SELECT * FROM users use")
        self.assertEqual(params, [])
