"""
Copyright (c) 2026 MongoDB Inc.

DISCLAIMER: THESE CODE SAMPLES ARE PROVIDED FOR EDUCATIONAL AND ILLUSTRATIVE PURPOSES ONLY,
TO DEMONSTRATE THE FUNCTIONALITY OF SPECIFIC MONGODB FEATURES.
THEY ARE NOT PRODUCTION-READY AND MAY LACK THE SECURITY HARDENING, ERROR HANDLING, AND TESTING REQUIRED FOR A LIVE ENVIRONMENT.
YOU ARE RESPONSIBLE FOR TESTING, VALIDATING, AND SECURING THIS CODE WITHIN YOUR OWN ENVIRONMENT BEFORE IMPLEMENTATION.
THIS MATERIAL IS PROVIDED "AS IS" WITHOUT WARRANTY OR LIABILITY.

Shared constants and data model for the Risk Register module.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

# Embed the Risk Name and Risk Description fields for vector search.
# Each field lives in its own collection so matching can fall back from
# Name to Risk Description.
CHROMA_COLLECTION = "risk_register"
CHROMA_COLLECTION_DESCRIPTION = "risk_register_description"
EMBED_FIELDS = ("Name", "Risk Description")


@dataclass
class Risk:
    """A single risk entry from the CSV risk register."""

    id: str
    risk_level: str
    impact: str
    name: str
    description: str


def _normalize_header(header: str) -> str:
    """Normalize a CSV header for case/whitespace-insensitive matching."""
    return (header or "").strip().lower()


def load_risks_from_csv(csv_path: Path) -> list[Risk]:
    """Parse a CSV risk register file.

    Used columns (matched case-insensitively; any other columns, e.g.
    ``Other Notes``, are ignored):
        ID, Risk level, Impact, Name, Risk description

    Rows without an ID or a Name are skipped.
    """
    risks: list[Risk] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = {_normalize_header(h): h for h in (reader.fieldnames or [])}
        for row in reader:
            risk = Risk(
                id=(row.get(headers.get("id", "")) or "").strip(),
                risk_level=(row.get(headers.get("risk level", "")) or "").strip(),
                impact=(row.get(headers.get("impact", "")) or "").strip(),
                name=(row.get(headers.get("name", "")) or "").strip(),
                description=(row.get(headers.get("risk description", "")) or "").strip(),
            )
            if risk.id and risk.name:
                risks.append(risk)
    return risks


def get_db_path() -> Path:
    """Return the platform-specific database directory path."""
    import platform

    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home()
    return base / ".x-ray"
