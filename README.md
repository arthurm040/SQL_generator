# SQL Generator

Dynamic SQL query builder for Python that **eliminates complex if/else logic** for dynamic WHERE clauses and JOINs. Build queries using a **constructor-based API** with automatic table aliasing and relationship management.

**Perfect for APIs, admin interfaces, reporting systems, and any application that needs dynamic SQL generation.**

## Installation

```bash
pip install sql-query-builder-py
```

**Requirements:** Python 3.12+

## The Problem This Solves

**Before: Complex Dynamic Query Logic**

```python
# Traditional approach - messy and error-prone
def build_user_query(include_orders=False, active_only=False, min_age=None):
    sql = "SELECT u.name"
    params = []
    
    if include_orders:
        sql += ", o.total"
        
    sql += " FROM users u"
    
    if include_orders:
        sql += " LEFT JOIN orders o ON u.id = o.user_id"
        
    conditions = []
    if active_only:
        conditions.append("u.active = %s")
        params.append(True)
        
    if min_age:
        conditions.append("u.age >= %s") 
        params.append(min_age)
        
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
        
    return sql, params
```

**After: Clean Constructor-Based API**

```python
from sql_generator import QueryBuilder, Table, TableJoinAttribute

# Define relationships once
users = Table('users', joins={
    'orders': TableJoinAttribute('id', 'user_id')
})
orders = Table('orders')

# Build queries declaratively
def build_user_query(include_orders=False, active_only=False, min_age=None):
    where_conditions = {}
    if active_only:
        where_conditions['users.active__eq'] = True
    if min_age:
        where_conditions['users.age__gte'] = min_age
        
    return QueryBuilder(
        tables=[users, orders] if include_orders else [users],
        select=['users.name'] + (['orders.total'] if include_orders else []),
        joins=['orders'] if include_orders else None,
        where=where_conditions or None
    ).build()
```

## Key Features

🚀 **Constructor-Based API** - Perfect for dynamic query generation - no method chaining required

🏷️ **Automatic Table Aliasing** - Generates unique 3+ character aliases with conflict resolution

🔗 **Flexible JOIN System** - Direct joins, via chains, and mixed join types

🎯 **Django-Style WHERE Conditions** - `{'users.id__eq': 1, 'or__age__gt': 18}`

🛡️ **Parameterized Queries** - Safe SQL with automatic parameter binding

✨ **Hybrid Input Support** - Use strings or objects for all query components

## Quick Start Examples

### Basic Query

```python
from sql_generator import QueryBuilder, Table, TableJoinAttribute

# Define table relationships
users = Table('users', joins={
    'orders': TableJoinAttribute('id', 'user_id')
})
orders = Table('orders')

# Simple query
qb = QueryBuilder([users], ['users.name', 'users.email'])
sql, params = qb.build()

print(sql)
# SELECT use.name, use.email
# FROM users use
```

### Query with JOINs and WHERE

```python
# Complex query with relationships
qb = QueryBuilder(
    tables=[users, orders],
    select=['users.name', 'orders.total'],
    joins=['orders'],
    where={
        'users.active__eq': True,
        'orders.total__gte': 100
    }
)

sql, params = qb.build()
print(sql)
# SELECT use.name, ord.total
# FROM users use
# INNER JOIN orders ord ON use.id = ord.user_id  
# WHERE use.active = %s AND ord.total >= %s

print(params)
# [True, 100]
```

### Advanced Features

```python
from sql_generator import SelectColumn, AggFunction, Join, ViaStep, JoinType

# Aggregation with custom aliases
qb = QueryBuilder(
    tables=[users, orders],
    select=[
        'users.name',
        SelectColumn('COUNT(*)', alias='order_count'),
        SelectColumn('total', table='orders', agg_function=AggFunction.SUM, alias='revenue')
    ],
    joins=['orders'],
    where={'users.active__eq': True},
    group_by=['users.id', 'users.name'],
    order_by=['revenue DESC'],
    limit=10
)
```

### Dynamic Query Generation

```python
# Perfect for APIs and dynamic filtering
def get_users(filters=None, include_orders=False, sort_by=None):
    tables = [users]
    select_cols = ['users.name', 'users.email']
    joins = []
    
    if include_orders:
        tables.append(orders)
        select_cols.append('orders.total')
        joins.append('orders')
        
    return QueryBuilder(
        tables=tables,
        select=select_cols,
        joins=joins or None,
        where=filters,
        order_by=[sort_by] if sort_by else None
    ).build()

# Usage
sql, params = get_users(
    filters={'users.active__eq': True, 'or__users.role__eq': 'admin'},
    include_orders=True,
    sort_by='users.name ASC'
)
```

## Why Choose This Library?

✅ **Eliminates Complex Logic** - No more nested if/else for dynamic queries

✅ **Type-Safe** - Catch errors at development time, not runtime  

✅ **Readable Code** - Declarative syntax that's easy to understand

✅ **Flexible** - Works with simple queries and complex multi-table joins

✅ **Safe** - Built-in SQL injection protection with parameterized queries

✅ **Maintainable** - Changes to table relationships update all queries automatically

## Usage Examples

### Table Definitions

```python
from sql_generator import Table, TableJoinAttribute

# Define table relationships
users = Table('users', joins={
    'orders': TableJoinAttribute('id', 'user_id'),
    'profiles': TableJoinAttribute('id', 'user_id')
})

orders = Table('orders', joins={
    'order_items': TableJoinAttribute('id', 'order_id')
})

order_items = Table('order_items', joins={
    'products': TableJoinAttribute('product_id', 'id')
})

products = Table('products')
```

### JOIN Examples

```python
# String joins (simple)
qb = QueryBuilder(
    [users, orders],
    ['users.name', 'orders.total'],
    joins=['orders']
)

# Join objects with via chains
qb = QueryBuilder(
    [users, orders, order_items, products],
    ['users.name', 'products.name'],
    joins=[
        Join('products', via_steps=[
            ViaStep('orders', JoinType.LEFT),
            ViaStep('order_items', JoinType.INNER)
        ])
    ]
)
```

### WHERE Conditions

```python
# Dictionary format with Django-style operators
where = {
    'users.active__eq': True,           # AND users.active = %s
    'or__users.age__lt': 25,           # OR users.age < %s  
    'and__orders.total__gte': 100,     # AND orders.total >= %s
    'users.name__like': '%john%',      # AND users.name LIKE %s
    'users.id__in': [1, 2, 3]         # AND users.id IN (%s, %s, %s)
}

# WhereCondition objects for complex logic
from sql_generator import WhereCondition, Operator

conditions = [
    WhereCondition('active', Operator.EQ, True, table='users'),
    WhereCondition('age', Operator.GTE, 18, table='users', logical_operator='OR'),
    WhereCondition('status', Operator.IN, ['active', 'pending'], table='orders')
]
```

## API Reference

### QueryBuilder

```python
QueryBuilder(
    tables: list[Table],                              # Required: Table definitions
    select: list[str | SelectColumn],                 # Required: Columns to select
    joins: list[str | Join] | None = None,           # Optional: JOIN clauses
    where: dict[str, Any] | list[WhereCondition] | None = None,  # Optional: WHERE conditions
    group_by: list[str | GroupBy] | None = None,     # Optional: GROUP BY columns
    order_by: list[str | OrderBy] | None = None,     # Optional: ORDER BY columns
    limit: int | None = None                         # Optional: LIMIT clause
)
```

### WHERE Operators

| Operator | SQL | Example |
|----------|-----|---------|
| `eq` | `=` | `{'id__eq': 1}` |
| `ne` | `!=` | `{'status__ne': 'inactive'}` |
| `lt`, `le` | `<`, `<=` | `{'age__lt': 25}` |
| `gt`, `ge` | `>`, `>=` | `{'price__gte': 100}` |
| `like`, `ilike` | `LIKE`, `ILIKE` | `{'name__like': '%john%'}` |
| `in`, `not_in` | `IN`, `NOT IN` | `{'id__in': [1,2,3]}` |
| `is_null`, `is_not_null` | `IS NULL`, `IS NOT NULL` | `{'deleted_at__is_null': None}` |
| `between` | `BETWEEN` | `{'age__between': [18, 65]}` |

### Key Classes

- **Table** - Database table with optional join definitions
- **TableJoinAttribute** - Defines relationship between tables
- **Join** - JOIN clause with optional via chains
- **ViaStep** - Step in a via chain with custom join type
- **SelectColumn** - Column selection with aggregation and aliasing
- **WhereCondition** - WHERE clause condition with logical operators
- **GroupBy/OrderBy** - GROUP BY and ORDER BY clauses

## Contributing

```bash
# Clone repository
git clone https://github.com/arthurm040/sql-generator.git
cd sql-generator

# Install with PDM
pdm install

# Run tests with coverage
pdm run test
```

## License

MIT License - see LICENSE file for details.

---

**Note:** This library generates parameterized SQL queries using `%s` placeholders, compatible with PostgreSQL and MySQL. For SQLite, you may need to replace `%s` with `?` in the generated SQL.