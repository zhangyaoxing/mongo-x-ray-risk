# mongo-x-ray-risk — Release Notes

Known-risks knowledge base for x-ray: a ChromaDB-backed vector search that matches analysis findings against known MongoDB risks, with CLI commands to manage the register.

## v2.0.0 (2026-08-25 — 2026-08-31)

### New Features
- **Standalone risk-register plugin**: extracted the ChromaDB-backed known-risks knowledge base into its own `mongo-x-ray-risk` package (renamed from the initial plugin name). Analysis plugins (healthcheck, log, gmd) detect it at runtime and silently skip risk enrichment when it is not installed.
- **`x-ray ingest <csv>` command**: loads a risk register CSV into the ChromaDB knowledge base.
- **CSV format**: uses `ID, Risk level, Impact, Name, Risk description` columns (case-insensitive header matching); other columns are ignored.
- **`x-ray ingest --clear`**: clears the register without requiring a CSV.
- **`has_risks()` helper**: public API to detect a populated risk register without raising on a missing/corrupt database.
- **`x-ray search <string>` command**: case-insensitive substring search of the risk `Name` column; prints the `Name` and `Risk description` of each match, exiting 0 when found and 1 when not (lets callers distinguish an already-known risk from a new one). Backed by a new `find_risks_by_name()` in the db layer.
- **Friendly error handling**: clear error message when ChromaDB is missing; fixed typing on `find_risks_by_name`.

### CI & Tooling
- **PyPI publishing**: release workflow publishing to (Test)PyPI via trusted publishing.
- **CodeQL**: static analysis enabled; fixed the reported issues (unnecessary lambda, uninitialized browser fixture variable).
- **Deterministic import sorting**: explicit known-first-party configuration for `mongo_x_ray*` imports (isort).
- **Copyright headers**: unified to 2026.

### Documentation
- README now includes a PyPI badge and usage docs for all commands.
