"""
Copyright (c) 2026 MongoDB Inc.

DISCLAIMER: THESE CODE SAMPLES ARE PROVIDED FOR EDUCATIONAL AND ILLUSTRATIVE PURPOSES ONLY,
TO DEMONSTRATE THE FUNCTIONALITY OF SPECIFIC MONGODB FEATURES.
THEY ARE NOT PRODUCTION-READY AND MAY LACK THE SECURITY HARDENING, ERROR HANDLING, AND TESTING REQUIRED FOR A LIVE ENVIRONMENT.
YOU ARE RESPONSIBLE FOR TESTING, VALIDATING, AND SECURING THIS CODE WITHIN YOUR OWN ENVIRONMENT BEFORE IMPLEMENTATION.
THIS MATERIAL IS PROVIDED "AS IS" WITHOUT WARRANTY OR LIABILITY.

Tests for the in-memory search cache keyed by the search term.
"""

from mongo_x_ray_risk import db
from mongo_x_ray_risk.shared import CHROMA_COLLECTION_DESCRIPTION, Risk


class _FakeCollection:
    """Minimal in-memory Chroma collection that counts query() calls."""

    def __init__(self):
        self._docs: dict[str, dict] = {}
        self.query_calls = 0

    def upsert(self, ids=None, documents=None, metadatas=None):
        for doc_id, meta in zip(ids or [], metadatas or []):
            self._docs[doc_id] = dict(meta)

    def query(self, query_texts=None, n_results=3):
        self.query_calls += 1
        ids = list(self._docs)[:n_results]
        return {
            "ids": [ids],
            "metadatas": [[self._docs[i] for i in ids]],
            "distances": [[0.1] * len(ids)],
        }

    def get(self, include=None):
        return {"ids": list(self._docs), "metadatas": [self._docs[i] for i in self._docs]}

    def delete(self, ids=None):
        for doc_id in ids or []:
            self._docs.pop(doc_id, None)


def _install_fake_collection(monkeypatch):
    fake = _FakeCollection()
    monkeypatch.setattr(db, "_collection", lambda name: fake)
    return fake


def test_repeated_search_of_same_term_queries_chromadb_once(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    fake.upsert(
        ids=["R1"],
        documents=["Replication Lag"],
        metadatas=[
            {
                "id": "R1",
                "risk_level": "High",
                "impact": "Medium",
                "name": "Replication Lag",
                "description": "oplog falls behind",
            }
        ],
    )

    first = db.search_risks("Replication Lag")
    second = db.search_risks("Replication Lag")

    assert first == second
    assert fake.query_calls == 1  # second call served from the cache


def test_different_terms_are_cached_separately(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    fake.upsert(
        ids=["R1", "R2"],
        documents=["Replication Lag", "Missing Index"],
        metadatas=[
            {"id": "R1", "risk_level": "High", "impact": "Medium", "name": "Replication Lag", "description": "a"},
            {"id": "R2", "risk_level": "Medium", "impact": "Low", "name": "Missing Index", "description": "b"},
        ],
    )

    db.search_risks("Replication Lag")
    db.search_risks("Replication Lag")
    db.search_risks("Missing Index")
    db.search_risks("Missing Index")

    assert fake.query_calls == 2


def test_cache_key_includes_n_results_and_collection(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    fake.upsert(
        ids=["R1", "R2"],
        documents=["Replication Lag", "Missing Index"],
        metadatas=[
            {"id": "R1", "risk_level": "High", "impact": "Medium", "name": "Replication Lag", "description": "a"},
            {"id": "R2", "risk_level": "Medium", "impact": "Low", "name": "Missing Index", "description": "b"},
        ],
    )

    db.search_risks("Replication Lag", n_results=1)
    db.search_risks("Replication Lag", n_results=1)  # cache hit
    db.search_risks("Replication Lag", n_results=5)  # different key -> new query
    db.search_risks("Replication Lag", n_results=5)  # cache hit
    db.search_risks("Replication Lag", n_results=1, collection_name=CHROMA_COLLECTION_DESCRIPTION)

    assert fake.query_calls == 3


def test_cached_entries_are_returned_as_copies(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    fake.upsert(
        ids=["R1"],
        documents=["Replication Lag"],
        metadatas=[
            {
                "id": "R1",
                "risk_level": "High",
                "impact": "Medium",
                "name": "Replication Lag",
                "description": "oplog falls behind",
            }
        ],
    )

    first = db.search_risks("Replication Lag")
    first[0]["name"] = "Mutated"

    second = db.search_risks("Replication Lag")
    assert second[0]["name"] == "Replication Lag"  # cache unaffected by mutation


def test_ingest_risks_invalidates_cache(monkeypatch):
    fake = _install_fake_collection(monkeypatch)

    db.search_risks("Replication Lag")
    assert fake.query_calls == 1

    risk = Risk(
        id="R1",
        risk_level="High",
        impact="Medium",
        name="Replication Lag",
        description="oplog falls behind",
    )
    db.ingest_risks([risk])
    assert fake.query_calls == 1  # ingest itself doesn't query

    db.search_risks("Replication Lag")
    assert fake.query_calls == 2  # cache was invalidated by ingest


def test_clear_risks_invalidates_cache(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    fake.upsert(
        ids=["R1"],
        documents=["Replication Lag"],
        metadatas=[
            {
                "id": "R1",
                "risk_level": "High",
                "impact": "Medium",
                "name": "Replication Lag",
                "description": "oplog falls behind",
            }
        ],
    )

    db.search_risks("Replication Lag")
    assert fake.query_calls == 1

    db.clear_risks()
    db.search_risks("Replication Lag")

    assert fake.query_calls == 2  # cache was invalidated by clear
