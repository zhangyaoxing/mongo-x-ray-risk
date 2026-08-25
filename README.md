# mongo-x-ray-risk

[![CI](https://github.com/zhangyaoxing/mongo-x-ray-risk/actions/workflows/ci.yml/badge.svg)](https://github.com/zhangyaoxing/mongo-x-ray-risk/actions/workflows/ci.yml)

Known-risks knowledge base for [x-ray](https://github.com/mongodb-ps/ce-mongo-x-ray): a ChromaDB-backed
vector search that matches analysis findings against known MongoDB risks.

This is an optional plugin: it ships the `ingest` command to load the risk register, and the
analysis plugins (healthcheck, log, gmd) detect it at runtime — when it is installed, their
reports are enriched with matched risks; when it is missing, the enrichment is silently skipped.

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
```

The CSV must have the columns `ID, Risk Level, Impact, Name, Risk Description`
(UTF-8, a BOM is tolerated). Rows without an ID or a Name are skipped; entries
with an existing ID are replaced. The data is stored under `~/.x-ray/chroma`.

Once ingested, the plugin is used automatically by the other plugins — no CLI
flags needed. It also exposes a small API for tooling:

```python
from mongo_x_ray_risk import Risk, load_risks_from_csv, ingest_risks, match_risk, enrich_test_results
```

## Development

Requires Python 3.10+, MongoDB 5.0 or later, and the [mongo-x-ray](https://github.com/mongodb-ps/ce-mongo-x-ray) core package.

```bash
make unit-test   # run the unit tests
make lint        # ruff check + ruff format --check
```
