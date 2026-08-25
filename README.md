# mongo-x-ray-risk-register

[![CI](https://github.com/zhangyaoxing/mongo-x-ray-risk-register/actions/workflows/ci.yml/badge.svg)](https://github.com/zhangyaoxing/mongo-x-ray-risk-register/actions/workflows/ci.yml)

Known-risks knowledge base for [x-ray](https://github.com/mongodb-ps/ce-mongo-x-ray): a ChromaDB-backed
vector search that matches analysis findings against known MongoDB risks.

This is an optional library plugin (it registers no CLI command). The analysis plugins
(healthcheck, log, gmd) detect it at runtime: when it is installed, their reports are
enriched with matched risks; when it is missing, the enrichment is silently skipped.

## Install

```bash
pip install mongo-x-ray mongo-x-ray-risk-register
```

## Usage

The plugin is used automatically by the other plugins once installed — no CLI flags needed.
It exposes a small API for tooling:

```python
from mongo_x_ray_risk_register import Risk, ingest_risks, match_risk, enrich_test_results
```

## Development

Requires Python 3.10+, MongoDB 5.0 or later, and the [mongo-x-ray](https://github.com/mongodb-ps/ce-mongo-x-ray) core package.

```bash
make unit-test   # run the unit tests
make lint        # ruff check + ruff format --check
```
