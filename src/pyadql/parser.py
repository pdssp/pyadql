"""
ADQL 2.1 parser -> typed AST.

Usage:
    from pyadql.parser import parse_adql
    ast = parse_adql("SELECT TOP 10 ra, dec FROM mytable WHERE ra > 10")
"""

from __future__ import annotations

import os
import time

from lark import Lark, Token, Transformer
from loguru import logger

from . import ast_nodes as A

_GRAMMAR_DIR = os.path.join(os.path.dirname(__file__), "grammar")
_GRAMMAR_ENTRY = os.path.join(_GRAMMAR_DIR, "adql.lark")

_lark_parser: Lark | None = None  # compiled lazily, see _get_lark_parser()


def _get_lark_parser() -> Lark:
    """Compile (once, on first call) and cache the Lark parser for the ADQL
    grammar.

    Deliberately lazy rather than run at module import time: compiling the
    Lark grammar takes ~100 ms and emits useful DEBUG logs (duration,
    grammar size) -- if that happened at `pyadql` import time (triggered by
    a bare `import pyadql`, before an application has had a chance to
    configure its loguru sinks), those logs would either be invisible or
    emitted with loguru's default configuration, ignoring the verbosity
    level requested by the caller (e.g. the CLI's -v/-vv/-q flags).

    The grammar itself is split across several files under grammar/
    (lexer.lark, literals.lark, core.lark, adql.lark) for readability --
    see the header comment in grammar/core.lark for why the mutually
    recursive "core" of the grammar couldn't be split further. Lark.open()
    resolves the relative %import statements between those files against
    grammar/adql.lark's own directory.
    """
    global _lark_parser
    if _lark_parser is not None:
        return _lark_parser

    logger.debug("Loading the ADQL grammar from {}", _GRAMMAR_ENTRY)

    # Earley: more tolerant of the ambiguities inherent to a SQL-like grammar
    # than LALR, which matters for covering all of ADQL without having to
    # manually resolve every ambiguity by hand.
    t0 = time.perf_counter()
    _lark_parser = Lark.open(
        _GRAMMAR_ENTRY, rel_to=_GRAMMAR_ENTRY, parser="earley", ambiguity="resolve"
    )
    logger.debug(
        "ADQL grammar compiled in {:.1f} ms (earley engine, multi-file grammar under {})",
        (time.perf_counter() - t0) * 1000,
        _GRAMMAR_DIR,
    )
    return _lark_parser


# ---------------------------------------------------------------------------
# Internal markers used while assembling composite rules (select_query,
# select_expression, table_expression, joins, ...). Avoids introducing
# public AST classes for pure construction details.
# ---------------------------------------------------------------------------
class _Marker:
    def __init__(self, kind, value=None):
        self.kind = kind
        self.value = value


def _unwrap_name(tok) -> str:
    """Convert a NAME token into a plain Python identifier, handling
    double-quoted (delimited, case-sensitive) identifiers, including the
    doubled-double-quote escape for a literal " inside them
    ([AnnexA #delimited_identifier], #double_quote_symbol)."""
    s = str(tok)
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1].replace('""', '"')
    return s


def _unwrap_string(tok) -> str:
    s = str(tok)
    # strip the surrounding SQL quotes and undo the doubled-quote escape ('')
    return s[1:-1].replace("''", "'")


class ADQLTransformer(Transformer):
    # -- literals -------------------------------------------------------------
    def number_literal(self, c):
        return A.NumberLiteral(float(c[0]))

    def string_literal(self, c):
        return A.StringLiteral(_unwrap_string(c[0]))

    def null_literal(self, c):
        return A.NullLiteral()

    def true_literal(self, c):
        return A.BoolLiteral(True)

    def false_literal(self, c):
        return A.BoolLiteral(False)

    # -- CAST target types ------------------------------------------------------
    def string_cast_type(self, c):
        name = str(c[0]).upper()
        params = [int(t) for t in c[1:]] if len(c) > 1 else None
        return A.CastType(name, params)

    def numeric_cast_type(self, c):
        return A.CastType(" ".join(str(t).upper() for t in c))

    def datetime_cast_type(self, c):
        return A.CastType(str(c[0]).upper())

    def geometry_cast_type(self, c):
        return A.CastType(str(c[0]).upper())

    # -- identifiers ------------------------------------------------------------
    def correlated_name(self, c):
        return _unwrap_name(c[0])

    def column_name(self, c):
        return _unwrap_name(c[0])

    def query_name(self, c):
        return _unwrap_name(c[0])

    def table_name(self, c):
        return ".".join(_unwrap_name(t) for t in c)

    def column_reference(self, c):
        # lark.Token subclasses str: conversion must be forced for every
        # segment, otherwise "raw" segments (t.<NAME>) stay Token instances
        # in the repr, even though isinstance(x, str) is already true.
        parts = [_unwrap_name(p) if isinstance(p, Token) else p for p in c]
        return A.ColumnRef(parts)

    def column_name_list(self, c):
        return list(c)

    # -- arithmetic / logical operators ---------------------------------------
    def add(self, c):
        return A.BinaryOp("+", c[0], c[1])

    def sub(self, c):
        return A.BinaryOp("-", c[0], c[1])

    def mul(self, c):
        return A.BinaryOp("*", c[0], c[1])

    def div(self, c):
        return A.BinaryOp("/", c[0], c[1])

    def neg(self, c):
        return A.UnaryOp("-", c[0])

    def pos(self, c):
        return A.UnaryOp("+", c[0])

    def concat(self, c):
        return A.BinaryOp("||", c[0], c[1])

    def and_(self, c):
        return A.BinaryOp("AND", c[0], c[1])

    def or_(self, c):
        return A.BinaryOp("OR", c[0], c[1])

    def not_(self, c):
        return A.UnaryOp("NOT", c[0])

    def scalar_subquery(self, c):
        return A.ScalarSubquery(c[0])

    # -- predicates -------------------------------------------------------------
    def comparison_predicate(self, c):
        left, op, right = c[0], str(c[1]), c[2]
        return A.BinaryOp(op, left, right)

    def between_predicate(self, c):
        negated = any(isinstance(t, Token) and t.type == "NOT_KW" for t in c)
        vals = [x for x in c if not (isinstance(x, Token) and x.type == "NOT_KW")]
        expr, low, high = vals
        return A.Between(expr, low, high, negated)

    def in_predicate(self, c):
        negated = any(isinstance(t, Token) and t.type == "NOT_KW" for t in c)
        vals = [x for x in c if not (isinstance(x, Token) and x.type == "NOT_KW")]
        expr, values = vals[0], vals[1]
        return A.InPredicate(expr, values, negated)

    def in_predicate_value(self, c):
        return c[0]

    def in_subquery(self, c):
        return c[0]

    def in_value_list(self, c):
        return list(c)

    def like_predicate(self, c):
        negated = any(isinstance(t, Token) and t.type == "NOT_KW" for t in c)
        case_insensitive = any(isinstance(t, Token) and t.type == "ILIKE_KW" for t in c)
        vals = [
            x
            for x in c
            if not (
                isinstance(x, Token) and x.type in ("NOT_KW", "LIKE_KW", "ILIKE_KW")
            )
        ]
        expr, pattern = vals
        return A.Like(expr, pattern, negated, case_insensitive)

    def null_predicate(self, c):
        negated = any(isinstance(t, Token) and t.type == "NOT_KW" for t in c)
        expr = c[0]
        return A.IsNull(expr, negated)

    def exists_predicate(self, c):
        return A.Exists(c[0])

    # -- functions --------------------------------------------------------
    def function_call(self, c):
        return c[0]

    def set_function(self, c):
        name = str(c[0]).upper()
        rest = c[1:]
        distinct = False
        args = []
        for item in rest:
            if isinstance(item, _Marker) and item.kind == "DISTINCT":
                distinct = True
            elif isinstance(item, _Marker) and item.kind == "ALL":
                distinct = False
            else:
                args.append(item)
        return A.FunctionCall(name, args, distinct)

    def count_star(self, c):
        return A.CountStar()

    def numeric_function(self, c):
        name = str(c[0]).upper()
        args = list(c[1]) if len(c) > 1 else []
        return A.FunctionCall(name, args, False)

    def string_function(self, c):
        name = str(c[0]).upper()
        args = list(c[1]) if len(c) > 1 else []
        return A.FunctionCall(name, args, False)

    def udf(self, c):
        name = c[0]
        args = list(c[1]) if len(c) > 1 else []
        return A.UserFunctionCall(name, args)

    def arg_list(self, c):
        return list(c)

    def cast_specification(self, c):
        return A.Cast(c[0], c[1])

    def coalesce_expression(self, c):
        return A.Coalesce(list(c))

    # -- geometry ----------------------------------------------------------
    def geometry_function(self, c):
        return c[0]

    def coord_sys(self, c):
        return A.StringLiteral(_unwrap_string(c[0]))

    def coordinates(self, c):
        return A.Coordinates(c[0], c[1])

    def radius(self, c):
        return c[0]

    def coord_value(self, c):
        return c[0]

    def udf_as_point(self, c):
        name = c[0]
        args = list(c[1]) if len(c) > 1 else []
        return A.UserFunctionCall(name, args)

    def point_expr(self, c):
        # children: [coord_sys?] coordinates
        if len(c) == 2:
            coordsys, coords = c
        else:
            coordsys, coords = None, c[0]
        return A.Point(coordsys, coords.ra, coords.dec)

    def circle_center(self, c):
        return c[0]

    def circle_expr(self, c):
        # children: [coord_sys?] circle_center radius
        if len(c) == 3:
            coordsys, center, radius = c
        else:
            coordsys = None
            center, radius = c
        return A.Circle(coordsys, center, radius)

    def box_center(self, c):
        return c[0]

    def box_expr(self, c):
        # children: [coord_sys?] box_center width height
        if len(c) == 4:
            coordsys, center, width, height = c
        else:
            coordsys = None
            center, width, height = c
        return A.Box(coordsys, center, width, height)

    def polygon_vertices_coords(self, c):
        return list(c)

    def polygon_vertices_points(self, c):
        return list(c)

    def polygon_expr(self, c):
        # children: [coord_sys?] polygon_vertices(list)
        if len(c) == 2:
            coordsys, vertices = c
        else:
            coordsys, vertices = None, c[0]
        return A.Polygon(coordsys, vertices)

    def region_expr(self, c):
        return A.Region(_unwrap_string(c[0]))

    def centroid_expr(self, c):
        return A.Centroid(c[0])

    def area_expr(self, c):
        return A.Area(c[0])

    def coord1_expr(self, c):
        return A.Coord1(c[0])

    def coord2_expr(self, c):
        return A.Coord2(c[0])

    def coordsys_expr(self, c):
        return A.Coordsys(c[0])

    def distance_points(self, c):
        return A.Distance(list(c), numeric_form=False)

    def distance_coords(self, c):
        return A.Distance(list(c), numeric_form=True)

    def contains_expr(self, c):
        return A.Contains(c[0], c[1])

    def intersects_expr(self, c):
        return A.Intersects(c[0], c[1])

    # -- SELECT / clauses -----------------------------------------------------
    def distinct(self, c):
        return _Marker("DISTINCT")

    def all_(self, c):
        return _Marker("ALL")

    def top(self, c):
        return _Marker("TOP", int(c[0]))

    def star_select(self, c):
        return A.Star()

    def qualified_star(self, c):
        return A.Star()  # qualified star (t.*) simplified to a generic Star

    def alias(self, c):
        return _Marker("ALIAS", c[0])

    def derived_column(self, c):
        expr = c[0]
        alias = None
        if len(c) > 1 and isinstance(c[1], _Marker) and c[1].kind == "ALIAS":
            alias = c[1].value
        return A.SelectItem(expr, alias)

    def select_sublist(self, c):
        return c[0]

    def select_items(self, c):
        return list(c)

    def asc(self, c):
        return "ASC"

    def desc(self, c):
        return "DESC"

    def sort_spec(self, c):
        expr = c[0]
        direction = c[1] if len(c) > 1 else "ASC"
        return A.SortItem(expr, direction)

    def where_clause(self, c):
        return _Marker("WHERE", c[0])

    def group_by_clause(self, c):
        return _Marker("GROUP_BY", list(c))

    def having_clause(self, c):
        return _Marker("HAVING", c[0])

    def order_by_clause(self, c):
        return _Marker("ORDER_BY", list(c))

    def offset_clause(self, c):
        return _Marker("OFFSET", int(c[0]))

    def from_clause(self, c):
        return list(c)

    def select_query(self, c):
        distinct = False
        top = None
        select_list = None
        from_clause = []
        where = None
        group_by = None
        having = None
        for item in c:
            if isinstance(item, _Marker):
                if item.kind == "DISTINCT":
                    distinct = True
                elif item.kind == "ALL":
                    distinct = False
                elif item.kind == "TOP":
                    top = item.value
                elif item.kind == "WHERE":
                    where = item.value
                elif item.kind == "GROUP_BY":
                    group_by = item.value
                elif item.kind == "HAVING":
                    having = item.value
            elif isinstance(item, A.Star) or isinstance(item, list):
                # `list` items are ambiguous between select_items and
                # from_clause -- from_clause always comes after select_list
                # positionally, so the first list/Star we see is select_list
                # and any subsequent list is from_clause.
                if select_list is None:
                    select_list = item
                else:
                    from_clause = item
        return A.Query(
            distinct=distinct,
            top=top,
            select_list=select_list,
            from_clause=from_clause,
            where=where,
            group_by=group_by,
            having=having,
        )

    # -- set operations / select_expression -----------------------------------
    def _set_op(self, op_name, c):
        left = c[0]
        right = c[-1]
        distinct = not any(
            isinstance(item, Token) and item.type == "ALL_KW" for item in c[1:-1]
        )
        return A.SetOperation(op_name, distinct, left, right)

    def union_op(self, c):
        return self._set_op("UNION", c)

    def except_op(self, c):
        return self._set_op("EXCEPT", c)

    def intersect_op(self, c):
        return self._set_op("INTERSECT", c)

    def paren_select_expression(self, c):
        return c[0]

    def select_expression(self, c):
        body = c[0]
        order_by = None
        offset = None
        for item in c[1:]:
            if isinstance(item, _Marker) and item.kind == "ORDER_BY":
                order_by = item.value
            elif isinstance(item, _Marker) and item.kind == "OFFSET":
                offset = item.value
        return A.SelectExpression(body=body, order_by=order_by, offset=offset)

    def with_query(self, c):
        return A.CTE(c[0], c[1])

    def with_clause(self, c):
        return _Marker("WITH", list(c))

    def query_specification(self, c):
        with_clause = None
        select_expression = None
        for item in c:
            if isinstance(item, _Marker) and item.kind == "WITH":
                with_clause = item.value
            elif isinstance(item, A.SelectExpression):
                select_expression = item
        select_expression.with_clause = with_clause
        return select_expression

    # -- FROM / joins -----------------------------------------------------
    def table_ref(self, c):
        name = c[0]
        alias, cols = None, None
        if len(c) > 1 and c[1] is not None:
            alias, cols = c[1]
        return A.TableRef(name, alias, cols)

    def derived_table(self, c):
        subquery = c[0]
        alias, cols = None, None
        if len(c) > 1 and c[1] is not None:
            alias, cols = c[1]
        return A.DerivedTable(subquery, alias, cols)

    def paren_table_ref(self, c):
        return c[0]

    def correlation_specification(self, c):
        alias = c[0]
        cols = c[1] if len(c) > 1 else None
        return (alias, cols)

    def inner_join(self, c):
        return "INNER"

    def left_join(self, c):
        return "LEFT"

    def right_join(self, c):
        return "RIGHT"

    def full_join(self, c):
        return "FULL"

    def on_spec(self, c):
        return _Marker("ON", c[0])

    def using_spec(self, c):
        return _Marker("USING", list(c))

    def joined(self, c):
        natural = False
        join_type = "INNER"
        right = None
        on = None
        using = None
        for item in c:
            if isinstance(item, Token) and item.upper() == "NATURAL":
                natural = True
            elif item in ("INNER", "LEFT", "RIGHT", "FULL"):
                join_type = item
            elif isinstance(item, _Marker) and item.kind == "ON":
                on = item.value
            elif isinstance(item, _Marker) and item.kind == "USING":
                using = item.value
            elif isinstance(item, (A.TableRef, A.DerivedTable, A.Join)):
                right = item
        return _Marker("JOINED", (natural, join_type, right, on, using))

    def table_reference(self, c):
        base = c[0]
        for jm in c[1:]:
            natural, join_type, right, on, using = jm.value
            base = A.Join(base, right, join_type, natural, on, using)
        return base

    def start(self, c):
        return c[0]


_transformer = ADQLTransformer()


def _summarize_ast(ast) -> str:
    """Compact summary of an AST for DEBUG logs (avoids dumping the whole
    tree when the goal is just to confirm its general shape)."""
    if not isinstance(ast, A.SelectExpression):
        return type(ast).__name__
    body = ast.body
    if isinstance(body, A.SetOperation):
        body_desc = f"SetOperation(op={body.op}, distinct={body.distinct})"
    elif isinstance(body, A.Query):
        n_select = 1 if isinstance(body.select_list, A.Star) else len(body.select_list)
        body_desc = (
            f"Query(distinct={body.distinct}, top={body.top}, "
            f"n_select={n_select}, n_from={len(body.from_clause)}, "
            f"where={body.where is not None}, group_by={body.group_by is not None}, "
            f"having={body.having is not None})"
        )
    else:
        body_desc = type(body).__name__
    return (
        f"SelectExpression(with_clause={ast.with_clause is not None}, "
        f"order_by={ast.order_by is not None}, offset={ast.offset}, body={body_desc})"
    )


def parse_adql(query: str):
    """Parse an ADQL query and return the root of the typed AST
    (an ast_nodes.SelectExpression; see that class's docstring for the full
    shape)."""
    logger.debug("parse_adql: query of {} characters", len(query))

    t0 = time.perf_counter()
    try:
        tree = _get_lark_parser().parse(query)
    except Exception:
        logger.debug(
            "Failed at the grammar stage (Lark) after {:.1f} ms -- the query "
            "does not follow the expected ADQL/SQL syntax",
            (time.perf_counter() - t0) * 1000,
        )
        raise
    t_parse = time.perf_counter()
    logger.debug(
        "Lark tree obtained in {:.1f} ms ({} direct children under 'start')",
        (t_parse - t0) * 1000,
        len(tree.children),
    )
    logger.opt(lazy=True).trace("Raw Lark tree:\n{}", lambda: tree.pretty())

    try:
        ast = _transformer.transform(tree)
    except Exception:
        logger.debug(
            "Failed at the transformer stage (Lark tree -> typed AST) after "
            "{:.1f} ms -- the grammar matched but building the AST node "
            "failed (check ADQLTransformer in parser.py)",
            (time.perf_counter() - t_parse) * 1000,
        )
        raise
    logger.debug(
        "AST built in {:.1f} ms (total parse+transform: {:.1f} ms): {}",
        (time.perf_counter() - t_parse) * 1000,
        (time.perf_counter() - t0) * 1000,
        _summarize_ast(ast),
    )
    return ast


def parse_tree(query: str):
    """Return the raw Lark parse tree (useful for debugging the grammar)."""
    logger.debug("parse_tree: query of {} characters", len(query))
    t0 = time.perf_counter()
    tree = _get_lark_parser().parse(query)
    logger.debug("Lark tree obtained in {:.1f} ms", (time.perf_counter() - t0) * 1000)
    return tree
