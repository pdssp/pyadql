from pyadql import ast_nodes as A


def test_comparison(parse_query):
    tree = parse_query("SELECT * FROM t WHERE x = 1")
    assert tree.where == A.BinaryOp("=", A.ColumnRef(["x"]), A.NumberLiteral(1.0))


def test_and_or_not_precedence(parse_query):
    tree = parse_query("SELECT * FROM t WHERE a = 1 OR NOT b = 2 AND c = 3")
    # AND binds tighter than OR; NOT binds to b = 2
    where = tree.where
    assert isinstance(where, A.BinaryOp) and where.op == "OR"
    assert where.left == A.BinaryOp("=", A.ColumnRef(["a"]), A.NumberLiteral(1.0))
    right = where.right
    assert isinstance(right, A.BinaryOp) and right.op == "AND"
    assert isinstance(right.left, A.UnaryOp) and right.left.op == "NOT"


def test_between(parse_query):
    tree = parse_query("SELECT * FROM t WHERE x BETWEEN 1 AND 10")
    pred = tree.where
    assert isinstance(pred, A.Between)
    assert pred.negated is False
    assert pred.low == A.NumberLiteral(1.0)
    assert pred.high == A.NumberLiteral(10.0)


def test_not_between(parse_query):
    pred = parse_query("SELECT * FROM t WHERE x NOT BETWEEN 1 AND 10").where
    assert isinstance(pred, A.Between)
    assert pred.negated is True


def test_in_list(parse_query):
    pred = parse_query("SELECT * FROM t WHERE x IN (1, 2, 3)").where
    assert isinstance(pred, A.InPredicate)
    assert pred.negated is False
    assert pred.values == [
        A.NumberLiteral(1.0),
        A.NumberLiteral(2.0),
        A.NumberLiteral(3.0),
    ]


def test_not_in_subquery(parse_query):
    pred = parse_query("SELECT * FROM t WHERE x NOT IN (SELECT id FROM excluded)").where
    assert isinstance(pred, A.InPredicate)
    assert pred.negated is True
    assert isinstance(pred.values, A.SelectExpression)


def test_like(parse_query):
    pred = parse_query("SELECT * FROM t WHERE name LIKE 'M%'").where
    assert isinstance(pred, A.Like)
    assert pred.pattern == A.StringLiteral("M%")
    assert pred.negated is False
    assert pred.case_insensitive is False


def test_ilike(parse_query):
    pred = parse_query("SELECT * FROM t WHERE name ILIKE 'M%'").where
    assert isinstance(pred, A.Like)
    assert pred.case_insensitive is True
    assert pred.negated is False


def test_not_ilike(parse_query):
    pred = parse_query("SELECT * FROM t WHERE name NOT ILIKE 'M%'").where
    assert pred.case_insensitive is True
    assert pred.negated is True


def test_is_null_and_is_not_null(parse_query):
    p1 = parse_query("SELECT * FROM t WHERE x IS NULL").where
    p2 = parse_query("SELECT * FROM t WHERE x IS NOT NULL").where
    assert isinstance(p1, A.IsNull) and p1.negated is False
    assert isinstance(p2, A.IsNull) and p2.negated is True


def test_exists(parse_query):
    pred = parse_query(
        "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM u WHERE u.id = t.id)"
    ).where
    assert isinstance(pred, A.Exists)
    assert isinstance(pred.subquery, A.SelectExpression)


def test_string_literal_with_escaped_quote(parse_query):
    tree = parse_query("SELECT * FROM t WHERE name = 'O''Brien'")
    assert tree.where.right == A.StringLiteral("O'Brien")
