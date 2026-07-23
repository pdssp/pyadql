# Operations manual

## General

This manual covers the two ways to operate PyADQL: as a Python library
(`import pyadql`) and as the standalone `pyadql` command-line tool. Both
share the same underlying parser and produce the same AST; the CLI is a
thin wrapper around the library's two public entry points, `parse_adql`
and `parse_tree` (see [`reference_manual.md`](reference_manual.md)).

## Set-up and initialisation

No authorisation, account, or credential is required to install or run
PyADQL -- it is a local tool with no network dependency at runtime.

Installation options:

```console
# From a released package (once published)
$ pip install pyadql

# From source, with uv (recommended for development)
$ git clone https://gitlab.cnes.fr/pdssp/common/pyadql.git
$ cd pyadql
$ make prepare-dev && source .venv/bin/activate && make install-dev

# As a container (no local Python needed)
$ docker build -t pdssp/pyadql -f docker/Dockerfile .
$ docker run --rm pdssp/pyadql "SELECT TOP 10 ra, dec FROM t"
```

Installing does not delete or overwrite any existing files, and requires
no further configuration: there is no configuration file to edit and no
parameters to enter before first use.

## Getting started

1. Install PyADQL (see above).
2. Run a first query through the CLI to check the installation:

   ```console
   $ pyadql "SELECT TOP 10 ra, dec FROM t WHERE ra > 10"
   ```

   A successful run prints the parsed AST to `stdout` and exits with code
   `0`; nothing is printed to `stderr` at the default log level.
3. If the command fails, re-run it with `--level DEBUG` to see where the
   failure occurs (grammar compilation, parsing, or AST building) --
   see "Error conditions" below.
4. From Python, the equivalent first step is:

   ```python
   from pyadql import parse_adql
   tree = parse_adql("SELECT TOP 10 ra, dec FROM t WHERE ra > 10")
   ```

For a complete worked example, see [`tutorial.md`](tutorial.md).

## Mode selection and control

PyADQL has no user accounts, passwords, or access-control features -- it
is a local parsing tool with no security perimeter of its own (see
[`external_view.md`](external_view.md#security-and-privacy-considerations)).
The closest equivalent to a "mode" is the **logging verbosity level**,
selected with `--level` on the CLI (default: `ERROR`, i.e. silent on
success):

| Level | Effect |
|---|---|
| `INFO` | + main steps (query source, parsing stage reached) |
| `DEBUG` | + per-step timing (grammar compilation, Lark parsing, AST building) and an AST summary (columns/tables count, presence of `WHERE`/`GROUP BY`/`HAVING`/`ORDER BY`) |
| `TRACE` | + the full raw Lark parse tree |
| `-q`/`--quiet` | errors only, overrides `--level` |

Output routing is fixed and not user-configurable: the parsed result
always goes to `stdout`, logs always go to `stderr`, so the two streams
can be redirected independently (`pyadql "..." 2>/dev/null` to keep only
the result, for instance).

## Normal operations

CLI usage:

```console
# Query passed as an argument
$ pyadql "SELECT TOP 10 ra, dec FROM t WHERE ra > 10"

# From a file
$ pyadql -f query.adql

# From standard input
$ echo "SELECT COUNT(*) FROM t" | pyadql

# JSON output (every node carries a "_type" key)
$ pyadql "SELECT ra FROM t" --json

# Raw Lark parse tree (useful when a query is rejected unexpectedly)
$ pyadql "SELECT ra FROM t" --tree
```

Library usage:

```python
from pyadql import parse_adql

tree = parse_adql("""
    SELECT TOP 10 ra, dec
    FROM mytable
    WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 10, 20, 1)) = 1
    ORDER BY ra
""")
print(type(tree).__name__)   # SelectExpression -- the root node
print(tree.body.where)       # the WHERE clause, as an AST node
```

See [`reference_manual.md`](reference_manual.md) for the full CLI option
reference and [`docs/AST.md`](AST.md) for the full AST shape.

## Normal termination

Both the CLI and the library terminate as soon as parsing (and, for the
CLI, printing the result) completes -- there is no background process or
session to close. Interrupting the CLI with `Ctrl+C` is caught by a
signal handler, which logs an error and exits with code `2`.

## Error conditions

The CLI signals failure through its exit code:

| Exit code | Meaning |
|---|---|
| `0` | Success |
| `1` | ADQL parsing failure (the query is invalid) |
| `2` | Usage error (no query supplied, or the query is empty; also raised on `Ctrl+C`) |

On a parsing failure, the logged error (visible at any `--level`, since
errors are always shown; use `DEBUG`/`TRACE` for more context) explicitly
distinguishes:

- a **grammar** error -- the query text does not match the ADQL grammar
  at all (a genuine syntax error, or a construct not yet supported --
  see "ADQL coverage" in [`reference_manual.md`](reference_manual.md)),
- a **transformer** error -- the grammar matched, but `ADQLTransformer`
  failed to build the corresponding AST node (an internal PyADQL bug,
  worth reporting -- see [`CONTRIBUTING.md`](https://gitlab.cnes.fr/pdssp/common/pyadql/blob/main/CONTRIBUTING.md)).

This distinction is the fastest way to tell "my query is wrong" from
"PyADQL has a bug" when a query is unexpectedly rejected.

When using the library directly, both cases surface as a Python
exception raised by `parse_adql()` / `parse_tree()`; catch it as you
would any other exception.

## Recover runs

PyADQL keeps no state between invocations (see
[`external_view.md`](external_view.md#continuity-of-operation)), so there
is no corrupted state to recover from and no restart procedure beyond
simply re-running the command or re-calling `parse_adql()`. If a query
that used to parse successfully suddenly fails after upgrading PyADQL,
compare the failure against the "ADQL coverage" / "Known limitations"
section of [`reference_manual.md`](reference_manual.md) and, if it looks
like a genuine regression, open an issue (see
[`CONTRIBUTING.md`](https://gitlab.cnes.fr/pdssp/common/pyadql/blob/main/CONTRIBUTING.md)).
