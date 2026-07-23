# Operations environment

## General

PyADQL is a pure-Python library and command-line tool; it needs nothing
beyond a standard Python interpreter and its two runtime dependencies (see
below) to run. There is no server component, no database, and no
network requirement.

## Hardware configuration

No specific hardware is required. PyADQL runs on any machine capable of
running CPython 3.12+ (a laptop, a CI runner, a container). There are no
particular memory or storage requirements: the Lark grammar is compiled
in memory (a few hundred kilobytes) and released when the process exits;
disk usage is limited to the installed package itself (a few hundred
kilobytes) and, optionally, the built Docker image.

## Software configuration

- **Interpreter**: Python >= 3.12 (`requires-python` in `pyproject.toml`).
- **Runtime dependencies** (installed automatically):
  - [`lark`](https://github.com/lark-parser/lark) (`>1.3,<2.0`) -- the
    parsing engine that compiles and runs the ADQL grammar.
  - [`loguru`](https://github.com/Delgan/loguru) (`>=0.7.3`) -- structured
    logging for the library and CLI.
- **Package/dependency manager**: [uv](https://docs.astral.sh/uv/), used
  for development, building (`uv build`), and running (`uv run`); PyADQL
  can equally be installed with plain `pip` once built.
- **Optional container runtime**: Docker, to run PyADQL from the image
  built by `docker/Dockerfile` (`ENTRYPOINT ["pyadql"]`), useful for
  running the CLI without a local Python environment.
- **Documentation toolchain** (development only): [MkDocs](https://www.mkdocs.org/)
  with the Material theme and `mkdocstrings`, used to build this manual
  (`make doc`, `make visu-doc`).

## Operational constraints

PyADQL can be used in two modes, which can be freely mixed within the same
environment:

- **As a library** (`from pyadql import parse_adql`), embedded in a larger
  Python application -- e.g. a TAP service validating incoming queries, or
  an editor plugin.
- **As a standalone CLI** (`pyadql ...`), for interactive or scripted use
  from a terminal or a shell pipeline.

There are no degraded or emergency modes: a failure always surfaces as an
ordinary Python exception (library use) or a non-zero exit code with a
logged error (CLI use, see [`operation_manual.md`](operation_manual.md#error-conditions));
there is no state that can be left inconsistent, since PyADQL holds no
persistent state between calls.
