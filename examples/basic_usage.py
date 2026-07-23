"""Usage example for the pyadql package (run with `uv run python examples/basic_usage.py`)."""

from pyadql import ast_nodes as A
from pyadql import parse_adql

query = """
SELECT TOP 100 g.source_id, g.ra, g.dec,
       DISTANCE(POINT('ICRS', g.ra, g.dec), POINT('ICRS', 56.75, 24.12)) AS dist
FROM gaiadr3.gaia_source AS g
WHERE CONTAINS(POINT('ICRS', g.ra, g.dec),
               CIRCLE('ICRS', 56.75, 24.12, 0.5)) = 1
  AND g.phot_g_mean_mag < 18
ORDER BY dist ASC
"""

tree = parse_adql(query)

print("Root node type:", type(tree).__name__)  # SelectExpression
print("Query body type:", type(tree.body).__name__)
print("TOP:", tree.body.top)
print("Selected columns:")
for item in tree.body.select_list:
    print("  -", item.expr, "AS", item.alias)

print(
    "\nQueried table:",
    tree.body.from_clause[0].name,
    "alias =",
    tree.body.from_clause[0].alias,
)
print(
    "ORDER BY (lives on the outer SelectExpression, not the inner query):",
    tree.order_by[0].expr,
    tree.order_by[0].direction,
)


def walk(node, found):
    """Simple recursive AST walk: collect every ColumnRef."""
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
print("\nColumns referenced in WHERE:", cols)
