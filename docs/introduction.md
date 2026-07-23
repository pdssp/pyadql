# Introduction

::: pyadql

## Purpose

This manual serves as a comprehensive resource for:

- Installation and Setup: Guiding you through the installation process and initial configuration.
- Features and Functionality: Explaining the core features and how to use them.
- Best Practices: Offering recommendations for optimal performance and usage.
- Troubleshooting: Providing solutions to common issues and frequently asked questions.

## Context

[ADQL](https://www.ivoa.net/documents/ADQL/) (*Astronomical Data Query
Language*) is the query language standardized by the
[IVOA](https://www.ivoa.net/) (International Virtual Observatory Alliance)
for querying astronomical catalogs through the
[TAP](https://www.ivoa.net/documents/TAP/) (*Table Access Protocol*)
protocol. It is a superset of SQL92 enriched with geometry functions
(`POINT`, `CIRCLE`, `BOX`, `POLYGON`, `CONTAINS`, `INTERSECTS`, `DISTANCE`,
...) used to express cross-match or sky-region-search queries. It is the
query language spoken by Virtual Observatory data centers such as Gaia,
SIMBAD, VizieR, and every other TAP-compliant service.

**PyADQL** parses an ADQL query into a **typed Python abstract syntax tree
(AST)**: plain Python dataclasses (`Query`, `SelectExpression`, `Join`,
`BinaryOp`, `Contains`, `Point`, `Circle`, ...) with no dependency on the
parsing engine once the tree is built. This makes PyADQL directly usable to:

- **validate** an ADQL query before sending it to a TAP service,
- **statically analyze** a query (referenced columns/tables, pattern
  detection, etc.),
- **transform or rewrite** a query (translation to another SQL dialect,
  injecting security constraints, rewriting subqueries),
- **build tooling** (linter, editor, autocompletion) around ADQL.

The grammar itself is built with [Lark](https://github.com/lark-parser/lark)
and transcribed directly from Annex A of IVOA Recommendation ADQL 2.1
(2023-12-15), so that every production in the code can be traced back to the
standard it implements (see the reference manual and
[`docs/AST.md`](AST.md) for details).

This manual is intended for two audiences: developers embedding PyADQL as a
library in a larger Python application (a TAP service, a query linter, an
IDE plugin, ...), and users running the `pyadql` command-line tool to
inspect or validate a query interactively.
