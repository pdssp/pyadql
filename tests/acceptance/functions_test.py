from pyadql import ast_nodes as A


def test_count_star(parse_query):
    tree = parse_query("SELECT COUNT(*) FROM t")
    assert isinstance(tree.select_list[0].expr, A.CountStar)


def test_aggregate_functions(parse_query):
    tree = parse_query("SELECT SUM(x), AVG(x), MIN(x), MAX(x) FROM t")
    names = [item.expr.name for item in tree.select_list]
    assert names == ["SUM", "AVG", "MIN", "MAX"]


def test_aggregate_with_distinct(parse_query):
    tree = parse_query("SELECT COUNT(DISTINCT x) FROM t")
    fn = tree.select_list[0].expr
    assert isinstance(fn, A.FunctionCall)
    assert fn.name == "COUNT"
    assert fn.distinct is True


def test_numeric_functions(parse_query):
    tree = parse_query(
        "SELECT ABS(x), SQRT(x), ROUND(x), POWER(x, 2), MOD(x, 3) FROM t"
    )
    names = [item.expr.name for item in tree.select_list]
    assert names == ["ABS", "SQRT", "ROUND", "POWER", "MOD"]


def test_trig_functions(parse_query):
    tree = parse_query("SELECT SIN(x), COS(x), ATAN2(y, x) FROM t")
    fns = [item.expr for item in tree.select_list]
    assert [f.name for f in fns] == ["SIN", "COS", "ATAN2"]
    assert fns[2].args == [A.ColumnRef(["y"]), A.ColumnRef(["x"])]


def test_in_unit_function(parse_query):
    """IN_UNIT is new in ADQL 2.1 ([AnnexA #in_unit_function])."""
    tree = parse_query("SELECT IN_UNIT(ra, 'deg') FROM t")
    fn = tree.select_list[0].expr
    assert isinstance(fn, A.FunctionCall)
    assert fn.name == "IN_UNIT"
    assert fn.args == [A.ColumnRef(["ra"]), A.StringLiteral("deg")]


def test_string_functions(parse_query):
    """ADQL 2.1's Annex A only lists LOWER/UPPER under
    case_folding_function -- unlike 2.0, SUBSTRING/TRIM/CHAR_LENGTH are not
    part of this grammar (an unrecognized name like TRIM still parses via
    the generic user_defined_function fallback, see test_functions'
    equivalent for POINT-as-UDF in test_geometry.py)."""
    tree = parse_query("SELECT LOWER(name), UPPER(name) FROM t")
    names = [item.expr.name for item in tree.select_list]
    assert names == ["LOWER", "UPPER"]


def test_cast(parse_query):
    tree = parse_query("SELECT CAST(ra AS DOUBLE PRECISION) FROM t")
    cast = tree.select_list[0].expr
    assert isinstance(cast, A.Cast)
    assert cast.type == A.CastType("DOUBLE PRECISION")
    assert cast.expr == A.ColumnRef(["ra"])


def test_cast_with_parameters(parse_query):
    tree = parse_query("SELECT CAST(name AS VARCHAR(20)) FROM t")
    cast = tree.select_list[0].expr
    assert cast.type == A.CastType("VARCHAR", [20])


def test_cast_integer_types(parse_query):
    for type_name in ("SMALLINT", "INTEGER", "BIGINT", "REAL"):
        tree = parse_query(f"SELECT CAST(x AS {type_name}) FROM t")
        assert tree.select_list[0].expr.type == A.CastType(type_name)


def test_cast_geometry_and_datetime_types(parse_query):
    tree = parse_query("SELECT CAST(p AS POINT) FROM t")
    assert tree.select_list[0].expr.type == A.CastType("POINT")
    tree = parse_query("SELECT CAST(t AS TIMESTAMP) FROM t")
    assert tree.select_list[0].expr.type == A.CastType("TIMESTAMP")


def test_coalesce(parse_query):
    """COALESCE is new in ADQL 2.1 ([AnnexA #coalesce_expression])."""
    tree = parse_query("SELECT COALESCE(a, b, c) FROM t")
    expr = tree.select_list[0].expr
    assert isinstance(expr, A.Coalesce)
    assert expr.args == [A.ColumnRef(["a"]), A.ColumnRef(["b"]), A.ColumnRef(["c"])]


def test_user_defined_function(parse_query):
    tree = parse_query("SELECT gavo_transform('GALACTIC', 'ICRS', p) FROM t")
    fn = tree.select_list[0].expr
    assert isinstance(fn, A.UserFunctionCall)
    assert fn.name == "gavo_transform"
    assert len(fn.args) == 3
