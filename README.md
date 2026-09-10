# mongo-x-ray-risk

[![CI](https://github.com/zhangyaoxing/mongo-x-ray-risk/actions/workflows/ci.yml/badge.svg)](https://github.com/zhangyaoxing/mongo-x-ray-risk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mongo-x-ray-risk.svg)](https://pypi.org/project/mongo-x-ray-risk/)

Known-risks knowledge base for [x-ray](https://github.com/mongodb-ps/ce-mongo-x-ray): a ChromaDB-backed
vector search that matches analysis findings against known MongoDB risks.

This is an optional plugin: it ships the `ingest` command to load the risk register, the `search`
command to look risks up by name, and the analysis plugins (healthcheck, log, gmd) detect it at
runtime — when it is installed, their reports are enriched with matched risks; when it is missing,
the enrichment is silently skipped.

## Install

```bash
pip install mongo-x-ray mongo-x-ray-risk
```

## Usage

Load a risk register CSV into the ChromaDB knowledge base:

```bash
x-ray ingest risk_register.csv
# start from an empty register, then ingest
x-ray ingest --clear risk_register.csv
# clear the register without ingesting (no CSV needed)
x-ray ingest --clear
```

Check whether a risk is already known by searching the `Name` column
(case-insensitive substring match). Prints the `Name` and `Risk description`
of every matching risk; exits 0 when something matches, 1 when nothing does:

```bash
x-ray search "Replication Lag"
x-ray search replication
```

The CSV must have the columns `ID, Risk level, Impact, Name, Risk description`
(UTF-8, a BOM is tolerated; header names are matched case-insensitively). Any
other columns, such as `Other Notes`, are ignored. Rows without an ID or a
Name are skipped; entries with an existing ID are replaced. The data is
stored under `~/.x-ray/chroma`.

Once ingested, the plugin is used automatically by the other plugins — no CLI
flags needed. It also exposes a small API for tooling:

```python
from mongo_x_ray_risk import Risk, load_risks_from_csv, ingest_risks, match_risk, enrich_test_results
```

## Security notes

Dependabot reports open advisories against the pinned `chromadb` version
(2 critical, 2 high as of 1.5.9). They all affect the **Chroma HTTP server API**
only:

- CVE-2026-45829 / CVE-2026-45833 — code injection: an attacker posts a
  malicious model repository with `trust_remote_code` set to true to the
  `/api/v2/.../collections` endpoints of a running Chroma server.
- CVE-2026-45830 / CVE-2026-45831 — a Chroma server lets authenticated users
  read, write or delete data across tenants, databases and collections.

This plugin never runs or connects to a Chroma server. It uses ChromaDB's
in-process embedded client on a local path:

```python
chromadb.PersistentClient(path=~/.x-ray/chroma, settings=Settings(anonymized_telemetry=False))
```

It embeds with the default local embedding function (no remote model is
downloaded) and accepts no remote Chroma endpoint, so neither the server API
nor its authentication layer is reachable. The advisories were therefore
dismissed on GitHub as "vulnerable code is not actually used". `chromadb==1.5.9`
is also the newest release and no advisory lists a patched version yet, so this
cannot be fixed by upgrading; the pin is revisited when a patched release
appears.

## Development

Requires Python 3.10+, MongoDB 5.0 or later, and the [mongo-x-ray](https://github.com/mongodb-ps/ce-mongo-x-ray) core package.

```bash
make unit-test   # run the unit tests
make lint        # ruff check + ruff format --check
```
