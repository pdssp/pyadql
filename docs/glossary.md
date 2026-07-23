# Terms, definitions and abbreviated terms

| Term      | Description |
|-----------|-------------|
| SUM       | Software User Manual |
| COTS      | Commercial Off-The-Shelf |
| ADQL      | Astronomical Data Query Language, the IVOA-standardized query language implemented by this package |
| AST       | Abstract Syntax Tree, the typed Python object tree returned by `parse_adql()` |
| IVOA      | International Virtual Observatory Alliance, the body that standardizes ADQL and TAP |
| TAP       | Table Access Protocol, the IVOA protocol used to send ADQL queries to astronomical data centers |
| Annex A   | The formal BNF grammar of ADQL 2.1, published as an annex to the IVOA Recommendation; PyADQL's grammar is transcribed directly from it |
| BNF       | Backus-Naur Form, the notation used by Annex A to define ADQL's grammar |
| CTE       | Common Table Expression, a `WITH name AS (...)` clause (ADQL 2.1) |
| UDF       | User-Defined Function; any `name(...)` call not recognized as a built-in ADQL function is parsed as `UserFunctionCall` |
| STC-S     | Space-Time Coordinate metadata in string form, as accepted by ADQL's `REGION(...)` |
| ICRS      | International Celestial Reference System, a common astronomical coordinate system used as an example `coordsys` value in this manual |
| Lark      | The Python parsing library ([lark-parser](https://github.com/lark-parser/lark)) used to compile PyADQL's grammar |
| Earley    | The parsing algorithm (Lark's `earley` engine) used to parse ADQL, chosen for its ability to handle ambiguous context-free grammars |
| DaCHS     | Data Center Helper Suite, a TAP-service implementation; production DaCHS/EPN-TAP logs were used to validate PyADQL's grammar coverage (see [`reference_manual.md`](reference_manual.md)) |
| Loguru    | The Python logging library used for PyADQL's structured logs (`stderr`) |
| CLI       | Command-Line Interface; PyADQL installs a `pyadql` command, see [`operation_manual.md`](operation_manual.md) |
| uv        | The Python packaging/dependency manager ([astral-sh/uv](https://docs.astral.sh/uv/)) used to build and develop PyADQL |
