"""Shared pytest fixtures for the mongo-x-ray-risk test suite."""

import pytest

from mongo_x_ray_risk import db


@pytest.fixture(autouse=True)
def _clear_search_cache():
    """Clear the module-level search cache around every test.

    ``db.search_risks`` caches results keyed by the search term; without a
    reset the cached entries from one test could leak into the next.
    """
    db._search_cache.clear()
    yield
    db._search_cache.clear()
