# PyADQL - pyadql turns an ADQL query into an AST
# Copyright (C) 2026 - Centre National d'Etudes Spatiales (Jean-Christophe Malapert for PDSSP)
# This file is part of PyADQL <https://gitlab.cnes.fr/pdssp/common/pyadql>
# SPDX-License-Identifier: Apache-2.0
"""
AST nodes for ADQL 2.1.

All classes are plain dataclasses with no dependency on Lark, so the AST can
be manipulated / serialized independently of the parser.

See docs/AST.md for a guided tour (diagram, node reference table, worked
example, and a tree-walking recipe) -- this module's docstrings cover each
node individually; docs/AST.md covers how they fit together.

Top-level shape
----------------
`parse_adql()` returns a `SelectExpression`, matching Annex A's own
structure (`query_specification ::= [with_clause] select_expression`, with
`with_clause` folded directly onto `SelectExpression` here for ergonomics --
there's no other content at that level, so nesting a separate wrapper node
just for an optional WITH clause would only add friction):

    SelectExpression
        with_clause: Optional[List[CTE]]   -- WITH ... AS (...), 2.1 only
        body: Query | SetOperation          -- the actual result rows
        order_by: Optional[List[SortItem]]  -- applies to the WHOLE combined result
        offset: Optional[int]               -- ditto (2.1 only)

This mirrors a real, deliberate ADQL 2.1 change from 2.0: ORDER BY / OFFSET
now apply once, to the combined result of any UNION/EXCEPT/INTERSECT, never
to an individual unparenthesized SELECT -- so they live on `SelectExpression`,
not on `Query`. For the common case of a single plain SELECT with no set
operations, `tree.body` is a `Query` holding the familiar
distinct/top/select_list/from_clause/where/group_by/having fields; `tree`
itself holds order_by/offset/with_clause.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union


class Node:
    """Marker base class for all AST nodes."""

    pass


# ---------------------------------------------------------------------------
# Top-level query
# ---------------------------------------------------------------------------
@dataclass
class SelectExpression(Node):
    """Root node returned by parse_adql(). See module docstring for the
    full shape. Also the node produced for *any* parenthesized subquery
    (a CTE's body, a derived table, a scalar subquery, EXISTS's/IN's
    subquery form) -- the same wrapper is reused everywhere a full ADQL
    "SELECT ... [ORDER BY ...] [OFFSET ...]" can appear.

    Example -- "SELECT id FROM t1 UNION SELECT id FROM t2 ORDER BY id":
        SelectExpression(
            body=SetOperation(op='UNION', left=Query(...), right=Query(...)),
            order_by=[SortItem(expr=ColumnRef(['id']), direction='ASC')],
        )
    """

    body: Query | SetOperation
    order_by: list[SortItem] | None = None
    offset: int | None = None
    with_clause: list[CTE] | None = None  # WITH ... AS (...), ADQL 2.1 only


@dataclass
class CTE(Node):
    """One entry of a WITH clause: `name AS (query)` (ADQL 2.1 only).
    `query` is itself a full SelectExpression, so a CTE can use ORDER BY /
    OFFSET internally just like any subquery.

    Example -- "WITH recent AS (SELECT id FROM t WHERE d > 2020) ...":
        CTE(name='recent', query=SelectExpression(body=Query(...)))
    """

    name: str
    query: SelectExpression


@dataclass
class Query(Node):
    """A single `SELECT ... FROM ... [WHERE] [GROUP BY] [HAVING]` (Annex A's
    <select_query>). Does NOT carry ORDER BY / OFFSET -- see SelectExpression
    above for why. This is what you get at `tree.body` for any plain query
    without UNION/EXCEPT/INTERSECT.

    Example -- "SELECT DISTINCT TOP 10 ra FROM t WHERE ra > 5":
        Query(distinct=True, top=10,
              select_list=[SelectItem(expr=ColumnRef(['ra']))],
              from_clause=[TableRef(name='t')],
              where=BinaryOp('>', ColumnRef(['ra']), NumberLiteral(5.0)))
    """

    distinct: bool
    top: int | None
    select_list: Star | list[SelectItem]
    from_clause: list[TableSource]
    where: Expr | None = None
    group_by: list[Expr] | None = None
    having: Expr | None = None


@dataclass
class SetOperation(Node):
    """`UNION` / `EXCEPT` / `INTERSECT` combining two queries. `distinct` is
    True unless the query used the `ALL` keyword (`UNION ALL` keeps
    duplicate rows; plain `UNION` removes them). `left`/`right` are usually
    `Query`, but can themselves be a `SetOperation` (chained set ops, e.g.
    "A UNION B INTERSECT C") or a `SelectExpression` when that operand was
    explicitly parenthesized (which lets it carry its own ORDER BY/OFFSET).

    Example -- "SELECT id FROM t1 UNION ALL SELECT id FROM t2":
        SetOperation(op='UNION', distinct=False, left=Query(...), right=Query(...))
    """

    op: str  # UNION | EXCEPT | INTERSECT
    distinct: bool
    left: Query | SetOperation | SelectExpression
    right: Query | SetOperation | SelectExpression


@dataclass
class Star(Node):
    """`SELECT *` -- no columns to enumerate, all of them are selected."""

    pass


@dataclass
class SelectItem(Node):
    """One entry of the SELECT list: an expression, plus an optional alias.

    Example -- "ra AS right_ascension":
        SelectItem(expr=ColumnRef(['ra']), alias='right_ascension')
    """

    expr: Expr
    alias: str | None = None


@dataclass
class SortItem(Node):
    """One entry of an ORDER BY list: an expression plus a direction.

    Example -- "ORDER BY mag DESC": SortItem(expr=ColumnRef(['mag']), direction='DESC')
    """

    expr: Expr
    direction: str = "ASC"  # ASC | DESC


# ---------------------------------------------------------------------------
# Table sources / joins
# ---------------------------------------------------------------------------
@dataclass
class TableRef(Node):
    """A plain table reference in FROM, e.g. "gaiadr3.gaia_source AS g".
    `name` keeps the schema-qualified name as one dotted string (it is not
    split into separate schema/table fields)."""

    name: str  # may contain schema.table
    alias: str | None = None
    columns: list[str] | None = None  # column renaming (rare)


@dataclass
class DerivedTable(Node):
    """A subquery used as a table in FROM: `(SELECT ...) AS alias`.
    `subquery` is a full SelectExpression (it can have its own ORDER BY,
    for instance)."""

    subquery: SelectExpression
    alias: str | None = None
    columns: list[str] | None = None


@dataclass
class Join(Node):
    """One JOIN in the FROM clause. `left`/`right` are the two table
    sources being joined -- either can itself be a `Join`, which is how a
    chain like "a JOIN b JOIN c" becomes a left-leaning tree:
    Join(left=Join(left=a, right=b), right=c).

    Example -- "t1 AS a LEFT JOIN t2 AS b ON a.id = b.id":
        Join(left=TableRef('t1', 'a'), right=TableRef('t2', 'b'),
             join_type='LEFT', on=BinaryOp('=', ColumnRef(['a','id']), ColumnRef(['b','id'])))
    """

    left: TableSource
    right: TableSource
    join_type: str = "INNER"  # INNER | LEFT | RIGHT | FULL
    natural: bool = False
    on: Expr | None = None
    using: list[str] | None = None


TableSource = Union[TableRef, DerivedTable, Join]


# ---------------------------------------------------------------------------
# Expressions - logic / predicates
# ---------------------------------------------------------------------------
@dataclass
class BinaryOp(Node):
    """Any operator taking two operands: boolean (`AND`/`OR`), arithmetic
    (`+ - * /`), string (`||`), or comparison (`= != < <= > >= <>`) -- one
    class covers all of them since they share the exact same shape; check
    `op` to know which one you're looking at.

    Example -- "ra > 10": BinaryOp(op='>', left=ColumnRef(['ra']), right=NumberLiteral(10.0))
    """

    op: str  # AND, OR, +, -, *, /, ||, =, !=, <, <=, >, >=, <>
    left: Expr
    right: Expr


@dataclass
class UnaryOp(Node):
    """A prefix operator with a single operand: `NOT <condition>`, or unary
    `-x` / `+x`. Note `NOT x BETWEEN a AND b` (this class, wrapping a
    `Between`) is a different AST shape from `x NOT BETWEEN a AND b`
    (a `Between` with `negated=True`) -- both are valid ADQL, meaning the
    same thing, but the negation sits in a different place in the tree.

    Example -- "NOT (a = 1)": UnaryOp(op='NOT', operand=BinaryOp('=', ...))
    """

    op: str  # NOT, -, +
    operand: Expr


@dataclass
class Between(Node):
    """`expr [NOT] BETWEEN low AND high`.

    Example -- "x BETWEEN 1 AND 10":
        Between(expr=ColumnRef(['x']), low=NumberLiteral(1.0), high=NumberLiteral(10.0))
    """

    expr: Expr
    low: Expr
    high: Expr
    negated: bool = False


@dataclass
class InPredicate(Node):
    """`expr [NOT] IN (...)`. `values` is either a plain list of expressions
    (`IN (1, 2, 3)`) or a `SelectExpression` (`IN (SELECT id FROM other)`) --
    check `isinstance(values, list)` to tell which form you have."""

    expr: Expr
    values: list[Expr] | SelectExpression
    negated: bool = False


@dataclass
class Like(Node):
    """`expr [NOT] LIKE pattern` or `expr [NOT] ILIKE pattern`.
    `case_insensitive=True` marks ILIKE (case-insensitive matching, ADQL 2.1)
    as opposed to plain LIKE."""

    expr: Expr
    pattern: Expr
    negated: bool = False
    case_insensitive: bool = False  # True for ILIKE (ADQL 2.1)


@dataclass
class IsNull(Node):
    """`expr IS [NOT] NULL`."""

    expr: Expr
    negated: bool = False


@dataclass
class Exists(Node):
    """`EXISTS (subquery)` -- true iff the subquery returns at least one row."""

    subquery: SelectExpression


@dataclass
class Contains(Node):
    """`CONTAINS(geom1, geom2)` -- a numeric geometry predicate: 1 if geom1
    is (fully) contained within geom2, 0 otherwise. Since it returns a
    number rather than a boolean, it's normally compared explicitly, e.g.
    "CONTAINS(POINT(...), CIRCLE(...)) = 1" -- that comparison shows up as
    an ordinary `BinaryOp('=', Contains(...), NumberLiteral(1.0))` wrapping
    this node, not as a special "contains predicate" of its own."""

    geom1: Expr
    geom2: Expr


@dataclass
class Intersects(Node):
    """`INTERSECTS(geom1, geom2)` -- 1 if the two geometries overlap at all,
    0 otherwise. Same usage pattern as `Contains` (normally wrapped in an
    explicit `= 1` comparison)."""

    geom1: Expr
    geom2: Expr


# ---------------------------------------------------------------------------
# Expressions - values
# ---------------------------------------------------------------------------
@dataclass
class ColumnRef(Node):
    """A column reference, optionally qualified by a table alias:
    `parts` holds each dot-separated segment in order, e.g. `['t', 'ra']`
    for `t.ra`, or just `['ra']` for a bare column name. `str(ref)`
    reconstructs the dotted form."""

    parts: list[str]  # e.g. ['t', 'ra'] for t.ra

    def __str__(self):
        return ".".join(self.parts)


@dataclass
class NumberLiteral(Node):
    """A numeric literal, e.g. `42` or `3.14e10`. Always stored as `float`,
    even for integer-looking literals -- note `TOP 10`'s `10` and
    `OFFSET 5`'s `5` are stored as a plain Python `int` directly on
    `Query.top` / `SelectExpression.offset`, not wrapped in a
    `NumberLiteral`; this class is only for numbers appearing inside
    expressions."""

    value: float


@dataclass
class StringLiteral(Node):
    """A single-quoted string literal, e.g. `'ICRS'`. The value is already
    unescaped (a doubled quote `''` in the source becomes a single `'`
    here)."""

    value: str


@dataclass
class NullLiteral(Node):
    """The `NULL` literal used as a value_expression (as opposed to the
    `IS NULL` predicate, which is `IsNull` above) -- e.g. `COALESCE(x, NULL)`."""

    pass


@dataclass
class BoolLiteral(Node):
    """`TRUE` or `FALSE` used as a literal value."""

    value: bool


@dataclass
class FunctionCall(Node):
    """A call to a *recognized* ADQL function: an aggregate (`COUNT`, `SUM`,
    `AVG`, `MIN`, `MAX`), a numeric/trig function (`ABS`, `SIN`, `MOD`,
    `IN_UNIT`, ...), or a string function (`LOWER`, `UPPER`). `distinct` is
    only meaningful for aggregates (`COUNT(DISTINCT x)`). Contrast with
    `UserFunctionCall`, used for any name pyadql doesn't recognize as a
    built-in ADQL function."""

    name: str
    args: list[Expr] = field(default_factory=list)
    distinct: bool = False


@dataclass
class CountStar(Node):
    """`COUNT(*)` specifically -- kept distinct from `FunctionCall('COUNT', [...])`
    since `*` isn't itself a value_expression argument."""

    pass


@dataclass
class CastType(Node):
    """The target type of a CAST, e.g. `CastType('VARCHAR', [20])` for
    `CAST(x AS VARCHAR(20))`, or `CastType('DOUBLE PRECISION')` for
    `CAST(x AS DOUBLE PRECISION)`. ADQL 2.1 enumerates legal CAST targets
    explicitly (character_string_type | numeric_type | datetime_type |
    geometry_type) rather than accepting an arbitrary type name -- so
    `name` is always one of `CHAR`, `VARCHAR`, `SMALLINT`, `INTEGER`,
    `BIGINT`, `REAL`, `DOUBLE PRECISION`, `TIMESTAMP`, `POINT`, `CIRCLE`,
    `POLYGON`."""

    name: str
    params: list[int] | None = None


@dataclass
class Cast(Node):
    """`CAST(expr AS type)`, ADQL 2.1."""

    expr: Expr
    type: CastType


@dataclass
class Coalesce(Node):
    """`COALESCE(a, b, c, ...)` -- ADQL 2.1 only: evaluates to the first
    non-NULL argument."""

    args: list[Expr]


@dataclass
class UserFunctionCall(Node):
    """A call to a function name pyadql does *not* recognize as a built-in
    ADQL function -- typically a TAP-service-specific user-defined function
    (e.g. `gavo_transform(...)`, `ivo_hashlist_has(...)`), but also the
    fallback for a recognized keyword used with an unexpected argument
    shape (see the "Known limitations" note in the README about
    `POINT(a, b, c)` with a non-string first argument)."""

    name: str
    args: list[Expr] = field(default_factory=list)


@dataclass
class ScalarSubquery(Node):
    """A subquery used as a single value inside an expression, e.g.
    `SELECT (SELECT MAX(x) FROM other) FROM t`. `subquery` is a full
    SelectExpression."""

    subquery: SelectExpression


# -- ADQL geometry ------------------------------------------------------------
@dataclass
class Point(Node):
    """`POINT([coordsys,] ra, dec)`. `coordsys` is `None` when omitted --
    made optional in ADQL 2.1 (it was mandatory in 2.0)."""

    coordsys: Expr | None  # None when omitted (optional as of ADQL 2.1)
    ra: Expr
    dec: Expr


@dataclass
class Circle(Node):
    """`CIRCLE([coordsys,] center, radius)`. `center` is either a
    `Coordinates` pair (`CIRCLE('ICRS', 10, 20, 1)`) or, as of ADQL 2.1, any
    point-valued expression -- a column, a `POINT(...)`/`CENTROID(...)`
    call, or a UDF (`CIRCLE(center_col, 1)`). Check
    `isinstance(center, Coordinates)` to tell the two forms apart."""

    coordsys: Expr | None
    center: Expr  # a (ra, dec) Coordinates pair, or a point-valued Expr (ADQL 2.1)
    radius: Expr


@dataclass
class Box(Node):
    """`BOX([coordsys,] center, width, height)`. `center` follows the same
    two-forms rule as `Circle.center` above. Note: BOX itself is deprecated
    as of ADQL 2.1 (still parsed here, but flagged for eventual removal by
    the standard)."""

    coordsys: Expr | None
    center: Expr  # a (ra, dec) Coordinates pair, or a point-valued Expr (ADQL 2.1)
    width: Expr
    height: Expr


@dataclass
class Coordinates(Node):
    """A raw `(ra, dec)` numeric coordinate pair -- used for `POINT`'s
    argument, and as one alternative for `Circle`/`Box` centers and
    `Polygon` vertices (the other alternative being a point-valued
    expression, see those classes)."""

    ra: Expr
    dec: Expr


@dataclass
class Polygon(Node):
    """`POLYGON([coordsys,] v1, v2, v3, ...)` -- at least 3 vertices.
    `vertices` is either a list of `Coordinates` pairs (`POLYGON('ICRS', 1,2,
    3,4,5,6)`) or, as of ADQL 2.1, a list of point-valued expressions
    (`POLYGON('ICRS', p1, p2, p3)`) -- the two forms are not mixed within
    one call. Check `isinstance(vertices[0], Coordinates)` to tell which
    form you have."""

    coordsys: Expr | None
    vertices: list[Expr]  # list of Coordinates, or list of point-valued Expr (ADQL 2.1)


@dataclass
class Region(Node):
    """`REGION('stc-s string')` -- a region described by an STC-S string
    (a separate mini-language, not parsed further here). ADQL 2.1 narrows
    the argument to a plain string literal (2.0 allowed any string
    expression), so `stcs` is a plain `str`, not an `Expr`."""

    stcs: str  # the raw STC-S string literal (narrowed to a literal in ADQL 2.1)


@dataclass
class Centroid(Node):
    """`CENTROID(geom)` -- the center point of a geometry (e.g. of a
    POLYGON or CIRCLE). Returns a point value, so it can itself be used
    wherever a point-valued expression is expected (a `Circle`/`Box`
    center, a `Polygon` vertex)."""

    geom: Expr


@dataclass
class Area(Node):
    """`AREA(geom)` -- the area of a geometry, in square degrees."""

    geom: Expr


@dataclass
class Coord1(Node):
    """`COORD1(point)` -- the first coordinate (right ascension / longitude)
    of a point value."""

    geom: Expr


@dataclass
class Coord2(Node):
    """`COORD2(point)` -- the second coordinate (declination / latitude) of
    a point value."""

    geom: Expr


@dataclass
class Coordsys(Node):
    """`COORDSYS(geom)` -- extracts the coordinate system string (e.g.
    'ICRS') from a geometry value."""

    geom: Expr


@dataclass
class Distance(Node):
    """`DISTANCE(...)` -- angular distance between two points, in degrees.
    ADQL 2.1 adds a second overload alongside the original two-point form:
    four raw numeric arguments (ra1, dec1, ra2, dec2), the form recommended
    by the standard for an efficient sky crossmatch. `args` is either
    `[point_expr, point_expr]` (`numeric_form=False`) or `[num, num, num,
    num]` (`numeric_form=True`) -- check `numeric_form` rather than
    `len(args)` to tell the two apart unambiguously."""

    args: list[Expr]
    numeric_form: bool = False


Expr = Union[
    BinaryOp,
    UnaryOp,
    Between,
    InPredicate,
    Like,
    IsNull,
    Exists,
    Contains,
    Intersects,
    ColumnRef,
    NumberLiteral,
    StringLiteral,
    NullLiteral,
    BoolLiteral,
    FunctionCall,
    CountStar,
    Cast,
    Coalesce,
    UserFunctionCall,
    ScalarSubquery,
    Point,
    Circle,
    Box,
    Polygon,
    Coordinates,
    Region,
    Centroid,
    Area,
    Coord1,
    Coord2,
    Coordsys,
    Distance,
]
