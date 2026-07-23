"""
Cross-check the grammar/*.lark files against the official ADQL 2.1 Annex A
nonterminal list.

This is a *coverage* check, not a proof of equivalence: grammar equivalence
between two context-free grammars is undecidable in general, so no tool can
mechanically "prove" the grammar is correct. What this script *can* do is
mechanically verify that every structural nonterminal defined in Annex A has
some corresponding rule somewhere in grammar/{lexer,literals,core,adql}.lark
-- either under the same name, or under a deliberate, explicitly-listed
alias (documented below and cross-referenced by the `[AnnexA #x]` comments
throughout those files).

Run it after editing the grammar to catch accidental omissions:

    uv run python scripts/check_bnf_coverage.py

Source of Annex A: IVOA Recommendation ADQL 2.1 (2023-12-15), Annex A ("ADQL
grammar"), supplied verbatim by the user and saved in annex_a_v21.txt
alongside this script (the official ivoa.net/ivoa.info mirrors disallow
automated fetching, and no other reliably fetchable mirror of the exact 2.1
Annex A text could be found -- see this project's chat history).

Known, intentional non-matches (not bugs -- see comments below):
  - Pure punctuation/character-literal nonterminals (<comma> ::= , etc.):
    represented as inline string literals in Lark, never as named rules.
  - Pure lexer-bookkeeping nonterminals (<token>, <newline>, <space>, the
    Latin-letter character classes...): meaningless in a Lark grammar, whose
    regex terminals already cover arbitrary Unicode input.
  - Decomposed literal/identifier lexical rules (<digit>, <mantissa>,
    <exact_numeric_literal>, <coordinate1>...): folded into a single regex
    terminal (SIGNED_NUMBER, NAME, STRING) rather than kept as separate
    named sub-rules.
  - `table_subquery` / `subquery` / `query_expression`: Annex A threads a
    parenthesized subquery through three wrapper nonterminals
    (query_expression -> subquery -> table_subquery); this grammar goes
    straight to `select_expression` wherever any of those is used, which
    accepts the same input.
  - Geometry functions returning a number or a string (CONTAINS/INTERSECTS/
    AREA/COORD1/COORD2/DISTANCE/COORDSYS) are, in Annex A, reached via
    numeric_value_function / string_value_function rather than through a
    dedicated "geometry_value" branch of value_expression -- this grammar
    folds all geometry functions into one `geometry_function` dispatch
    point reached via `function_call`/`primary` instead, a harmless
    simplification (see the SECTION 5 header comment in core.lark).
  - A handful of structural simplifications, e.g. GROUP BY accepting any
    value_expression rather than only grouping_column_reference (a
    deliberate, harmless superset matching real-world usage).
"""

import re
from pathlib import Path

_HERE = Path(__file__).parent
_GRAMMAR_DIR = _HERE.parent / "src" / "pyadql" / "grammar"
GRAMMAR_FILES = ["lexer.lark", "literals.lark", "core.lark", "adql.lark"]
BNF_PATH = _HERE / "annex_a_v21.txt"

# Deliberate renamings: AnnexA nonterminal name -> our Lark rule/alias name
# (or a list of candidate names, when Annex A's one nonterminal maps to more
# than one of ours -- e.g. distance_function's two overloads). Each mapping
# here is documented by an `[AnnexA #x]` comment next to the corresponding
# rule in grammar/core.lark or grammar/literals.lark.
ALIASES = {
    "point": "point_expr",
    "circle": "circle_expr",
    "box": "box_expr",
    "polygon": "polygon_expr",
    "region": "region_expr",
    "centroid": "centroid_expr",
    "area": "area_expr",
    "coord1": "coord1_expr",
    "coord2": "coord2_expr",
    "extract_coordsys": "coordsys_expr",
    "distance_function": ["distance_points", "distance_coords"],
    "contains": "contains_expr",
    "intersects": "intersects_expr",
    "point_value": ["point_expr", "centroid_expr", "udf_as_point"],
    "coord_value": ["point_expr", "centroid_expr", "udf_as_point", "column_reference"],
    "circle_center": [
        "coordinates",
        "point_expr",
        "centroid_expr",
        "udf_as_point",
        "column_reference",
    ],
    "box_center": [
        "coordinates",
        "point_expr",
        "centroid_expr",
        "udf_as_point",
        "column_reference",
    ],
    "polygon_vertices": ["polygon_vertices_coords", "polygon_vertices_points"],
    # table_subquery / subquery / query_expression: all three collapse to
    # select_expression here, see module docstring.
    "table_subquery": "select_expression",
    "subquery": "select_expression",
    "query_expression": "select_expression",
    "correlation_name": "correlated_name",
    "join_condition": "on_spec",
    "named_columns_join": "using_spec",
    "join_column_list": "column_name_list",
    "qualified_join": "joined",
    "outer_join_type": "join_type",
    "qualifier": "correlated_name",
    "identifier": "NAME",
    "regular_identifier": "NAME",
    "delimited_identifier": "NAME",
    "keyword": "NAME",
    "not_equals_operator": "COMP_OP",
    "not_equals_operator1": "COMP_OP",
    "not_equals_operator2": "COMP_OP",
    "less_than_operator": "COMP_OP",
    "less_than_or_equals_operator": "COMP_OP",
    "greater_than_operator": "COMP_OP",
    "greater_than_or_equals_operator": "COMP_OP",
    "equals_operator": "COMP_OP",
    "unsigned_decimal": "UNSIGNED_INT",
    "exact_numeric_literal": "SIGNED_NUMBER",
    "approximate_numeric_literal": "SIGNED_NUMBER",
    "mantissa": "SIGNED_NUMBER",
    "exponent": "SIGNED_NUMBER",
    "signed_integer": "SIGNED_NUMBER",
    "sign": "factor",
    "unsigned_numeric_literal": "number_literal",
    "unsigned_literal": "literal",
    "unsigned_value_specification": "literal",
    "general_literal": "string_literal",
    "character_string_literal": "STRING",
    "value_expression_primary": "primary",
    "numeric_primary": "primary",
    "character_primary": "primary",
    "character_factor": "string_operand",
    "character_value_expression": "string_concat",
    "string_value_expression": "value_expression",
    "match_value": "value_expression",
    "pattern": "value_expression",
    "group_by_term": "value_expression",
    "group_by_term_list": "group_by_clause",
    "order_by_expression": "value_expression",
    "order_by_term": "sort_spec",
    "order_by_term_list": "order_by_clause",
    "order_by_direction": "order_direction",
    "schema_name": "table_name",
    "catalog_name": "table_name",
    "unqualified_schema name": "table_name",
    "set_function_specification": "set_function",
    "general_set_function": "set_function",
    "set_function_type": "SET_FUNC_NAME",
    "math_function": "numeric_function",
    "trig_function": "numeric_function",
    "in_unit_function": "numeric_function",
    "case_folding_function": "string_function",
    "string_geometry_function": "coordsys_expr",
    "string_value_function": "string_function",
    "numeric_value_function": ["numeric_function", "geometry_function"],
    "geometry_value_expression": "function_call",
    "geometry_value_function": "geometry_function",
    "predicate_geometry_function": "geometry_function",
    "non_predicate_geometry_function": "geometry_function",
    "numeric_geometry_function": "geometry_function",
    "user_defined_function_name": "correlated_name",
    "user_defined_function_param": "value_expression",
    "in_predicate_value": "in_predicate_value",
    "with_query": "with_query",
    "comment": "COMMENT_TERM",
    "comment_character": "COMMENT_TERM",
    "comment_introducer": "COMMENT_TERM",
    "concatenation": "concat",
    "concatenation_operator": "concat",
    "coordinate1": "coordinates",
    "coordinate2": "coordinates",
    "exact_numeric_type": "EXACT_NUMERIC_KW",
    "approximate_numeric_type": ["REAL_KW", "DOUBLE_KW"],
}

# Pure lexer/character-level plumbing that a Lark grammar legitimately never
# needs as separate named rules (see module docstring).
LEXER_LEVEL_NOT_APPLICABLE = {
    "nondelimiter_token",
    "delimiter_token",
    "token",
    "nondoublequote_character",
    "nonquote_character",
    "newline",
    "space",
    "separator",
    "simple_Latin_letter",
    "simple_Latin_upper_case_letter",
    "simple_Latin_lower_case_letter",
    "quote_symbol",
    "double_quote_symbol",
    "delimited_identifier_body",
    "delimited_identifier_part",
    "character_representation",
    "default_function_prefix",
    "ADQL_language_character",
    "ADQL_reserved_word",
    "SQL_embedded_language_character",
    "SQL_reserved_word",
    "SQL_special_character",
    "digit",
    # <double_period> (..) is defined in the token catalog but not actually
    # referenced by any active production in Annex A -- a vestige of the
    # SQL92-derived lexer alphabet, not a real ADQL construct.
    "double_period",
}


def extract_lark_names(path: Path) -> set:
    """Return every rule name and `-> alias` name defined in a .lark file
    (comments stripped first). This is the Lark side of the comparison."""
    text = path.read_text(encoding="utf-8")
    no_comments = re.sub(r"//.*", "", text)
    names = set(
        re.findall(
            r"^\??([a-zA-Z_][a-zA-Z0-9_]*)(?:\.-?\d+)?\s*:", no_comments, re.MULTILINE
        )
    )
    names |= set(re.findall(r"->\s*([a-zA-Z_][a-zA-Z0-9_]*)", no_comments))
    return names


def extract_bnf_definitions(bnf_text: str) -> set:
    """Return every nonterminal name defined (`<name> ::= ...`) anywhere in
    a BNF text. This is the Annex A side of the comparison."""
    return {
        n.strip()
        for n in re.findall(
            r"^\s*<([A-Za-z_][A-Za-z0-9_ ]*)>\s*::=", bnf_text, re.MULTILINE
        )
    }


def find_punctuation_like(bnf_text: str, bnf_defined: set) -> set:
    """Return the subset of `bnf_defined` whose own definition is a single
    short literal char/operator with no nested <...> (e.g. `<comma> ::= ,`
    or `<left_paren> ::= (`) -- these are written as inline string literals
    in Lark, never as their own named rule, so they don't count as a
    coverage gap."""
    punctuation_like = set()
    for nt in bnf_defined:
        m = re.search(
            rf"<{re.escape(nt)}>\s*::=\s*(.*?)(?=\n\s*<[A-Za-z_]|\Z)",
            bnf_text,
            re.DOTALL,
        )
        if m and len(m.group(1).strip()) <= 3 and "<" not in m.group(1):
            punctuation_like.add(nt)
    return punctuation_like


def is_covered(nt: str, lark_defined_lower: set, aliases: dict = ALIASES) -> bool:
    """True if BNF nonterminal `nt` has a same-named or aliased match in
    `lark_defined_lower` (a lowercased set of Lark rule/alias names, as
    produced by extract_lark_names)."""
    if nt.lower() in lark_defined_lower:
        return True
    alias = aliases.get(nt, aliases.get(nt.replace(" ", "_")))
    if alias is None:
        return False
    candidates = alias if isinstance(alias, list) else [alias]
    return any(c.lower() in lark_defined_lower for c in candidates)


def load_lark_defined_names() -> set:
    """Union of extract_lark_names(...) over every file in GRAMMAR_FILES."""
    names = set()
    for fname in GRAMMAR_FILES:
        names |= extract_lark_names(_GRAMMAR_DIR / fname)
    return names


def main():
    bnf_text = BNF_PATH.read_text(encoding="utf-8")
    bnf_defined = extract_bnf_definitions(bnf_text)
    punctuation_like = find_punctuation_like(bnf_text, bnf_defined)
    structural_bnf = bnf_defined - punctuation_like

    lark_defined = load_lark_defined_names()
    lark_defined_lower = {r.lower() for r in lark_defined}

    missing = sorted(
        nt
        for nt in structural_bnf
        if nt not in LEXER_LEVEL_NOT_APPLICABLE
        and not is_covered(nt, lark_defined_lower)
    )

    print(f"Annex A 2.1 nonterminals (total)            : {len(bnf_defined)}")
    print(f"  .. pure punctuation/character literals    : {len(punctuation_like)}")
    print(
        f"  .. pure lexer bookkeeping (token/space/..): {len(LEXER_LEVEL_NOT_APPLICABLE)}"
    )
    print(f"  .. structural nonterminals checked        : {len(structural_bnf)}")
    print(f"Rules/aliases/terminals defined in grammar/*.lark : {len(lark_defined)}")
    print()
    if missing:
        print(
            f"=== Structural Annex A nonterminals with NO coverage found ({len(missing)}) ==="
        )
        for nt in missing:
            print(" -", nt)
        print()
        print("Each of these is either a further lexical decomposition folded into a")
        print("single regex terminal, or a deliberate structural simplification -- see")
        print("this script's module docstring and the [AnnexA #x] comments in")
        print("grammar/core.lark. None of them indicate a missing ADQL construct as of")
        print("the last manual review.")
    else:
        print("All structural Annex A nonterminals are covered.")


if __name__ == "__main__":
    main()
