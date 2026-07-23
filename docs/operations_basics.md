# Operations basics

## Operational tasks

PyADQL supports a single operational task, available in two forms:
**parsing an ADQL query into an AST**.

- **Library form**: call `pyadql.parse_adql(query)` from Python code and
  work with the returned `SelectExpression` object (see
  [`tutorial.md`](tutorial.md) and [`docs/AST.md`](AST.md)).
- **CLI form**: run `pyadql <query>` (or `-f <file>`, or pipe through
  stdin) from a shell; the result is printed to `stdout` as a Python
  `repr`, JSON (`--json`), or a raw Lark parse tree (`--tree`), while
  diagnostic logs go to `stderr` (see [`operation_manual.md`](operation_manual.md)
  and [`reference_manual.md`](reference_manual.md)).

There is no sequence or hierarchy between operations: each call/invocation
is independent and stateless (see [`external_view.md`](external_view.md#continuity-of-operation)).

## Roles and staffing

No dedicated operational staff or administrator role is needed. Two
informal roles interact with PyADQL:

- **Integrator / developer**: adds PyADQL as a dependency of their own
  application and calls `parse_adql()` programmatically.
- **End user**: runs the `pyadql` CLI directly, e.g. to check whether a
  query is valid before pasting it into a TAP client.

## Standard and contingency operations

There are no "daily operations" in the operational sense (no service to
start, monitor, or shut down): PyADQL is invoked on demand, once per
query. The only "contingency" scenario is a parsing failure, handled
uniformly:

- as a Python exception when used as a library,
- as a non-zero exit code (`1` for an ADQL parsing failure, `2` for a
  usage error) plus a logged error message when used as a CLI.

See [`operation_manual.md`](operation_manual.md#error-conditions) for the
full detail on diagnosing a failure.
