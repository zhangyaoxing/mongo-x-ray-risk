"""
Copyright (c) 2026 MongoDB Inc.

DISCLAIMER: THESE CODE SAMPLES ARE PROVIDED FOR EDUCATIONAL AND ILLUSTRATIVE PURPOSES ONLY,
TO DEMONSTRATE THE FUNCTIONALITY OF SPECIFIC MONGODB FEATURES.
THEY ARE NOT PRODUCTION-READY AND MAY LACK THE SECURITY HARDENING, ERROR HANDLING, AND TESTING REQUIRED FOR A LIVE ENVIRONMENT.
YOU ARE RESPONSIBLE FOR TESTING, VALIDATING, AND SECURING THIS CODE WITHIN YOUR OWN ENVIRONMENT BEFORE IMPLEMENTATION.
THIS MATERIAL IS PROVIDED "AS IS" WITHOUT WARRANTY OR LIABILITY.

Tests for the risk register ``search`` command plugin.
"""

import argparse

from mongo_x_ray_risk.plugin import SearchPlugin


def _args(**overrides) -> argparse.Namespace:
    ns = argparse.Namespace(string=None)
    ns.__dict__.update(overrides)
    return ns


def test_plugin_metadata():
    assert SearchPlugin.name == "search"
    assert SearchPlugin.distribution == "mongo-x-ray-risk"
    assert "risk register" in SearchPlugin.help
    assert "case-insensitive" in SearchPlugin.description
    assert "x-ray search" in SearchPlugin.epilog


def test_run_prints_matching_risks(monkeypatch, capsys):
    matches = [
        {
            "id": "R1",
            "risk_level": "High",
            "impact": "Medium",
            "name": "Replication Lag",
            "description": "oplog falls behind",
        },
        {
            "id": "R2",
            "risk_level": "Medium",
            "impact": "Low",
            "name": "Missing Index",
            "description": "no matching index",
        },
    ]
    seen = {}

    def fake_find(query):
        seen["query"] = query
        return matches

    monkeypatch.setattr("mongo_x_ray_risk.plugin.find_risks_by_name", fake_find)

    assert SearchPlugin().run(_args(string="Replication")) == 0
    assert seen == {"query": "Replication"}
    out = capsys.readouterr().out
    assert "Name: Replication Lag" in out
    assert "Risk description: oplog falls behind" in out
    assert "Name: Missing Index" in out


def test_run_no_match_returns_1(monkeypatch):
    monkeypatch.setattr("mongo_x_ray_risk.plugin.find_risks_by_name", lambda query: [])
    assert SearchPlugin().run(_args(string="Nothing Here")) == 1


def test_run_empty_string_returns_error():
    assert SearchPlugin().run(_args(string="   ")) == 1


def test_run_search_failure_returns_error(monkeypatch):
    def boom(_query):
        raise RuntimeError("chromadb unavailable")

    monkeypatch.setattr("mongo_x_ray_risk.plugin.find_risks_by_name", boom)
    assert SearchPlugin().run(_args(string="Replication")) == 1
