# PyADQL

[![Maintained](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://gitlab.cnes.fr/pdssp/common/pyadql)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**pyadql** turns an [ADQL](https://www.ivoa.net/documents/ADQL/) query
(*Astronomical Data Query Language*, the IVOA-standardized query language
for querying astronomical catalogs via the TAP protocol) into a **typed
Python abstract syntax tree (AST)**.

ADQL is a superset of SQL92 enriched with geometry functions (`POINT`,
`CIRCLE`, `BOX`, `POLYGON`, `CONTAINS`, `INTERSECTS`, `DISTANCE`, etc.) that
let you express cross-match or sky-region-search queries -- used by Gaia,
SIMBAD, VizieR, and every Virtual Observatory TAP service.

The package is built on a [Lark](https://github.com/lark-parser/lark)
grammar, transcribed directly from **Annex A of IVOA Recommendation
ADQL 2.1** (2023-12-15) -- see `src/pyadql/grammar/core.lark` for detailed,
production-by-production spec cross-references (`[AnnexA #x]` comments) --
and returns an AST made of plain Python dataclasses (`Query`,
`SelectExpression`, `Join`, `BinaryOp`, `Contains`, `Point`, `Circle`, ...)
-- with no dependency on Lark once the tree is built -- which makes it
directly usable to:

- **validate** an ADQL query before sending it to a TAP service,
- **statically analyze** a query (referenced columns/tables, pattern
  detection, etc.),
- **transform or rewrite** a query (e.g. translation to another SQL dialect,
  injecting security constraints, rewriting subqueries),
- **build tooling** (linter, editor, autocompletion) around ADQL.

## Stable release

To install PyADQL, run this command in your
terminal:

``` console
$ pip install git+https://gitlab.cnes.fr/pdssp/common/pyadql.git
```

This is the preferred method to install PyADQL,
as it will always install the most recent stable release.

If you don't have [pip](https://pip.pypa.io) installed, this [Python
installation
guide](http://docs.python-guide.org/en/latest/starting/installation/)
can guide you through the process.

PyADQL requires **Python >= 3.12**.

## Installing UV

To manage the dependencies of PyADQL, we use
[UV](https://docs.astral.sh/uv/). If you don't have UV
installed, follow these steps:

1.  **Install UV**:

    > ``` shell
    > $ curl -LsSf https://astral.sh/uv/install.sh | sh
    > ```

2.  **Verify the installation**:

    > ``` console
    > $ uv --version
    > ```

Please note that this project has been tested with UV version 0.9.15.

## From sources

The sources for PyADQL can be downloaded from
the [Gitlab repo](https://gitlab.cnes.fr/pdssp/common/pyadql).

You can either clone the repository:

``` console
$ git clone https://gitlab.cnes.fr/pdssp/common/pyadql.git
```

Or download an archive of a specific tag/branch directly from Gitlab's
web UI (Code > Download source code).

Once you have a copy of the source, you can install it with:

``` console
$ make  # install
```

## Development

``` console
$ git clone https://gitlab.cnes.fr/pdssp/common/pyadql.git
$ cd pyadql
$ make prepare-dev
$ source .venv/bin/activate
$ make install-dev
```

To get more information about the preconfigured tasks:

``` console
$ make help
```

## Docker

A multi-stage `docker/Dockerfile` (`ENTRYPOINT ["pyadql"]`) is also
available, handy for running the CLI without a local Python environment:

``` console
$ docker build -t pdssp/pyadql -f docker/Dockerfile .
$ docker run --rm pdssp/pyadql "SELECT TOP 10 ra, dec FROM t"
```

## Project structure

```
pyadql/
├── pyproject.toml
├── uv.lock
├── README.md
├── src/pyadql/
│   ├── __init__.py         # public API: parse_adql, parse_tree, ast_nodes
│   ├── __main__.py         # Executable CLI
│   ├── ast_nodes.py         # AST nodes (dataclasses)
│   ├── parser.py            # multi-file grammar loader + Lark tree -> AST transformer
│   ├── _version.py          # Software version
│   ├── config.py            # Loguru configuration
│   └── grammar/             # the ADQL 2.1 grammar itself, split for readability:
│       ├── lexer.lark        #   terminals (NAME, STRING, numbers, keyword tokens)
│       ├── literals.lark     #   identifiers, literals, CAST target types
│       ├── core.lark         #   query structure, predicates, expressions, functions,
│       │                     #   geometry -- kept in one file: genuinely mutually
│       │                     #   recursive through subqueries, see that file's header
│       └── adql.lark         #   entry point: assembles the above, defines `start`
├── examples/
│   └── basic_usage.py
├── scripts/
│   ├── check_bnf_coverage.py  # cross-checks grammar/*.lark against Annex A
│   ├── annex_a_v21.txt         # verbatim copy of ADQL 2.1's Annex A BNF
│   └── license.py              # generates the third-party license table (`make licences`)
├── docker/
│   └── Dockerfile          # multi-stage image, ENTRYPOINT ["pyadql"]
├── docs/                   # MkDocs source (`make doc` / `make visu-doc`)
│   └── AST.md               # guided tour of the AST (diagrams, node reference, examples)
└── tests/                  # pytest suite (137 tests)
    ├── conftest.py
    ├── acceptance/          # behavioral tests, one file per ADQL area
    │   ├── test_select.py
    │   ├── test_joins.py
    │   ├── test_predicates.py
    │   ├── test_geometry.py
    │   ├── test_functions.py
    │   ├── test_clauses_and_subqueries.py
    │   ├── test_integration.py
    │   ├── test_cli.py
    │   ├── test_cli_executable.py
    │   ├── test_docker.py
    │   └── test_real_world_log_patterns.py
    └── unit/
        └── test_check_bnf_coverage.py
```

## Command-line usage (CLI)

`pyadql` installs a command of the same name, handy for quickly testing an
ADQL query without writing any Python code. Logs (via
[loguru](https://github.com/Delgan/loguru)) go to `stderr`, the result goes
to `stdout` -- so the two streams stay cleanly separable.

```bash
# Query passed as an argument
pyadql "SELECT TOP 10 ra, dec FROM t WHERE ra > 10"

# From a file
pyadql -f query.adql

# From standard input
echo "SELECT COUNT(*) FROM t" | pyadql

# JSON output (every node carries a "_type" key)
pyadql "SELECT ra FROM t" --json

# Raw Lark parse tree (useful for debugging the grammar)
pyadql "SELECT ra FROM t" --tree

# More or less verbose logging
pyadql "SELECT ra FROM t"                  # ERROR by default (silent on success)
pyadql "SELECT ra FROM t" --level INFO     # + INFO (main steps)
pyadql "SELECT ra FROM t" --level DEBUG    # + DEBUG (detailed timing, grammar
                                            #   compilation, AST summary)
pyadql "SELECT ra FROM t" --level TRACE    # + TRACE (full Lark parse tree)
pyadql "SELECT ra FROM t" -q               # errors only
```

In `DEBUG` level, each step is timed separately (grammar compilation on
first use, Lark parsing time, AST-building time), and a summary of the
resulting AST is printed (number of columns/tables, presence of
WHERE/GROUP BY/HAVING/ORDER BY). On failure, the log explicitly
distinguishes a **grammar** error (syntactically invalid query) from a
**transformer** error (the grammar matched but building an AST node
failed), which speeds up diagnosis. In `TRACE` level, the full raw
Lark tree is also printed.

Exit codes: `0` success, `1` ADQL parsing failure, `2` usage error (no query
supplied, empty query).

If the package is installed (`uv build` then `pip install dist/*.whl`, or
`uv tool install`), the `pyadql` command is available directly, without
going through `uv run`.

## Usage

```python
from pyadql import parse_adql

ast = parse_adql("""
    SELECT TOP 10 ra, dec
    FROM mytable
    WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 10, 20, 1)) = 1
    ORDER BY ra
""")

print(type(ast).__name__)   # SelectExpression -- the root node
print(ast.order_by)         # [SortItem(...)] -- ORDER BY / OFFSET / WITH live here
print(ast.body.top)         # 10 -- the actual SELECT lives in .body
print(ast.body.from_clause) # [TableRef(name='mytable', ...)]
print(ast.body.where)       # BinaryOp(op='=', left=Contains(...), right=...)
```

`parse_adql()` returns an `ast_nodes.SelectExpression`, matching a real,
deliberate ADQL 2.1 structural change from 2.0: `ORDER BY` / `OFFSET` (and
`WITH`) apply once, to the combined result of any `UNION`/`EXCEPT`/
`INTERSECT`, never to an individual unparenthesized `SELECT` -- so they live
one level up from the actual query body. See the docstring of
`SelectExpression` in `ast_nodes.py` for the full shape, including how
`UNION`/`EXCEPT`/`INTERSECT` (`ast_nodes.SetOperation`) and `WITH` (CTEs,
`ast_nodes.CTE`) fit in.

**For a guided tour of the whole AST** -- simplified class diagrams grouped
by category, a node reference table, a fully worked example, and a
tree-walking recipe -- see [`docs/AST.md`](docs/AST.md).

## Running the tests

```bash
uv run pytest -v

# or, via the preconfigured Makefile target (verbose + live log output):
make tests

# coverage report:
make coverage
```

137 tests, split into two suites:

- `tests/acceptance/` (118 tests) covering: `SELECT` (`TOP`/`DISTINCT`/alias),
  joins (`INNER`/`LEFT`/`RIGHT`/`FULL`, `NATURAL`, `ON`, `USING`), subqueries
  (correlated, scalar, `IN`, `EXISTS`), `WITH` (common table expressions),
  predicates (`BETWEEN`, `IN`, `LIKE`/`ILIKE`, `IS NULL`, comparisons,
  `AND`/`OR`/`NOT` precedence), the full ADQL geometry set (`POINT`/`CIRCLE`/
  `BOX`/`POLYGON`/`REGION`/`CONTAINS`/`INTERSECTS`/`DISTANCE`/`AREA`/
  `CENTROID`/`COORD1`/`COORD2`/`COORDSYS`, including the ADQL 2.1
  `coord_value` forms and `DISTANCE`'s 4-argument overload), aggregate/
  numeric/string functions, `CAST` (with its enumerated 2.1 target types),
  `COALESCE`, `UNION`/`EXCEPT`/`INTERSECT`, realistic integration queries
  (Gaia DR3-style, joins + geometry + `GROUP BY`, CTE-fed crossmatches), the
  CLI -- both by calling `run()` directly (`test_cli.py`) and through the
  real installed executable via `subprocess` (`test_cli_executable.py`) --
  patterns derived from analyzing a real DaCHS/TAP production log
  (`test_real_world_log_patterns.py`, see below), and the `docker/Dockerfile`
  itself (`test_docker.py`: multi-stage build, non-root user, OCI labels).
- `tests/unit/test_check_bnf_coverage.py` (19 tests) covering
  `scripts/check_bnf_coverage.py`'s own logic -- the tool that cross-checks
  `grammar/*.lark` against ADQL 2.1's Annex A (see below).

## Validation against a real production log

The grammar was run against ~2584 unique ADQL queries extracted from a
production log of a TAP service (DaCHS, EPN-TAP): **2533 parsed
successfully**, 51 fail, and break down as:

- `LIMIT` (31 queries): generic SQL syntax never standardized in ADQL (the
  standard uses `TOP`) -- correctly rejected, a standard-compliant TAP
  service rejects it too,
- one SQL injection attempt by a bot (correctly rejected),
- truncated log lines or client queries that are plainly malformed (missing
  commas, unclosed quotes).

This result held steady across a full grammar rewrite (see "A note on
grammar fidelity" below): rebuilding the grammar directly from ADQL 2.1's
official Annex A text changed none of the 2533/2584 outcome, since the 51
failures are all genuinely non-ADQL or malformed input, not gaps the
rewrite could have closed.

## Documentation

The full documentation (Software User Manual, AST guided tour, API
reference) is built with [MkDocs](https://www.mkdocs.org/) and
automatically deployed from the `main` branch to
<https://pdssp.pages.cnes.fr/common/pyadql>.

To build or browse it locally:

``` console
$ make doc        # build the static site (also runs tests/coverage/licenses)
$ make visu-doc    # serve it locally with live-reload (mkdocs serve)
```

## ADQL coverage

What's supported:

- `SELECT` (`DISTINCT`, `TOP n`, `*`, column aliases)
- `WITH` (common table expressions, ADQL 2.1)
- `FROM` with every join type (`INNER`, `LEFT/RIGHT/FULL [OUTER]`,
  `NATURAL`, `ON`, `USING`), derived tables `(SELECT ...) AS alias`
- `WHERE`, `GROUP BY`, `HAVING`
- `ORDER BY [ASC|DESC]`, `OFFSET` (ADQL 2.1) -- applying to the whole
  combined query, per Annex A (see `ast_nodes.SelectExpression`)
- Set operators `UNION` / `EXCEPT` / `INTERSECT` (+ `ALL`)
- Predicates: comparisons, `BETWEEN`, `IN` (list or subquery), `LIKE` and
  `ILIKE` (case-insensitive, ADQL 2.1), `IS [NOT] NULL`, `EXISTS`
- Arithmetic expressions (`+ - * /`), `||` concatenation, `NOT`/`AND`/`OR`
- Scalar and correlated subqueries
- `CAST(expr AS type)` with ADQL 2.1's enumerated target types (`CHAR`/
  `VARCHAR(n)`, `SMALLINT`/`INTEGER`/`BIGINT`/`REAL`/`DOUBLE PRECISION`,
  `TIMESTAMP`, `POINT`/`CIRCLE`/`POLYGON`)
- `COALESCE(a, b, ...)` (ADQL 2.1)
- Aggregate functions: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` (+ `DISTINCT`)
- ADQL numeric functions: `ABS`, `CEILING`, `FLOOR`, `ROUND`, `SQRT`,
  `POWER`, `MOD`, `LOG`, `LOG10`, `EXP`, `PI`, `RAND`, `SIGN`, `TRUNCATE`,
  trigonometric functions (`SIN`, `COS`, `TAN`, `ASIN`, `ACOS`, `ATAN`,
  `ATAN2`, `COT`), `DEGREES`, `RADIANS`, `IN_UNIT` (ADQL 2.1)
- String functions: `LOWER`, `UPPER`
- **ADQL geometry**: `POINT` (optional `coordsys`, ADQL 2.1), `CIRCLE`,
  `BOX`, `POLYGON` (all three accepting either a raw `ra, dec` pair or a
  ready-made point-valued expression as center/vertex, ADQL 2.1), `REGION`,
  `CONTAINS`, `INTERSECTS`, `AREA`, `CENTROID`, `COORD1`, `COORD2`,
  `COORDSYS`, `DISTANCE` (both the two-point and the 2.1-added 4-number
  overload)
- User-defined functions (any unrecognized `name(...)` call is captured as
  `UserFunctionCall`, to cover TAP-service-specific extensions)
- Double-quoted identifiers (`"My Column"`, with `""`-escaped literal
  quotes), `--` comments

Known limitations (feel free to extend, see `grammar/core.lark`):

- `TIMESTAMP`/`INTERVAL` *literals* (as opposed to `CAST(... AS TIMESTAMP)`,
  which is supported) are not yet in the grammar; Annex A itself barely
  defines them.
- No specific handling of `TAP_UPLOAD` (a TAP-protocol detail, outside the
  ADQL grammar proper).
- Earley's ambiguity resolution (`ambiguity='resolve'`) picks the "most
  likely" derivation; for very unusual queries, double-check the resulting
  AST. One concrete case: `POINT(a, b, c)` where none of `a`/`b`/`c` fit
  `POINT`'s expected shape (e.g. `a` isn't a string literal coordsys) falls
  back to a generic `UserFunctionCall` named `"POINT"` rather than being
  rejected outright -- a harmless permissive superset, but worth knowing
  about if you're validating strict spec compliance rather than just
  parsing. For example:

  ``` python
  # Regular query: POINT('ICRS', ra, dec)
  Point(coordsys=StringLiteral(value='ICRS'), ra=ColumnRef(['ra']), dec=ColumnRef(['dec']))

  # Query with cs_col (a column, not a string): POINT(cs_col, ra, dec)
  UserFunctionCall(name='POINT', args=[ColumnRef(['cs_col']), ColumnRef(['ra']), ColumnRef(['dec'])])
  ```

To cover a missing case: add the rule in the relevant `src/pyadql/grammar/*.lark`
file (following Annex A, see the `[AnnexA #x]` cross-references already
there), then add the matching method in `ADQLTransformer`
(`src/pyadql/parser.py`) that builds the AST node (`src/pyadql/ast_nodes.py`).

## Author

👤 **Jean-Christophe Malapert** ([jean-christophe.malapert@cnes.fr](mailto:jean-christophe.malapert@cnes.fr))

## 🤝 Contributing

Contributions, issues and feature requests are welcome! Feel free
to check the [issues page](https://gitlab.cnes.fr/pdssp/common/pyadql/issues). You can
also take a look at the [contributing guide](CONTRIBUTING.md).

## 📝 License

This project is [Apache 2.0](LICENSE) licensed.
