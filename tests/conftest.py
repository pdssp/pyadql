import pytest
from loguru import logger

from pyadql import ast_nodes as A
from pyadql import parse_adql


@pytest.fixture
def parse():
    """Shortcut: parse(query) -> AST (the root SelectExpression)."""
    return parse_adql


@pytest.fixture
def parse_query():
    """Shortcut for tests that only care about a single SELECT's own
    fields (distinct/top/select_list/from_clause/where/group_by/having):
    parse_query(query) -> the inner ast_nodes.Query, i.e. parse_adql(query).body.
    ORDER BY / OFFSET / WITH live one level up, on the SelectExpression
    wrapper -- use the `parse` fixture directly for tests about those."""

    def _parse_query(query):
        return parse_adql(query).body

    return _parse_query


@pytest.fixture(autouse=True)
def _reset_loguru_handlers():
    """CLI tests (cli_test.py) configure a loguru handler pointing at the
    stream captured by `capsys`, which is closed at the end of the test.
    Without this reset, loguru keeps that reference around, and a later test
    that logs (via parse_adql -> logger.debug) writes to an already-closed
    stream, producing a noisy "Logging Error" (non-fatal, but distracting)
    in the test suite output."""
    yield
    logger.remove()
