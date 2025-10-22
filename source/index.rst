.. SQL Query Builder documentation master file, created by
   sphinx-quickstart on Mon Oct 20 16:22:49 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SQL Query Builder Documentation
===============================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api

Installation
============

.. code-block:: bash

   pip install sql-query-builder-py

**Requirements:** Python 3.12+

Welcome to SQL Query Builder
============================

Dynamic SQL query builder for Python that eliminates complex if/else logic for dynamic WHERE clauses and JOINs. Build queries using a constructor-based API with automatic table aliasing and relationship management.

The Problem This Solves
------------------------

**Before: Complex Dynamic Query Logic**

.. code-block:: python

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

**After: Clean Constructor-Based API**

.. code-block:: python

   from sql_generator.QueryObjects Table, TableJoinAttribute
   from sql_generator.select_query_generator QueryBuilder

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

Key Features
------------

🚀 **Constructor-Based API**
   Perfect for dynamic query generation - no method chaining required

🏷️ **Automatic Table Aliasing**
   Generates unique 3+ character aliases with conflict resolution

🔗 **Flexible JOIN System**
   Direct joins, via chains, and mixed join types

🎯 **Django-Style WHERE Conditions**
   ``{'users.id__eq': 1, 'or__age__gt': 18}``

🛡️ **Parameterized Queries**
   Safe SQL with automatic parameter binding

✨ **Hybrid Input Support**
   Use strings or objects for all query components

Quick Start Examples
--------------------

**Basic Query**

.. code-block:: python

   from sql_generator.QueryObjects import Table, TableJoinAttribute
   from sql_generator.select_query_generator QueryBuilder

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

**Query with JOINs and WHERE**

.. code-block:: python

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

**Advanced Features**

.. code-block:: python

   from sql_generator.QueryObjects import SelectColumn, AggFunction, Join, ViaStep, JoinType

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

**Dynamic Query Generation**

.. code-block:: python

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

Strings vs Objects - Flexible Input
-----------------------------------

The library supports both string and object inputs for all components, giving you flexibility to choose the approach that fits your use case.

**SELECT Columns**

.. code-block:: python

   # Define tables first (needed for all examples)
   from sql_generator import QueryBuilder, Table, TableJoinAttribute
   users = Table('users', joins={'orders': TableJoinAttribute('id', 'user_id')})
   orders = Table('orders')

   # Using strings (simple and concise)
   qb = QueryBuilder([users], ['users.name', 'users.email', 'COUNT(*)'])

   # Using objects (more control and type safety)
   from sql_generator.QueryObjects import SelectColumn, AggFunction
   qb = QueryBuilder([users], [
       SelectColumn('name', table='users'),
       SelectColumn('email', table='users'),
       SelectColumn('id', table='users', agg_function=AggFunction.COUNT, alias='total_users')
   ])

**WHERE Conditions**

.. code-block:: python

   # Using dictionary format (Django-style, concise)
   qb = QueryBuilder([users], ['users.name'], where={
       'users.active__eq': True,
       'users.age__gte': 18,
       'or__users.role__eq': 'admin'
   })

   # Using objects (explicit control over logic)
   from sql_generator.QueryObjects import WhereCondition, Operator
   qb = QueryBuilder([users], ['users.name'], where=[
       WhereCondition('active', Operator.EQ, True, table='users'),
       WhereCondition('age', Operator.GE, 18, table='users'),
       WhereCondition('role', Operator.EQ, 'admin', table='users', logical_operator='OR')
   ])

**JOIN Operations**

.. code-block:: python

   # Define all tables needed for examples
   users = Table('users', joins={'orders': TableJoinAttribute('id', 'user_id')})
   orders = Table('orders', joins={'order_items': TableJoinAttribute('id', 'order_id')})
   order_items = Table('order_items', joins={'products': TableJoinAttribute('product_id', 'id')})
   products = Table('products')

   # Using strings (simple joins)
   qb = QueryBuilder([users, orders], ['users.name', 'orders.total'],
                     joins=['orders'])

   # Using objects (complex via chains with custom join types)
   from sql_generator.QueryObjects import Join, ViaStep, JoinType
   qb = QueryBuilder([users, orders, order_items, products],
                     ['users.name', 'products.name'], joins=[
       Join('products', via_steps=[
           ViaStep('orders', JoinType.LEFT),
           ViaStep('order_items', JoinType.INNER)
       ])
   ])

**ORDER BY Clauses**

.. code-block:: python

   # Using strings (quick and readable)
   qb = QueryBuilder([users], ['users.name'],
                     order_by=['users.name ASC', 'users.created_at DESC'])

   # Using objects (explicit control)
   from sql_generator.QueryObjects import OrderBy
   qb = QueryBuilder([users], ['users.name'], order_by=[
       OrderBy('name', table='users', direction='ASC'),
       OrderBy('created_at', table='users', direction='DESC')
   ])

**Mixed Approach**

.. code-block:: python

   # You can mix strings and objects in the same query
   qb = QueryBuilder(
       tables=[users, orders],
       select=[
           'users.name',  # String
           SelectColumn('total', table='orders', agg_function=AggFunction.SUM, alias='revenue')  # Object
       ],
       joins=['orders'],  # String
       where={'users.active__eq': True},  # Dictionary
       order_by=['revenue DESC']  # String
   )

**When to Use Each Approach**

**Use Strings When:**
- Building simple, straightforward queries
- Rapid prototyping and development
- You prefer concise, readable code
- Working with standard SQL patterns

**Use Objects When:**
- You need explicit control over query components
- Building complex queries with custom logic
- You want full type safety and IDE support
- Creating reusable query components
- Working with complex JOIN chains or aggregations


Why Choose This Library?
------------------------

✅ **Eliminates Complex Logic** - No more nested if/else for dynamic queries

✅ **Type-Safe** - Catch errors at development time, not runtime

✅ **Readable Code** - Declarative syntax that's easy to understand

✅ **Flexible** - Works with simple queries and complex multi-table joins

✅ **Safe** - Built-in SQL injection protection with parameterized queries

✅ **Maintainable** - Changes to table relationships update all queries automatically

Perfect for building APIs, admin interfaces, reporting systems, and any application that needs dynamic SQL generation.
