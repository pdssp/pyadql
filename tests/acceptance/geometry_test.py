from pyadql import ast_nodes as A


def test_point(parse_query):
    tree = parse_query("SELECT POINT('ICRS', ra, dec) FROM t")
    p = tree.select_list[0].expr
    assert isinstance(p, A.Point)
    assert p.coordsys == A.StringLiteral("ICRS")
    assert p.ra == A.ColumnRef(["ra"])
    assert p.dec == A.ColumnRef(["dec"])


def test_point_without_coordsys():
    """coord_sys is optional as of ADQL 2.1 ([AnnexA #point])."""
    from pyadql import parse_adql

    tree = parse_adql("SELECT POINT(ra, dec) FROM t").body
    p = tree.select_list[0].expr
    assert p.coordsys is None
    assert p.ra == A.ColumnRef(["ra"])
    assert p.dec == A.ColumnRef(["dec"])


def test_circle(parse_query):
    tree = parse_query("SELECT CIRCLE('ICRS', 10, 20, 1) FROM t")
    c = tree.select_list[0].expr
    assert isinstance(c, A.Circle)
    assert c.coordsys == A.StringLiteral("ICRS")
    assert c.center == A.Coordinates(A.NumberLiteral(10.0), A.NumberLiteral(20.0))
    assert c.radius == A.NumberLiteral(1.0)


def test_circle_center_as_coord_value(parse_query):
    """ADQL 2.1 addition: the center can be a ready-made point-valued
    expression (a column, POINT()/CENTROID(), or a UDF) instead of a raw
    ra/dec pair ([AnnexA #circle_center])."""
    tree = parse_query("SELECT CIRCLE(center_col, 1) FROM t")
    c = tree.select_list[0].expr
    assert isinstance(c, A.Circle)
    assert c.coordsys is None
    assert c.center == A.ColumnRef(["center_col"])


def test_box(parse_query):
    tree = parse_query("SELECT BOX('ICRS', 1, 2, 3, 4) FROM t")
    b = tree.select_list[0].expr
    assert isinstance(b, A.Box)
    assert b.center == A.Coordinates(A.NumberLiteral(1.0), A.NumberLiteral(2.0))
    assert (b.width, b.height) == (A.NumberLiteral(3.0), A.NumberLiteral(4.0))


def test_box_center_as_coord_value(parse_query):
    tree = parse_query("SELECT BOX(center_col, 1, 1) FROM t")
    b = tree.select_list[0].expr
    assert b.center == A.ColumnRef(["center_col"])


def test_polygon(parse_query):
    tree = parse_query("SELECT POLYGON('ICRS', 1, 2, 3, 4, 5, 6) FROM t")
    poly = tree.select_list[0].expr
    assert isinstance(poly, A.Polygon)
    assert len(poly.vertices) == 3
    assert poly.vertices[0] == A.Coordinates(A.NumberLiteral(1.0), A.NumberLiteral(2.0))


def test_polygon_vertices_as_coord_values(parse_query):
    """ADQL 2.1 addition: each vertex can be a point-valued expression
    instead of a raw ra/dec pair ([AnnexA #polygon_vertices])."""
    tree = parse_query("SELECT POLYGON('ICRS', p1, p2, p3) FROM t")
    poly = tree.select_list[0].expr
    assert len(poly.vertices) == 3
    assert poly.vertices == [
        A.ColumnRef(["p1"]),
        A.ColumnRef(["p2"]),
        A.ColumnRef(["p3"]),
    ]


def test_region(parse_query):
    tree = parse_query("SELECT REGION('circle 10 20 1') FROM t")
    region = tree.select_list[0].expr
    assert isinstance(region, A.Region)
    assert region.stcs == "circle 10 20 1"


def test_contains_used_in_predicate(parse_query):
    tree = parse_query(
        "SELECT * FROM t WHERE "
        "CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 10, 20, 1)) = 1"
    )
    where = tree.where
    assert isinstance(where, A.BinaryOp) and where.op == "="
    assert isinstance(where.left, A.Contains)
    assert isinstance(where.left.geom1, A.Point)
    assert isinstance(where.left.geom2, A.Circle)


def test_intersects(parse_query):
    tree = parse_query(
        "SELECT * FROM t WHERE "
        "INTERSECTS(POLYGON('ICRS', 1,2,3,4,5,6), BOX('ICRS',1,2,3,4)) = 1"
    )
    assert isinstance(tree.where.left, A.Intersects)


def test_distance_area_centroid_coord(parse_query):
    tree = parse_query(
        "SELECT DISTANCE(POINT('ICRS', 1, 2), POINT('ICRS', 3, 4)), "
        "AREA(CIRCLE('ICRS', 1, 2, 3)), "
        "CENTROID(POLYGON('ICRS', 1,2,3,4,5,6)), "
        "COORD1(POINT('ICRS', 1, 2)), "
        "COORD2(POINT('ICRS', 1, 2)), "
        "COORDSYS(POINT('ICRS', 1, 2)) "
        "FROM t"
    )
    exprs = [item.expr for item in tree.select_list]
    assert isinstance(exprs[0], A.Distance)
    assert exprs[0].numeric_form is False
    assert isinstance(exprs[1], A.Area)
    assert isinstance(exprs[2], A.Centroid)
    assert isinstance(exprs[3], A.Coord1)
    assert isinstance(exprs[4], A.Coord2)
    assert isinstance(exprs[5], A.Coordsys)


def test_distance_four_argument_numeric_form(parse_query):
    """ADQL 2.1 addition: DISTANCE(ra1, dec1, ra2, dec2), the recommended
    form for an efficient sky crossmatch ([AnnexA #distance_function])."""
    tree = parse_query("SELECT DISTANCE(1, 2, 3, 4) FROM t")
    dist = tree.select_list[0].expr
    assert isinstance(dist, A.Distance)
    assert dist.numeric_form is True
    assert dist.args == [
        A.NumberLiteral(1.0),
        A.NumberLiteral(2.0),
        A.NumberLiteral(3.0),
        A.NumberLiteral(4.0),
    ]


def test_coordsys_must_be_a_string_literal(parse_query):
    """ADQL 2.1 narrows coord_sys to a plain string literal (it was any
    string_value_expression in 2.0): a column reference used where a
    coordsys is expected does not match point_expr's shape, so it falls
    back to the generic user_defined_function path (POINT treated as an
    ordinary 3-argument function call) rather than producing a Point node."""
    tree = parse_query("SELECT POINT(cs_col, ra, dec) FROM t")
    expr = tree.select_list[0].expr
    assert isinstance(expr, A.UserFunctionCall)
    assert expr.name == "POINT"
    assert len(expr.args) == 3
