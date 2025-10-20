# SQL Generator

Dynamic SQL query builder for Python that eliminates complex if/else logic for dynamic WHERE clauses and JOINs. Build queries using a constructor-based API with automatic table aliasing and relationship management.

## Installation

```bash
pip install sql-generator
```

**Requirements:** Python 3.12+

## Quick Start

```python
from sql_generator import QueryBuilder, Table, TableJoinAttribute

# Define table relationships
users = Table('users', joins={
    'orders': TableJoinAttribute('id', 'user_id')
})
orders = Table('orders')

# Build query
qb = QueryBuilder(
    tables=[users, orders],
    select=['users.name', 'orders.total'],
    joins=['orders'],
    where={'users.active__eq': True}
)

sql, params = qb.build()
print(sql)
# SELECT use.name, ord.total
# FROM users use
# INNER JOIN orders ord ON use.id = ord.user_id
# WHERE use.active = %s
```

## Features

- **Constructor-based API** - Perfect for dynamic query generation
- **Automatic table aliasing** - Generates unique 3+ character aliases with conflict resolution
- **Where conditions Class** - Dynamic class that generates complex where clauses
- **Django-style WHERE conditions** - `{'users.id__eq': 1, 'or__age__gt': 18}`
- **Flexible JOIN system** - Direct joins, via chains, and mixed join types
- **Hybrid input support** - Use strings or objects for all query components
- **Parameterized queries** - Safe SQL with parameter binding
- **JOIN deduplication** - Removes duplicate JOINs while preserving order
- **Comprehensive validation** - Clear error messages for invalid configurations

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

### Basic Queries

```python
# Simple SELECT
qb = QueryBuilder([users], ['users.name', 'users.email'])
sql, params = qb.build()

# With WHERE conditions
qb = QueryBuilder(
    [users], 
    ['users.name'],
    where={'users.active__eq': True, 'users.age__gte': 18}
)
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
from sql_generator import Join, ViaStep, JoinType

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

### Advanced Features

```python
from sql_generator import SelectColumn, AggFunction, GroupBy, OrderBy

# Aggregation with aliases
qb = QueryBuilder(
    [users, orders],
    [
        'users.name',
        SelectColumn('COUNT(*)', alias='order_count'),
        SelectColumn('total', AggFunction.SUM, table='orders', alias='total_sales')
    ],
    joins=['orders'],
    group_by=['users.id', 'users.name'],
    order_by=['total_sales DESC'],
    limit=50
)
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

## Why This Library?

**Perfect for dynamic queries** where you need to conditionally add JOINs, WHERE clauses, or change SELECT columns based on user input or application logic.

**Replaces complex code like:**
```python
# Before: Complex if/else logic
sql = "SELECT users.name"
params = []
if include_orders:
    sql += ", orders.total"
if join_orders:
    sql += " FROM users u JOIN orders o ON u.id = o.user_id"
else:
    sql += " FROM users u"
if active_only:
    sql += " WHERE u.active = %s"
    params.append(True)
# ... more complex logic
```

**With simple constructor calls:**
```python
# After: Clean, declarative
qb = QueryBuilder(
    tables=[users, orders] if join_orders else [users],
    select=['users.name'] + (['orders.total'] if include_orders else []),
    joins=['orders'] if join_orders else None,
    where={'users.active__eq': True} if active_only else None
)
sql, params = qb.build()
```

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
