"""
Tests derived from analyzing a DaCHS production log (EPN-TAP TAP service).

The log was run entirely through pyadql (~2584 unique queries extracted from
the QUERY= parameters of TAP requests): 2533 parsed successfully, 51 failed.
Walking the resulting ASTs confirmed coverage of the ADQL constructs actually
used in real-world traffic (comparisons, AND/OR, TOP, DISTINCT, LIKE,
BETWEEN, IN, IS NULL, GROUP BY, user-defined functions, aliases,
concatenation, quoted identifiers, etc.): all of them were already covered by
equivalent tests in test_select.py, test_joins.py, test_predicates.py and
test_functions.py.

This file covers the few real-world patterns that did not yet have an
explicit equivalent in the suite:
  - NOT in front of an entire predicate (UnaryOp) rather than the NOT_KW
    internal to BETWEEN/IN/LIKE (two valid ADQL syntactic forms, two
    different AST shapes),
  - GROUP BY without HAVING,
  - a space between a function name and its parenthesis ("COUNT (*)"),
  - a user-defined function nested inside a comparison
    ("1 = ivo_hashlist_has(...)"),
  - OFFSET (pagination) and ILIKE (case-insensitive LIKE): both constructs,
    seen in the log, are indeed part of the ADQL 2.1 standard (contrary to
    what a first quick pass had assumed -- see IVOA REC-ADQL-2.1 and
    https://blog.g-vo.org/speak-out-on-adql-2-1.html); the grammar has since
    been extended to support them.

Only LIMIT (generic SQL, never standardized in ADQL, unlike OFFSET) remains,
correctly, rejected by pyadql.
"""

import pytest

from pyadql import ast_nodes as A
from pyadql import parse_adql


def test_not_prefixing_a_whole_between_predicate():
    """'NOT x BETWEEN a AND b' (a generic NOT wrapping the whole predicate)
    is different from 'x NOT BETWEEN a AND b' (negation internal to
    BETWEEN) -- the latter is already tested in
    test_predicates.py::test_not_between. Seen in the log:
    'SELECT TOP 1 epoch FROM t WHERE NOT epoch BETWEEN 2086000 AND 2817000'."""
    tree = parse_adql(
        "SELECT TOP 1 epoch FROM dynastvo.epn_core "
        "WHERE NOT epoch BETWEEN 2086000 AND 2817000"
    )
    where = tree.body.where
    assert isinstance(where, A.UnaryOp)
    assert where.op == "NOT"
    assert isinstance(where.operand, A.Between)
    assert (
        where.operand.negated is False
    )  # the negation comes from the wrapping NOT, not BETWEEN itself


def test_group_by_without_having():
    """GROUP BY on its own (having_clause is optional in the grammar) -- the
    only existing test (test_clauses_and_subqueries.py) always pairs
    GROUP BY with HAVING. Seen in the log:
    'SELECT discovered, COUNT(*) FROM exoplanet.epn_core
     WHERE discovered >= 2010 AND discovered <= 2026 GROUP BY discovered'."""
    tree = parse_adql(
        "SELECT discovered, COUNT(*) FROM exoplanet.epn_core "
        "WHERE discovered >= 2010 AND discovered <= 2026 "
        "GROUP BY discovered"
    )
    assert tree.body.group_by == [A.ColumnRef(["discovered"])]
    assert tree.body.having is None


def test_space_between_function_name_and_parenthesis():
    """'COUNT (*)' with a space: seen verbatim in the log
    ('SELECT COUNT (*) FROM apis.epn_core'). The grammar ignores whitespace
    (%ignore WS), so this must be strictly equivalent to 'COUNT(*)'."""
    tree = parse_adql("SELECT COUNT (*) FROM apis.epn_core")
    assert isinstance(tree.body.select_list[0].expr, A.CountStar)


def test_user_defined_function_nested_in_comparison():
    """A user-defined function (a TAP-service-specific extension, here
    ivo_hashlist_has from EPN-TAP) itself nesting LOWER() calls, used as an
    operand of a comparison -- a very common pattern in the log (733
    user-defined-function occurrences overall). The only existing test
    (test_functions.py::test_user_defined_function) only covers a bare UDF
    in SELECT position, not this level of nesting."""
    tree = parse_adql(
        "SELECT * FROM apis.epn_core WHERE "
        "1 = ivo_hashlist_has(lower(target_name), lower('Jupiter'))"
    )
    where = tree.body.where
    assert isinstance(where, A.BinaryOp) and where.op == "="
    assert where.left == A.NumberLiteral(1.0)

    udf = where.right
    assert isinstance(udf, A.UserFunctionCall)
    assert udf.name == "ivo_hashlist_has"
    assert len(udf.args) == 2
    assert all(isinstance(a, A.FunctionCall) and a.name == "LOWER" for a in udf.args)


def test_quoted_table_and_schema_names():
    """Table and schema names in double quotes: very common in the log
    (pattern 'SELECT * FROM "schema"."epn_core"', seen more than 30 times
    across different schemas). Already covered indirectly by
    test_select.py::test_quoted_identifier (on a column) but not yet on a
    qualified table name."""
    tree = parse_adql('SELECT * FROM "apis"."epn_core"')
    assert tree.body.from_clause[0].name == "apis.epn_core"


def test_offset_clause_is_valid_adql_2_1():
    """OFFSET is part of the ADQL 2.1 standard (added for pagination, see
    IVOA REC-ADQL-2.1 section 4.10.1 and the standard editor's blog post:
    https://blog.g-vo.org/speak-out-on-adql-2-1.html). Unlike LIMIT (plain
    generic SQL, never standardized in ADQL), OFFSET must therefore be
    accepted -- seen in the log as 'TOP 1 ... OFFSET 0' (the classic hack to
    constrain the Postgres query planner)."""
    tree = parse_adql("SELECT TOP 1 * FROM dynastvo.epn_core OFFSET 0")
    assert tree.body.top == 1
    assert tree.offset == 0


def test_offset_after_order_by():
    """The canonical OFFSET usage as documented in the spec: pagination
    combined with TOP and ORDER BY."""
    tree = parse_adql(
        "SELECT TOP 10 * FROM hipparcos.main ORDER BY parallax DESC OFFSET 10"
    )
    assert tree.body.top == 10
    assert tree.order_by[0].direction == "DESC"
    assert tree.offset == 10


def test_ilike_is_valid_adql_2_1():
    """ILIKE (case-insensitive LIKE) is also part of the ADQL 2.1 standard,
    added alongside LOWER to strengthen text handling (see the standard
    editor's blog post, "LOWER and ILIKE" section). Seen in the log:
    'column_name ILIKE '%mass%''."""
    tree = parse_adql(
        "SELECT column_name FROM TAP_SCHEMA.columns WHERE column_name ILIKE '%mass%'"
    )
    like = tree.body.where
    assert isinstance(like, A.Like)
    assert like.case_insensitive is True
    assert like.negated is False


def test_not_ilike():
    tree = parse_adql("SELECT * FROM t WHERE name NOT ILIKE '%x%'")
    like = tree.body.where
    assert like.case_insensitive is True
    assert like.negated is True


def test_limit_is_correctly_rejected_not_adql():
    """Unlike OFFSET and ILIKE, LIMIT has never been part of ADQL, in any
    version -- ADQL uses TOP instead. Seen 31 times in the log (clients used
    to generic SQL), but a standard-compliant TAP service rejects it too."""
    with pytest.raises(Exception):
        parse_adql("SELECT * FROM exoplanet.epn_core LIMIT 5")
