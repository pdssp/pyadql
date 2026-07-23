"""
CLI tests that go through the actually-installed `pyadql` executable
(subprocess), as opposed to test_cli.py which calls main() directly in
Python.

These tests exercise the full chain: console entry point (declared in
pyproject.toml under [project.scripts]) -> package import -> execution ->
exit code and stdout/stderr streams, exactly as a user would see the command
from a terminal.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _find_pyadql_executable() -> str | None:
    """Locate the `pyadql` executable installed by `uv sync` / `pip install`.

    We first look next to the current Python interpreter (the normal case:
    the console script is installed in the same venv, e.g.
    .venv/bin/pyadql), then fall back to the PATH."""
    venv_script = Path(sys.executable).parent / "pyadql"
    if venv_script.exists():
        return str(venv_script)
    return shutil.which("pyadql")


PYADQL_BIN = _find_pyadql_executable()

pytestmark = pytest.mark.skipif(
    PYADQL_BIN is None,
    reason="`pyadql` executable not found (uv sync should install it in .venv/bin)",
)


def test_executable_basic_query(tmp_path):
    result = subprocess.run(
        [PYADQL_BIN, "SELECT ra, dec FROM t"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "SelectExpression(" in result.stdout
    assert "ColumnRef(parts=['ra'])" in result.stdout
    assert result.stderr == ""  # default WARNING level: silent


def test_executable_invalid_query_exit_code_and_stderr():
    result = subprocess.run(
        [PYADQL_BIN, "SELECT FROM WHERE"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stdout == ""  # nothing on stdout when it fails
    assert "ADQL parsing failed" in result.stderr


def test_executable_verbose_debug_logs():
    result = subprocess.run(
        [PYADQL_BIN, "SELECT ra FROM t", "--level", "DEBUG"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "DEBUG" in result.stderr
    assert "SelectExpression(" in result.stdout
    assert "DEBUG" not in result.stdout  # logs and result stay cleanly separated


def test_executable_reads_from_stdin():
    result = subprocess.run(
        [PYADQL_BIN],
        input="SELECT COUNT(*) FROM t",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "CountStar()" in result.stdout


def test_executable_reads_from_file(tmp_path):
    query_file = tmp_path / "query.adql"
    query_file.write_text("SELECT TOP 5 ra FROM stars")

    result = subprocess.run(
        [PYADQL_BIN, "-f", str(query_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "top=5" in result.stdout


def test_executable_json_output_is_valid_json():
    import json

    result = subprocess.run(
        [PYADQL_BIN, "SELECT ra FROM t", "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["_type"] == "SelectExpression"
