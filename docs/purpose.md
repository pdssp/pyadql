# Purpose of the Software

PyADQL turns an [ADQL](https://www.ivoa.net/documents/ADQL/) query into a
typed, inspectable Python abstract syntax tree. Its intended uses are:

- **Query validation** -- check that an ADQL query is syntactically valid
  *before* sending it to a TAP service, giving fast, local, actionable
  feedback (with a clear distinction between a grammar error and an
  internal transformer error) instead of round-tripping to a remote server.
- **Static analysis** -- inspect a query's structure without executing it:
  which tables and columns it references, which geometry functions it
  uses, whether it contains subqueries or set operations, etc.
- **Query transformation and rewriting** -- since the AST is a plain,
  serializable, dependency-free data structure, it can be walked and
  rewritten programmatically: translating to another SQL dialect,
  injecting row-level security constraints, or normalizing subqueries.
- **Tooling** -- serve as the parsing layer for editor plugins, linters,
  autocompletion engines, or any other developer tool that needs to
  understand ADQL rather than treat it as an opaque string.

Expected benefits over ad hoc string handling or regular expressions:

- **Correctness** -- the grammar is transcribed directly from Annex A of
  the IVOA ADQL 2.1 Recommendation, with per-production cross-references,
  and cross-checked against thousands of real production queries (see
  [`reference_manual.md`](reference_manual.md)).
- **A stable, dependency-free data model** -- `ast_nodes` has no dependency
  on the underlying parsing engine ([Lark](https://github.com/lark-parser/lark)),
  so consumers of the AST are insulated from parser internals.
- **Two entry points for two contexts** -- a Python API (`parse_adql`) for
  embedding in applications, and a standalone `pyadql` CLI for interactive
  or scripted use, both documented in [`operation_manual.md`](operation_manual.md).
