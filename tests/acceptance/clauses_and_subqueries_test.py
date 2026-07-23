from pyadql import ast_nodes as A


def test_group_by_having_order_by(parse):
    tree = parse(
        "SELECT field, AVG(mag) FROM stars "
        "GROUP BY field HAVING COUNT(*) > 5 ORDER BY AVG(mag) DESC"
    )
    # GROUP BY / HAVING belong to the inner Query (select_query)...
    assert tree.body.group_by == [A.ColumnRef(["field"])]
    assert isinstance(tree.body.having, A.BinaryOp) and tree.body.having.op == ">"
    # ...but ORDER BY belongs to the outer SelectExpression (ADQL 2.1: it
    # applies to the whole combined result, not to an individual SELECT).
    assert len(tree.order_by) == 1
    assert tree.order_by[0].direction == "DESC"


def test_order_by_default_ascending(parse):
    tree = parse("SELECT x FROM t ORDER BY x")
    assert tree.order_by[0].direction == "ASC"


def test_order_by_multiple_columns(parse):
    tree = parse("SELECT x, y FROM t ORDER BY x ASC, y DESC")
    dirs = [(item.expr, item.direction) for item in tree.order_by]
    assert dirs == [(A.ColumnRef(["x"]), "ASC"), (A.ColumnRef(["y"]), "DESC")]


def test_offset(parse):
    """OFFSET is new in ADQL 2.1 and, like ORDER BY, lives on the outer
    SelectExpression."""
    tree = parse("SELECT x FROM t OFFSET 5")
    assert tree.offset == 5


def test_offset_with_top_and_order_by(parse):
    tree = parse("SELECT TOP 10 x FROM t ORDER BY x DESC OFFSET 3")
    assert tree.body.top == 10
    assert tree.order_by[0].direction == "DESC"
    assert tree.offset == 3


def test_union(parse):
    tree = parse("SELECT id FROM t1 UNION SELECT id FROM t2")
    assert isinstance(tree.body, A.SetOperation)
    assert tree.body.op == "UNION"
    assert tree.body.distinct is True  # UNION without ALL => implicit DISTINCT
    assert tree.body.left.from_clause[0].name == "t1"
    assert tree.body.right.from_clause[0].name == "t2"


def test_union_all(parse):
    tree = parse("SELECT id FROM t1 UNION ALL SELECT id FROM t2")
    assert tree.body.distinct is False


def test_except_and_intersect(parse):
    e = parse("SELECT id FROM t1 EXCEPT SELECT id FROM t2")
    i = parse("SELECT id FROM t1 INTERSECT SELECT id FROM t2")
    assert e.body.op == "EXCEPT"
    assert i.body.op == "INTERSECT"


def test_order_by_and_offset_apply_to_whole_union(parse):
    """ADQL 2.1: ORDER BY / OFFSET after a UNION apply to the combined
    result, never to just the last operand."""
    tree = parse("SELECT id FROM t1 UNION SELECT id FROM t2 ORDER BY id OFFSET 1")
    assert isinstance(tree.body, A.SetOperation)
    assert tree.order_by[0].expr == A.ColumnRef(["id"])
    assert tree.offset == 1


def test_with_clause_cte(parse):
    """WITH (common table expressions) is new in ADQL 2.1."""
    tree = parse(
        "WITH recent AS (SELECT id FROM t WHERE d > 2020) " "SELECT id FROM recent"
    )
    assert tree.with_clause is not None
    assert len(tree.with_clause) == 1
    cte = tree.with_clause[0]
    assert isinstance(cte, A.CTE)
    assert cte.name == "recent"
    assert isinstance(cte.query, A.SelectExpression)
    assert cte.query.body.from_clause[0].name == "t"
    assert tree.body.from_clause[0].name == "recent"


def test_scalar_subquery_in_select(parse_query):
    tree = parse_query("SELECT (SELECT MAX(x) FROM other) FROM t")
    expr = tree.select_list[0].expr
    assert isinstance(expr, A.ScalarSubquery)
    assert isinstance(expr.subquery, A.SelectExpression)
    assert expr.subquery.body.from_clause[0].name == "other"


def test_correlated_subquery(parse_query):
    tree = parse_query(
        "SELECT * FROM (SELECT id FROM t1) AS sub "
        "WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = sub.id)"
    )
    exists = tree.where
    assert isinstance(exists, A.Exists)
    cond = exists.subquery.body.where
    assert cond.right == A.ColumnRef(["sub", "id"])
