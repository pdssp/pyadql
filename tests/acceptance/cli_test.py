import json

import pytest

from pyadql import ast_nodes as A
from pyadql import parse_adql
from pyadql.__main__ import node_to_dict, run


def test_cli_basic_query_success(capsys):
    code = run(["SELECT ra, dec FROM t"])
    captured = capsys.readouterr()
    assert code == 0
    assert "SelectExpression(" in captured.out
    assert "ColumnRef(parts=['ra'])" in captured.out


def test_cli_json_output(capsys):
    code = run(["SELECT ra FROM t", "--json"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["_type"] == "SelectExpression"
    assert data["body"]["_type"] == "Query"
    assert data["body"]["select_list"][0]["expr"]["_type"] == "ColumnRef"
    assert data["body"]["select_list"][0]["expr"]["parts"] == ["ra"]


def test_cli_tree_output(capsys):
    code = run(["SELECT ra FROM t", "--tree"])
    captured = capsys.readouterr()
    assert code == 0
    assert "query_specification" in captured.out
    assert "column_reference" in captured.out


def test_cli_invalid_query_returns_error_code(capsys):
    code = run(["SELECT FROM WHERE"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""  # nothing on stdout when it fails


def test_cli_empty_query_returns_usage_error(capsys):
    code = run(["   "])
    assert code == 2


def test_cli_reads_from_file(tmp_path, capsys):
    query_file = tmp_path / "query.adql"
    query_file.write_text("SELECT COUNT(*) FROM stars")
    code = run(["-f", str(query_file)])
    captured = capsys.readouterr()
    assert code == 0
    assert "CountStar()" in captured.out


def test_cli_verbose_logs_go_to_stderr(capsys):
    code = run(["SELECT ra FROM t", "--level", "DEBUG"])
    captured = capsys.readouterr()
    assert code == 0
    assert "DEBUG" in captured.err
    assert "SUCCESS" in captured.err
    # stdout should only contain the result, not the logs
    assert "DEBUG" not in captured.out


def test_cli_quiet_suppresses_info_logs(capsys):
    code = run(["SELECT ra FROM t", "--level", "ERROR"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""


def test_cli_default_verbosity_is_completely_silent(capsys):
    """Without --level, no log should appear on stderr (WARNING level,
    and none of our logs are emitted at that level on success)."""
    code = run(["SELECT ra FROM t"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""


def test_cli_debug_includes_grammar_compilation_log(monkeypatch, capsys):
    """Checks that the grammar-compilation logs (in parser.py) honor the
    level requested by the CLI, even though compilation is triggered from
    inside parse_adql(). We force a recompilation by resetting the cache so
    this doesn't depend on test execution order."""
    import pyadql.parser as parser_module

    monkeypatch.setattr(parser_module, "_lark_parser", None)

    code = run(["SELECT ra FROM t", "--level", "DEBUG"])
    captured = capsys.readouterr()
    assert code == 0
    assert "ADQL grammar compiled" in captured.err


def test_cli_trace_shows_raw_lark_tree(capsys):
    code = run(["SELECT ra FROM t", "--level", "TRACE"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Raw Lark tree" in captured.err
    assert "query_specification" in captured.err


def test_node_to_dict_preserves_type_information():
    ast = parse_adql("SELECT * FROM t WHERE x = 1")
    d = node_to_dict(ast)
    assert d["_type"] == "SelectExpression"
    assert d["body"]["_type"] == "Query"
    assert d["body"]["where"]["_type"] == "BinaryOp"
    assert d["body"]["where"]["op"] == "="
    assert d["body"]["where"]["left"]["_type"] == "ColumnRef"


def test_node_to_dict_handles_star_and_lists():
    ast = parse_adql("SELECT * FROM t")
    d = node_to_dict(ast)
    assert d["body"]["select_list"]["_type"] == "Star"
    assert isinstance(d["body"]["from_clause"], list)
    assert d["body"]["from_clause"][0]["_type"] == "TableRef"
