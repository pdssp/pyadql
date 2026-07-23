# External view of the software

## Software files necessary to operate

PyADQL is a self-contained Python library and CLI: it needs no external
database, no network access, and no runtime configuration file to operate.
The files it depends on at runtime all ship inside the installed package
(`src/pyadql/`, installed as the `pyadql` distribution):

| File / directory | Role |
|---|---|
| `pyadql/grammar/adql.lark` | Entry point of the ADQL grammar; assembles the files below via Lark `%import` |
| `pyadql/grammar/lexer.lark` | Terminals: `NAME`, `STRING`, numeric literals, keyword tokens |
| `pyadql/grammar/literals.lark` | Identifiers, literals, `CAST` target types |
| `pyadql/grammar/core.lark` | Query structure, predicates, expressions, functions, geometry |
| `pyadql/parser.py` | Compiles the grammar (lazily, cached) and transforms a Lark parse tree into the typed AST |
| `pyadql/ast_nodes.py` | The AST node dataclasses themselves (no dependency on Lark) |
| `pyadql/__main__.py` | The `pyadql` CLI entry point |
| `pyadql/config.py` | Loguru logging configuration |

The Lark grammar is compiled **in memory** on first use and cached for the
process's lifetime (see `parser._get_lark_parser()`); PyADQL never writes
to disk, and produces no persistent data files, caches, or databases of
its own.

## Security and privacy considerations

- PyADQL performs no network I/O and reads no external files unless
  explicitly asked to (`pyadql -f PATH`, or the query text supplied by the
  caller). It never executes the ADQL query against a database -- it only
  parses it -- so there is no SQL-injection surface *within* PyADQL itself;
  it can in fact be used to help detect suspicious input before it reaches
  a real TAP service (see the production-log validation notes in
  [`reference_manual.md`](reference_manual.md)).
- The only user data PyADQL handles is the ADQL query text passed to it (as
  a CLI argument, a file, or standard input) and the resulting AST, both of
  which stay in memory / on the caller's own stdout; nothing is transmitted
  elsewhere.
- Diagnostic logs (via [loguru](https://github.com/Delgan/loguru)) go to
  `stderr` and, depending on the verbosity level requested (`--level`), may
  include the raw query text (`DEBUG`) -- treat logs at `DEBUG`/`TRACE`
  level as containing the same sensitivity as the queries being parsed.

## Continuity of operation

PyADQL is stateless: every call to `parse_adql()` (or every `pyadql`
invocation) is fully independent, with no session, lock file, or on-disk
state to corrupt or recover. In case of an unexpected interruption (e.g.
`Ctrl+C`, trapped by the CLI's `SigintHandler`), simply re-running the same
command resumes normal operation -- there is no cleanup or recovery
procedure required.
