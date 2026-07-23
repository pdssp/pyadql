# Tutorial

## Introduction

This tutorial walks through installing PyADQL, parsing a first query, and
then a more realistic, Gaia-style astronomical cross-match query, showing
both the CLI and the library API side by side. It complements
[`operation_manual.md`](operation_manual.md) (procedures) and
[`reference_manual.md`](reference_manual.md) (full option/feature
reference) with a narrative, example-driven introduction.

## Getting started

Install PyADQL with [uv](https://docs.astral.sh/uv/) (used throughout
this project):

```console
$ uv sync
```

or, once built, with plain `pip`:

```console
$ pip install pyadql
```

Check the installation by parsing a trivial query:

```console
$ uv run pyadql "SELECT TOP 10 ra, dec FROM t WHERE ra > 10"
SelectExpression(body=Query(distinct=False, top=10, ...), order_by=None, offset=None, with_clause=None)
```

From Python, the equivalent is:

```python
>>> from pyadql import parse_adql
>>> tree = parse_adql("SELECT TOP 10 ra, dec FROM t WHERE ra > 10")
>>> tree.body.top
10
```

## Using the software on a typical task

A realistic ADQL query, as used against a Gaia-like TAP service, combines
a `TOP` clause, a computed column, a table alias, and a sky-region search
with `CONTAINS`/`POINT`/`CIRCLE`:

```sql
SELECT TOP 100 g.source_id, g.ra, g.dec,
       DISTANCE(POINT('ICRS', g.ra, g.dec), POINT('ICRS', 56.75, 24.12)) AS dist
FROM gaiadr3.gaia_source AS g
WHERE CONTAINS(POINT('ICRS', g.ra, g.dec),
               CIRCLE('ICRS', 56.75, 24.12, 0.5)) = 1
  AND g.phot_g_mean_mag < 18
ORDER BY dist ASC
```

Run it with the CLI, and inspect specific parts of the JSON output with a
tool like [`jq`](https://jqlang.org/):

```console
$ uv run pyadql --json "$(cat query.adql)" | jq '.body.from_clause'
```

Or walk the typed AST directly in Python -- this is exactly what
[`examples/basic_usage.py`](https://gitlab.cnes.fr/pdssp/common/pyadql/blob/main/examples/basic_usage.py) does:

```python
from pyadql import parse_adql
from pyadql import ast_nodes as A

tree = parse_adql(query)  # the SQL text above

print("Root node type:", type(tree).__name__)          # SelectExpression
print("TOP:", tree.body.top)                            # 100
for item in tree.body.select_list:
    print("  -", item.expr, "AS", item.alias)

print("Table:", tree.body.from_clause[0].name,
      "alias =", tree.body.from_clause[0].alias)         # gaiadr3.gaia_source / g
print("ORDER BY:", tree.order_by[0].expr, tree.order_by[0].direction)  # dist ASC

# Collect every column referenced in the WHERE clause
def walk(node, found):
    if isinstance(node, A.ColumnRef):
        found.append(str(node))
    elif hasattr(node, "__dataclass_fields__"):
        for f in node.__dataclass_fields__:
            walk(getattr(node, f), found)
    elif isinstance(node, list):
        for item in node:
            walk(item, found)

cols = []
walk(tree.body.where, cols)
print("Columns referenced in WHERE:", cols)
```

Two things worth noting when reading the result (explained in full in
[`docs/AST.md`](AST.md)):

- `tree` is a `SelectExpression`, not the `SELECT` itself: `ORDER BY`
  lives on `tree.order_by`, one level above `tree.body` (a `Query`), per
  a deliberate ADQL 2.1 structural change.
- `CONTAINS(...) = 1` parses as an ordinary `BinaryOp('=', ...)` wrapping
  a `Contains` node -- ADQL defines `CONTAINS` as a numeric function, not
  a dedicated predicate.

Try running this example yourself with:

```console
$ uv run python examples/basic_usage.py
```

For the full node reference table and more worked examples, continue with
[`docs/AST.md`](AST.md).
