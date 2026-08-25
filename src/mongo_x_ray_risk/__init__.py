"""Risk Register — ChromaDB-backed vector search for known risks.

The public API is re-exported here; consumers should import from this package
rather than from the ``db``/``shared`` submodules, which are implementation
details. The enrichment functions operate on plain values (a ``list[dict]`` of
test results, a ``str`` category), so they never depend on any analysis
module's item types.
"""

from mongo_x_ray_risk.db import (
    clear_risks,
    enrich_test_results,
    find_risks_by_name,
    has_risks,
    ingest_risks,
    match_risk,
    search_risks,
)
from mongo_x_ray_risk.shared import Risk, load_risks_from_csv

__all__ = [
    "Risk",
    "load_risks_from_csv",
    "ingest_risks",
    "search_risks",
    "find_risks_by_name",
    "clear_risks",
    "match_risk",
    "enrich_test_results",
    "has_risks",
]
