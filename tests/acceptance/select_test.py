from pyadql import ast_nodes as A


def test_simple_select(parse_query):
    tree = parse_query("SELECT ra, dec FROM mytable")
    assert isinstance(tree, A.Query)
    assert tree.distinct is False
    assert tree.top is None
    assert [item.expr.parts for item in tree.select_list] == [["ra"], ["dec"]]
    assert tree.from_clause[0].name == "mytable"


def test_select_star(parse_query):
    tree = parse_query("SELECT * FROM mytable")
    assert isinstance(tree.select_list, A.Star)


def test_top_and_distinct(parse_query):
    tree = parse_query("SELECT DISTINCT TOP 10 ra FROM mytable")
    assert tree.distinct is True
    assert tree.top == 10


def test_column_alias(parse_query):
    tree = parse_query("SELECT ra AS right_ascension FROM mytable")
    item = tree.select_list[0]
    assert item.alias == "right_ascension"


def test_table_alias(parse_query):
    tree = parse_query("SELECT t.ra FROM mytable AS t")
    ref = tree.from_clause[0]
    assert isinstance(ref, A.TableRef)
    assert ref.name == "mytable"
    assert ref.alias == "t"


def test_schema_qualified_table(parse_query):
    tree = parse_query("SELECT * FROM gaiadr3.gaia_source")
    assert tree.from_clause[0].name == "gaiadr3.gaia_source"


def test_arithmetic_expression_precedence(parse_query):
    tree = parse_query("SELECT dec * 2 - 3 FROM t")
    expr = tree.select_list[0].expr
    # (dec * 2) - 3  =>  multiplication correctly binds tighter
    assert isinstance(expr, A.BinaryOp)
    assert expr.op == "-"
    assert isinstance(expr.left, A.BinaryOp)
    assert expr.left.op == "*"
    assert expr.right == A.NumberLiteral(3.0)


def test_quoted_identifier(parse_query):
    tree = parse_query('SELECT "My Column" FROM t')
    assert tree.select_list[0].expr.parts == ["My Column"]


def test_quoted_identifier_with_escaped_double_quote(parse_query):
    """Per the official spec ([AnnexA #delimited_identifier]): a doubled
    double-quote inside a delimited identifier escapes a literal double
    quote, exactly like '' does inside a string literal. The spec's own
    example: "Table""X" denotes the single identifier Table"X."""
    tree = parse_query('SELECT "Table""X" FROM t')
    assert tree.select_list[0].expr.parts == ['Table"X']


def test_string_concatenation(parse_query):
    tree = parse_query("SELECT a || b FROM t")
    expr = tree.select_list[0].expr
    assert isinstance(expr, A.BinaryOp)
    assert expr.op == "||"
