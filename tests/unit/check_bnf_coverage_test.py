"""
Unit tests for scripts/check_bnf_coverage.py -- the tool that cross-checks
grammar/*.lark against ADQL 2.1's Annex A nonterminal list.

The script lives under scripts/, not src/pyadql/, so it isn't installed as
part of the pyadql package: it's loaded directly from its file path below,
by module name, rather than imported normally.
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "check_bnf_coverage.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("check_bnf_coverage", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bnf_mod():
    """The check_bnf_coverage module, loaded once per test module."""
    return _load_script_module()


# ---------------------------------------------------------------------------
# extract_bnf_definitions: parsing "<name> ::= ..." out of a BNF text
# ---------------------------------------------------------------------------
def test_extract_bnf_definitions_basic(bnf_mod):
    text = "  <foo> ::= bar | baz\n  <qux> ::= <foo> quux\n"
    assert bnf_mod.extract_bnf_definitions(text) == {"foo", "qux"}


def test_extract_bnf_definitions_ignores_references(bnf_mod):
    """Only the left-hand side of ::= counts as a definition; <foo>
    appearing on the right-hand side of <qux>'s definition must not itself
    be reported as defined again."""
    text = "<qux> ::= <foo> <bar>\n"
    assert bnf_mod.extract_bnf_definitions(text) == {"qux"}


def test_extract_bnf_definitions_handles_space_in_name(bnf_mod):
    """Annex A itself has one nonterminal with a literal space in its name
    (<unqualified_schema name>, likely a spec typo) -- the extractor must
    preserve it verbatim rather than crash or silently drop it."""
    text = "<unqualified_schema name> ::= <identifier>\n"
    assert bnf_mod.extract_bnf_definitions(text) == {"unqualified_schema name"}


# ---------------------------------------------------------------------------
# find_punctuation_like: detecting <comma> ::= , style pure-literal rules
# ---------------------------------------------------------------------------
def test_find_punctuation_like_detects_short_literals(bnf_mod):
    text = "<comma> ::= ,\n<left_paren> ::= (\n"
    defined = {"comma", "left_paren"}
    assert bnf_mod.find_punctuation_like(text, defined) == {"comma", "left_paren"}


def test_find_punctuation_like_ignores_structural_rules(bnf_mod):
    """A rule whose body references other nonterminals (contains '<') is
    never punctuation, however short its body might look."""
    text = "<point> ::= POINT <left_paren> <coord_sys> <right_paren>\n"
    defined = {"point"}
    assert bnf_mod.find_punctuation_like(text, defined) == set()


def test_find_punctuation_like_ignores_long_literal_bodies(bnf_mod):
    """A body longer than 3 characters is treated as structural even
    without a nested <...> (e.g. a multi-word keyword production), not as
    punctuation."""
    text = "<something> ::= ABCDEF\n"
    defined = {"something"}
    assert bnf_mod.find_punctuation_like(text, defined) == set()


# ---------------------------------------------------------------------------
# extract_lark_names: rule names and -> alias names from a .lark file
# ---------------------------------------------------------------------------
def test_extract_lark_names_plain_rule(bnf_mod, tmp_path):
    lark_file = tmp_path / "sample.lark"
    lark_file.write_text('foo: "a" bar\nbar: "b"\n')
    assert bnf_mod.extract_lark_names(lark_file) == {"foo", "bar"}


def test_extract_lark_names_inlined_rule_prefix(bnf_mod, tmp_path):
    """The '?' inlining prefix must not become part of the captured name."""
    lark_file = tmp_path / "sample.lark"
    lark_file.write_text("?foo: bar\n")
    assert bnf_mod.extract_lark_names(lark_file) == {"foo"}


def test_extract_lark_names_captures_aliases(bnf_mod, tmp_path):
    """A '-> alias' branch introduces a name the transformer dispatches on,
    distinct from (and in addition to) the rule name itself."""
    lark_file = tmp_path / "sample.lark"
    lark_file.write_text('foo: "a" -> alias_a\n   | "b" -> alias_b\n')
    assert bnf_mod.extract_lark_names(lark_file) == {"foo", "alias_a", "alias_b"}


def test_extract_lark_names_ignores_comments(bnf_mod, tmp_path):
    lark_file = tmp_path / "sample.lark"
    lark_file.write_text('// commented_out: "x"\nreal_rule: "y"\n')
    names = bnf_mod.extract_lark_names(lark_file)
    assert "real_rule" in names
    assert "commented_out" not in names


def test_extract_lark_names_captures_rule_priority(bnf_mod, tmp_path):
    """A rule priority suffix (e.g. `.-1`) must not break name extraction."""
    lark_file = tmp_path / "sample.lark"
    lark_file.write_text("user_defined_function.-1: NAME\n")
    assert bnf_mod.extract_lark_names(lark_file) == {"user_defined_function"}


# ---------------------------------------------------------------------------
# is_covered: same-name match, single alias, list-of-candidates alias
# ---------------------------------------------------------------------------
def test_is_covered_same_name_case_insensitive(bnf_mod):
    lark_names = {"select_query"}
    assert bnf_mod.is_covered("select_query", lark_names, aliases={}) is True
    assert bnf_mod.is_covered("SELECT_QUERY", lark_names, aliases={}) is True


def test_is_covered_via_single_alias(bnf_mod):
    lark_names = {"point_expr"}
    assert (
        bnf_mod.is_covered("point", lark_names, aliases={"point": "point_expr"}) is True
    )


def test_is_covered_via_alias_list_any_match(bnf_mod):
    """When a BNF nonterminal maps to several candidate Lark names, a match
    on any one of them counts as covered."""
    lark_names = {"udf_as_point"}
    aliases = {"point_value": ["point_expr", "centroid_expr", "udf_as_point"]}
    assert bnf_mod.is_covered("point_value", lark_names, aliases) is True


def test_is_covered_handles_space_to_underscore_variant(bnf_mod):
    """Annex A's <unqualified_schema name> (with a literal space) should
    still resolve through an alias keyed with an underscore."""
    lark_names = {"table_name"}
    aliases = {"unqualified_schema_name": "table_name"}
    assert bnf_mod.is_covered("unqualified_schema name", lark_names, aliases) is True


def test_is_covered_returns_false_when_nothing_matches(bnf_mod):
    lark_names = {"something_else"}
    assert bnf_mod.is_covered("totally_unrelated", lark_names, aliases={}) is False


# ---------------------------------------------------------------------------
# Integration: run the real check against the actual project grammar
# ---------------------------------------------------------------------------
def test_real_grammar_has_full_annex_a_coverage(bnf_mod, capsys):
    """End-to-end: running the script's own main() against the project's
    real grammar/*.lark files and the real annex_a_v21.txt must report full
    coverage. This is the same check `uv run python
    scripts/check_bnf_coverage.py` performs manually -- codified as a test
    so a future grammar change that silently drops a construct fails CI
    rather than waiting to be noticed by hand."""
    bnf_mod.main()
    captured = capsys.readouterr()
    assert "All structural Annex A nonterminals are covered." in captured.out
    assert "NO coverage found" not in captured.out


def test_real_grammar_structural_nonterminal_count(bnf_mod):
    """Sanity check on the split itself: Annex A should have a stable,
    non-trivial number of nonterminals in each bucket. Mostly guards against
    a broken extraction regex silently returning an empty/tiny set (which
    would make the coverage check vacuously pass)."""
    bnf_text = bnf_mod.BNF_PATH.read_text(encoding="utf-8")
    bnf_defined = bnf_mod.extract_bnf_definitions(bnf_text)
    punctuation = bnf_mod.find_punctuation_like(bnf_text, bnf_defined)
    structural = bnf_defined - punctuation

    assert len(bnf_defined) > 150  # Annex A defines ~198 nonterminals
    assert len(punctuation) > 10  # a few dozen punctuation/character literals
    assert len(structural) > 100  # the bulk is real structural content


def test_real_grammar_lark_names_nonempty(bnf_mod):
    """Guards against load_lark_defined_names() silently returning nothing
    (e.g. if GRAMMAR_FILES pointed at the wrong directory)."""
    names = bnf_mod.load_lark_defined_names()
    assert len(names) > 100
    assert "select_query" in names
    assert "point_expr" in names
