# PyADQL - pyadql turns an ADQL query into an AST
# Copyright (C) 2026 - Centre National d'Etudes Spatiales (Jean-Christophe Malapert for PDSSP)
# This file is part of PyADQL <https://gitlab.cnes.fr/pdssp/common/pyadql>
# SPDX-License-Identifier: Apache-2.0
"""
pyadql -- ADQL 2.1 parser producing a typed Python AST.

Example:

    >>> from pyadql import parse_adql
    >>> tree = parse_adql("SELECT TOP 10 ra, dec FROM mytable WHERE ra > 10")
    >>> tree.body.top
    10

Note the root node is a ``SelectExpression``, not the ``SELECT`` itself: per
ADQL 2.1's own grammar, ``ORDER BY``/``OFFSET``/``WITH`` apply to the whole
combined query (after any ``UNION``/``EXCEPT``/``INTERSECT``), not to an
individual ``SELECT`` -- so ``tree.body`` holds the actual query (a
``Query`` or a ``SetOperation``), while ``tree.order_by``/``tree.offset``/
``tree.with_clause`` live on ``tree`` itself. See ``ast_nodes.SelectExpression``'s
docstring for the full shape.

Package architecture
---------------------
This package is split into four small, single-purpose modules, plus a
sub-package holding the grammar itself:

- ``grammar/`` (``lexer.lark``, ``literals.lark``, ``core.lark``, ``adql.lark``)
    The ADQL 2.1 grammar, written for the `Lark <https://github.com/lark-parser/lark>`_
    parsing library (Earley engine), transcribed directly from Annex A of
    IVOA Recommendation ADQL 2.1. Pure grammar text (no Python), loaded and
    compiled lazily on first use by ``parser._get_lark_parser()`` from
    ``grammar/adql.lark`` (the entry point, which assembles the other three
    files). Every rule is commented with a cross-reference to the exact
    Annex A production it implements (``[AnnexA #x]``). ``core.lark`` holds
    the mutually-recursive heart of the grammar (query structure,
    predicates, value expressions, functions, geometry) in one file quite
    deliberately -- see that file's own header comment for the Lark
    constraints (experimentally confirmed) that make a deeper split unsafe.
    This is the place to look first when adding support for a new piece of
    ADQL syntax.

- ``ast_nodes``
    Defines every AST node as a plain ``@dataclass``: ``SelectExpression``
    (the root), ``Query``, ``SetOperation``, ``CTE``, ``TableRef``,
    ``Join``, ``BinaryOp``, ``Between``, ``InPredicate``, ``Like``,
    ``IsNull``, ``Exists``, ``Cast``/``CastType``, ``Coalesce``, the
    geometry nodes ``Point``/``Circle``/``Box``/``Polygon``/``Coordinates``/
    ``Region``/``Contains``/``Intersects``/``Distance``/etc., and more.
    This module has **no dependency on Lark**: the AST it defines can be
    built, inspected, serialized, and tested completely independently of
    the parser, which keeps the public data model stable even if the
    parsing engine were ever swapped out.

- ``parser``
    The bridge between the grammar and the AST: compiles the multi-file
    Lark grammar (``_get_lark_parser()``, lazy + cached, resolving
    ``grammar/adql.lark``'s relative ``%import`` statements via
    ``Lark.open(..., rel_to=...)``) and defines ``ADQLTransformer``, a
    ``lark.Transformer`` with one method per grammar rule that turns each
    Lark parse-tree node into the matching ``ast_nodes`` dataclass. Exposes
    the two public entry points re-exported below: ``parse_adql`` (query ->
    typed AST) and ``parse_tree`` (query -> raw Lark tree, mainly useful for
    debugging the grammar itself). Also emits structured ``loguru`` debug
    logs (grammar-compilation time, Lark-parsing time, AST-building time,
    AST summary) that the CLI's ``-v``/``-vv``/``-vvv`` flags surface.

- ``cli``
    The ``pyadql`` command-line entry point (declared in ``pyproject.toml``
    under ``[project.scripts]``). A thin ``argparse``-based wrapper around
    ``parse_adql``/``parse_tree`` that reads a query from an argument, a
    file, or stdin, prints the AST (as a Python repr, JSON, or a raw Lark
    tree), and configures ``loguru`` logging verbosity. Not imported by the
    two lines below -- it depends on the rest of the package, not the other
    way around, so importing ``pyadql`` as a library never pulls in
    ``argparse``/CLI-only concerns.

Data flow for a single call to ``parse_adql(query)``:
    query (str)
      -> Lark parser (``grammar/adql.lark`` + imports, compiled once, cached)
      -> raw Lark parse tree
      -> ``ADQLTransformer`` (``parser.py``)
      -> typed AST (``ast_nodes.SelectExpression``, wrapping a ``Query`` or
         ``SetOperation`` in ``.body``)
"""

from . import ast_nodes
from ._version import (
    __author__,
    __author_email__,
    __copyright__,
    __description__,
    __license__,
    __name_soft__,
    __title__,
    __url__,
    __version__,
)
from .config import configure_logging
from .parser import parse_adql, parse_tree

configure_logging()

__all__ = ["parse_adql", "parse_tree", "ast_nodes"]
