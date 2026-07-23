# Conventions

This document summarizes the symbols, stylistic conventions, and command
syntax conventions used throughout the PyADQL documentation.

## Typographic conventions

- `monospace` denotes code: Python identifiers (`parse_adql`, `ast_nodes.Query`),
  file paths (`src/pyadql/grammar/core.lark`), CLI flags (`--json`), and
  literal text the user types or the program prints.
- ADQL keywords are written in UPPERCASE inside prose (`SELECT`, `WHERE`,
  `CONTAINS`), matching the convention used by the ADQL standard itself,
  even though PyADQL's grammar is case-insensitive on keywords.
- AST node (class) names use `CapitalizedCamelCase` (`SelectExpression`,
  `BinaryOp`, `ColumnRef`), matching the `dataclass` names in
  `src/pyadql/ast_nodes.py`.
- Cross-references to the ADQL 2.1 standard's formal grammar appear as
  `[AnnexA #x]` comments in the grammar files (`src/pyadql/grammar/*.lark`);
  the same tag is used in this documentation when pointing at a specific
  Annex A production.

## Command syntax conventions

- A `$` prefix on a code block line marks a shell prompt; the rest of the
  line is the command to type, e.g.:

  ```console
  $ pyadql "SELECT TOP 10 ra, dec FROM t"
  ```

- Square brackets `[...]` in a command's syntax mark an optional part;
  `<...>` marks a placeholder the user must replace, following the usual
  UNIX man-page convention (e.g. `pyadql [-f PATH] [<query>]`).
- Python code examples are runnable as shown with `uv run python`, unless
  otherwise noted.
- Exit codes are always given as plain integers (`0`, `1`, `2`); see
  [`operation_manual.md`](operation_manual.md#error-conditions) for their
  meaning.
