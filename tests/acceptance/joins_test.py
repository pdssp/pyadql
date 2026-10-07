from pyadql import ast_nodes as A


def test_inner_join_on(parse_query):
    tree = parse_query(
        'SELECT a.id FROM tbl_a AS a INNER JOIN tbl_b AS "B" ON a.id = "B".id'
    )
    join = tree.from_clause[0]
    assert isinstance(join, A.Join)
    assert join.join_type == "INNER"
    assert join.left == A.TableRef(name=[A.Identifier("tbl_a", False)], alias=A.Identifier("a", False))
    assert join.right == A.TableRef(name=[A.Identifier("tbl_b", False)], alias=A.Identifier("B", True))
    assert isinstance(join.on, A.BinaryOp)
    assert join.on.op == "="


def test_left_outer_join_using(parse_query):
    tree = parse_query("SELECT * FROM a LEFT OUTER JOIN b USING (id)")
    join = tree.from_clause[0]
    assert join.join_type == "LEFT"
    assert join.using == [A.Identifier("id", False)]
    assert join.on is None


def test_right_and_full_join(parse_query):
    right = parse_query("SELECT * FROM a RIGHT JOIN b ON a.x = b.x").from_clause[0]
    full = parse_query("SELECT * FROM a FULL OUTER JOIN b ON a.x = b.x").from_clause[0]
    assert right.join_type == "RIGHT"
    assert full.join_type == "FULL"


def test_multiple_joins_chain(parse_query):
    tree = parse_query("SELECT * FROM a JOIN b ON a.id = b.id JOIN c ON b.id = c.id")
    outer_join = tree.from_clause[0]
    assert isinstance(outer_join, A.Join)
    # (a JOIN b) JOIN c: the outermost join has c on its right side
    assert outer_join.right == A.TableRef(name=[A.Identifier("c", False)])
    assert isinstance(outer_join.left, A.Join)
    assert outer_join.left.right == A.TableRef(name=[A.Identifier("b", False)])


def test_derived_table_in_from(parse_query):
    tree = parse_query("SELECT * FROM (SELECT id FROM t1) AS sub")
    derived = tree.from_clause[0]
    assert isinstance(derived, A.DerivedTable)
    assert derived.alias == A.Identifier("sub", False)
    assert isinstance(derived.subquery, A.SelectExpression)
    assert derived.subquery.body.from_clause[0].name[0] == A.Identifier("t1", False)


def test_multiple_from_tables_cartesian(parse_query):
    tree = parse_query("SELECT * FROM a, b WHERE a.id = b.id")
    assert len(tree.from_clause) == 2
    assert [t.name for t in tree.from_clause] == [[A.Identifier("a", False)], [A.Identifier("b", False)]]
