# mongo-x-ray-risk — Release Notes

Known-risks knowledge base for x-ray: a ChromaDB-backed vector search that matches analysis findings against known MongoDB risks, with CLI commands to manage the register.

## v2.1.0

### Added
- **Vector search result cache**: search results are cached per search term, so repeated matches (the same alert category matched for many findings) no longer re-run the embedding query — reports with many findings get noticeably faster risk enrichment.

### Inherited from core (applies to every plugin report)
- Report copy icons for inline code, code blocks and table `<pre>` blocks; output report folders are prefixed with the plugin name. Risk enrichment output (the tooltips) is unchanged: the risk `Name` is the tooltip title and the `Risk description` the body.

### Security
- The `chromadb==1.5.9` pin is flagged by four advisories (2 critical, 2 high), but all of them need the Chroma **HTTP server** API (`trust_remote_code` collection endpoint, server-side RBAC and authentication) that this plugin never starts or connects to: it uses the embedded in-process `PersistentClient` on a local path with the default local embedding function. The advisories were dismissed on GitHub as "vulnerable code is not actually used", and 1.5.9 is the newest release with no patched version yet. See the README "Security notes" section.

### Development
- **CI now runs on pull requests** as well as on pushes to `main`, so a dependency bump is linted and tested before it can land.
- **Dependabot** is enabled for `pip` and GitHub Actions (weekly). Patch and minor updates merge automatically once every check is green, as do major updates of the CI actions and the build/lint/test tooling; a major update of a runtime dependency (`mongo-x-ray`, `chromadb`) is left for review, and a failing or missing check leaves the pull request open instead of merging.
- **Tooling bumped**: `setuptools` 83.0.0 → 84.0.0, `actions/checkout` v4 → v7, `actions/setup-python` v5 → v7.

## v2.0.0

Extracted into a standalone `mongo-x-ray-risk` package (ChromaDB moved out of the core). It provides `x-ray ingest <csv>` (columns `ID, Risk level, Impact, Name, Risk description`, case-insensitive headers, other columns ignored), `x-ray ingest --clear` (clear without a CSV), `x-ray search <string>` (substring search over risk names, exit code 0/1 so callers can tell "already known" from "new"), and the `has_risks()` / `match_risk()` / `enrich_test_results()` API used by the analysis plugins. Missing ChromaDB yields a clear error instead of a traceback; analysis plugins silently skip enrichment when the plugin is absent.
