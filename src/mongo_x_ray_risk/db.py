"""
Copyright (c) 2026 MongoDB Inc.

DISCLAIMER: THESE CODE SAMPLES ARE PROVIDED FOR EDUCATIONAL AND ILLUSTRATIVE PURPOSES ONLY,
TO DEMONSTRATE THE FUNCTIONALITY OF SPECIFIC MONGODB FEATURES.
THEY ARE NOT PRODUCTION-READY AND MAY LACK THE SECURITY HARDENING, ERROR HANDLING, AND TESTING REQUIRED FOR A LIVE ENVIRONMENT.
YOU ARE RESPONSIBLE FOR TESTING, VALIDATING, AND SECURING THIS CODE WITHIN YOUR OWN ENVIRONMENT BEFORE IMPLEMENTATION.
THIS MATERIAL IS PROVIDED "AS IS" WITHOUT WARRANTY OR LIABILITY.

ChromaDB-backed risk register with vector search.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any, Mapping, Optional

from mongo_x_ray_risk.shared import (
    CHROMA_COLLECTION,
    CHROMA_COLLECTION_DESCRIPTION,
    Risk,
    get_db_path,
)

# Mute chromadb telemetry errors (posthog API mismatch)
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

_logger = logging.getLogger(__name__)

# In-process cache of vector-search results, keyed by search term so repeated
# lookups of the same alert title don't re-embed / re-query ChromaDB. Kept
# small (bounded LRU) and invalidated whenever the register is mutated.
_SEARCH_CACHE_SIZE = 512
_search_cache: OrderedDict[tuple[str, int, str], tuple[dict, ...]] = OrderedDict()


def _cache_search(key: tuple[str, int, str], entries: list[dict]) -> None:
    """Store *entries* under *key*, evicting the least-recently-used entry."""
    _search_cache[key] = tuple(entries)
    _search_cache.move_to_end(key)
    while len(_search_cache) > _SEARCH_CACHE_SIZE:
        _search_cache.popitem(last=False)


def _collection(collection_name: str = CHROMA_COLLECTION):
    """Return an initialized ChromaDB collection (lazy singleton)."""
    # Import chromadb lazily so importing this module stays cheap and the risk
    # register remains an optional best-effort enrichment. ChromaDB is not
    # bundled into the frozen x-ray binary, so a missing import surfaces as a
    # clear error instead of a raw traceback.
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as exc:
        raise RuntimeError(
            "ChromaDB is not available in this build. Install the "
            "'mongo-x-ray-risk' pip package (which depends on chromadb) "
            "to use the risk register."
        ) from exc

    db_path = get_db_path() / "chroma"
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(collection_name)


def ingest_risks(risks: list[Risk]) -> int:
    """Upsert risks into ChromaDB, returning the number of documents ingested.

    Each risk is embedded twice — once for the ``Name`` field and once for the
    ``Risk Description`` field — stored in two separate collections so that
    matching can fall back from Name to Risk Description. Risks without a Risk
    Description are only embedded in the Name collection. Existing documents
    with the same ID are replaced (upsert).
    """
    if not risks:
        return 0

    name_col = _collection(CHROMA_COLLECTION)
    desc_col = _collection(CHROMA_COLLECTION_DESCRIPTION)

    name_ids: list[str] = []
    name_documents: list[str] = []
    name_metadatas: list[Mapping[str, Any]] = []
    desc_ids: list[str] = []
    desc_documents: list[str] = []
    desc_metadatas: list[Mapping[str, Any]] = []

    for risk in risks:
        metadata = {
            "id": risk.id,
            "risk_level": risk.risk_level,
            "impact": risk.impact,
            "name": risk.name,
            "description": risk.description,
        }
        name_ids.append(risk.id)
        name_documents.append(risk.name)
        name_metadatas.append(metadata)
        if risk.description.strip():
            desc_ids.append(risk.id)
            desc_documents.append(risk.description)
            desc_metadatas.append(metadata)

    name_col.upsert(ids=name_ids, documents=name_documents, metadatas=name_metadatas)
    if desc_ids:
        desc_col.upsert(ids=desc_ids, documents=desc_documents, metadatas=desc_metadatas)
    _search_cache.clear()
    _logger.info("Ingested %d risks into ChromaDB", len(risks))
    return len(risks)


def search_risks(
    query: str,
    n_results: int = 3,
    collection_name: str = CHROMA_COLLECTION,
) -> list[dict]:
    """Vector search for risks matching the query text.

    Results are cached in memory keyed by ``(query, n_results,
    collection_name)``: repeating the same search term (e.g. the same alert
    title across many findings) returns the cached result directly instead of
    re-querying ChromaDB. The cache is cleared whenever the register changes
    (ingest or clear), so results never go stale.

    Args:
        query: The text to search for.
        n_results: Maximum number of results to return.
        collection_name: Which field collection to search; defaults to the
            risk ``Name`` collection.

    Returns:
        A list of dicts with keys: id, risk_level, impact, name,
        description, distance.
    """
    key = (query, n_results, collection_name)
    cached = _search_cache.get(key)
    if cached is not None:
        _search_cache.move_to_end(key)
        # Return copies so callers can't mutate the cached entries.
        return [dict(entry) for entry in cached]

    col = _collection(collection_name)
    results = col.query(query_texts=[query], n_results=n_results)
    entries: list[dict] = []
    if not results["ids"] or not results["ids"][0]:
        _cache_search(key, entries)
        return entries
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else None
        entries.append(
            {
                "id": meta.get("id", doc_id),
                "risk_level": meta.get("risk_level", ""),
                "impact": meta.get("impact", ""),
                "name": meta.get("name", ""),
                "description": meta.get("description", ""),
                "distance": distance,
            }
        )
    _cache_search(key, entries)
    # Return copies so callers can't mutate the cached entries.
    return [dict(entry) for entry in entries]


def find_risks_by_name(query: str) -> list[dict]:
    """Return risks whose ``Name`` contains *query* (case-insensitive).

    Unlike :func:`search_risks` (vector similarity), this is a deterministic
    substring match on the risk ``Name`` field — the right tool for checking
    whether a proposed new risk name already exists in the register.

    Args:
        query: The name fragment to search for. Leading/trailing whitespace
            is ignored; an empty query matches nothing.

    Returns:
        A list of dicts with keys: id, risk_level, impact, name, description.
        Matches are returned in insertion order; no ``distance`` is included.
    """
    needle = query.strip().lower()
    if not needle:
        return []
    col = _collection(CHROMA_COLLECTION)
    got = col.get(include=["metadatas"])
    entries: list[dict] = []
    for doc_id, meta in zip(got["ids"], got["metadatas"] or []):
        meta = meta or {}
        name = str(meta.get("name", "") or "")
        if needle in name.lower():
            entries.append(
                {
                    "id": str(meta.get("id", doc_id)),
                    "risk_level": str(meta.get("risk_level", "") or ""),
                    "impact": str(meta.get("impact", "") or ""),
                    "name": name,
                    "description": str(meta.get("description", "") or ""),
                }
            )
    return entries


def clear_risks() -> None:
    """Delete all documents from all risk collections."""
    for collection_name in (CHROMA_COLLECTION, CHROMA_COLLECTION_DESCRIPTION):
        col = _collection(collection_name)
        ids = col.get()["ids"]
        if ids:
            col.delete(ids=ids)
            _logger.info("Cleared %d risks from %s", len(ids), collection_name)
    _search_cache.clear()


def _collection_count() -> int:
    """Return the number of documents in the Name collection."""
    col = _collection(CHROMA_COLLECTION)
    return col.count()


def has_risks() -> bool:
    """Return True if the risk register contains any ingested risks.

    Never raises: a missing/corrupt ChromaDB or an empty register both mean
    ``False``, so callers can decide whether to show risk-related UI.
    """
    try:
        return _collection_count() > 0
    except Exception:
        return False


def match_risk(category: str, max_distance: float = 0.9) -> Optional[dict]:
    """Find the closest matching risk for a given issue.

    Two-stage fallback search:
    1. Match ``category`` against the risk ``Name`` field.
    2. If no ``Name`` match is found, fall back to matching the same
       ``category`` against the risk ``Risk Description`` field.

    Args:
        category: The issue category to match — the ``Alert Category``
            column in the reports (each item's ``title``).
        max_distance: Maximum vector distance for a match to be considered
            valid. Lower values mean closer matches. Default 0.9.

    Returns:
        The best matching risk dict, or ``None`` if no match found.
    """
    for collection_name in (CHROMA_COLLECTION, CHROMA_COLLECTION_DESCRIPTION):
        results = search_risks(category, n_results=1, collection_name=collection_name)
        if not results:
            continue
        top = results[0]
        if top["distance"] is not None and top["distance"] > max_distance:
            continue
        return top
    return None


def enrich_test_results(test_results: list[dict], max_distance: float = 0.9) -> int:
    """Enrich a list of test results with matched risk information.

    Each result dict that has a ``title`` key (the ``Alert Category`` column
    in the reports) will be matched against the risk register's ``Name``
    field using the two-stage fallback search. If a match is found, a
    ``matched_risk`` key is added.

    Args:
        test_results: List of test result dicts (each has a ``title`` key).
        max_distance: Maximum vector distance for a match.

    Returns:
        Number of results that were successfully matched to a risk.
    """
    if _collection_count() == 0:
        _logger.warning("\033[33mRisk register is empty — run `x-ray ingest <csv>` first\033[0m")
        return 0
    matched = 0
    for result in test_results:
        title = result.get("title", "")
        if not title:
            continue
        risk = match_risk(title, max_distance=max_distance)
        if risk:
            result["matched_risk"] = risk
            matched += 1
    return matched
