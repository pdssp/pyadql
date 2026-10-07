from pyadql import ast_nodes as A


def test_realistic_gaia_query(parse):
    query = """
    SELECT TOP 100 g.source_id, g.ra, g.dec,
           DISTANCE(POINT('ICRS', g.ra, g.dec), POINT('ICRS', 56.75, 24.12)) AS dist
    FROM gaiadr3.gaia_source AS g
    WHERE CONTAINS(POINT('ICRS', g.ra, g.dec),
                   CIRCLE('ICRS', 56.75, 24.12, 0.5)) = 1
      AND g.phot_g_mean_mag < 18
    ORDER BY dist ASC
    """
    tree = parse(query)

    assert tree.body.top == 100
    
    assert len(tree.body.from_clause[0].name) == 2
    assert tree.body.from_clause[0].name[0] == A.Identifier("gaiadr3", False)
    assert tree.body.from_clause[0].name[1] == A.Identifier("gaia_source", False)
    assert tree.body.from_clause[0].alias == A.Identifier("g", False)

    dist_item = tree.body.select_list[3]
    assert dist_item.alias == A.Identifier("dist", False)
    assert isinstance(dist_item.expr, A.Distance)
    assert dist_item.expr.numeric_form is False

    where = tree.body.where
    assert isinstance(where, A.BinaryOp) and where.op == "AND"
    assert isinstance(where.left, A.BinaryOp) and isinstance(
        where.left.left, A.Contains
    )
    
    right_expr = where.right
    assert isinstance(right_expr, A.BinaryOp) 
    assert right_expr.op == "<"
    assert right_expr.left == A.ColumnRef([A.Identifier("g", False), A.Identifier("phot_g_mean_mag", False)]) 
    assert right_expr.right == A.NumberLiteral(18.0)

    # ORDER BY belongs to the outer SelectExpression, not the inner Query.
    assert tree.order_by[0].expr == A.ColumnRef([A.Identifier("dist", False)])
    assert tree.order_by[0].direction == "ASC"


def test_query_with_join_geometry_and_grouping():
    from pyadql import parse_adql

    query = """
    SELECT c.cluster_name, COUNT(*) AS n_members
    FROM clusters AS c
    INNER JOIN members AS m ON c.id = m.cluster_id
    WHERE CONTAINS(POINT('ICRS', m.ra, m.dec), c.footprint) = 1
    GROUP BY c.cluster_name
    HAVING COUNT(*) > 10
    ORDER BY n_members DESC
    """
    tree = parse_adql(query)
    join = tree.body.from_clause[0]
    assert isinstance(join, A.Join)
    assert join.join_type == "INNER"
    assert tree.body.group_by == [A.ColumnRef([A.Identifier("c", False), A.Identifier("cluster_name", False)])]
    assert tree.body.having.op == ">"
    assert tree.order_by[0].direction == "DESC"


def test_cte_feeding_a_geometry_crossmatch():
    """A more realistic use of ADQL 2.1's WITH clause: pre-filter one table,
    then crossmatch against it using the new 4-argument DISTANCE form."""
    from pyadql import parse_adql

    query = """
    WITH bright AS (
        SELECT source_id, ra, dec FROM gaiadr3.gaia_source WHERE phot_g_mean_mag < 15
    )
    SELECT b.source_id, x.name
    FROM bright AS b
    INNER JOIN external_catalog AS x
        ON DISTANCE(b.ra, b.dec, x.ra, x.dec) < 0.01
    """
    tree = parse_adql(query)
    assert tree.with_clause[0].name == A.Identifier("bright", False)
    assert tree.with_clause[0].query.body.where.op == "<"

    join = tree.body.from_clause[0]
    assert isinstance(join, A.Join)
    assert isinstance(join.on, A.BinaryOp) and join.on.op == "<"
    dist = join.on.left
    assert isinstance(dist, A.Distance)
    assert dist.numeric_form is True
