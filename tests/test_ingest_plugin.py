"""Tests for the risk register ``ingest`` command plugin."""

import argparse

from mongo_x_ray_risk.plugin import IngestPlugin


def _args(**overrides) -> argparse.Namespace:
    ns = argparse.Namespace(csv=None, clear=False)
    ns.__dict__.update(overrides)
    return ns


def test_plugin_metadata():
    assert IngestPlugin.name == "ingest"
    assert IngestPlugin.distribution == "mongo-x-ray-risk"
    assert "CSV" in IngestPlugin.help
    assert "ID, Risk level, Impact, Name, Risk description" in IngestPlugin.description
    assert "Other Notes" in IngestPlugin.description
    assert "x-ray ingest risk_register.csv" in IngestPlugin.epilog


def test_run_ingests_csv_rows(monkeypatch, tmp_path):
    csv_path = tmp_path / "risks.csv"
    csv_path.write_text(
        "ID,Risk level,Impact,Name,Risk description,Other Notes\n"
        "R1,High,Medium,Replication Lag,oplog falls behind,internal note\n"
        "R2,Medium,Low,Missing Index,no matching index,\n"
        ",,Low,No Id Here,skipped,note\n",
        encoding="utf-8",
    )
    seen = {}

    def fake_ingest(risks):
        seen["risks"] = risks
        return len(risks)

    monkeypatch.setattr("mongo_x_ray_risk.plugin.ingest_risks", fake_ingest)

    assert IngestPlugin().run(_args(csv=str(csv_path))) == 0
    assert [r.id for r in seen["risks"]] == ["R1", "R2"]
    assert seen["risks"][0].name == "Replication Lag"
    assert seen["risks"][0].risk_level == "High"
    assert seen["risks"][0].impact == "Medium"
    assert seen["risks"][0].description == "oplog falls behind"


def test_run_clear_empties_register_first(monkeypatch, tmp_path):
    csv_path = tmp_path / "risks.csv"
    csv_path.write_text("ID,Risk level,Impact,Name,Risk description\nR1,Low,Low,One Risk,x\n", encoding="utf-8")
    cleared = []
    monkeypatch.setattr("mongo_x_ray_risk.plugin.clear_risks", lambda: cleared.append(True))
    monkeypatch.setattr("mongo_x_ray_risk.plugin.ingest_risks", lambda risks: len(risks))

    assert IngestPlugin().run(_args(csv=str(csv_path), clear=True)) == 0
    assert cleared == [True]


def test_run_clear_without_csv_only_clears(monkeypatch):
    cleared = []
    ingest_called = []
    monkeypatch.setattr("mongo_x_ray_risk.plugin.clear_risks", lambda: cleared.append(True))
    monkeypatch.setattr("mongo_x_ray_risk.plugin.ingest_risks", lambda risks: ingest_called.append(risks))

    assert IngestPlugin().run(_args(clear=True)) == 0
    assert cleared == [True]
    assert ingest_called == []


def test_run_without_csv_or_clear_returns_error():
    assert IngestPlugin().run(_args()) == 1


def test_run_missing_csv_returns_error(tmp_path):
    assert IngestPlugin().run(_args(csv=str(tmp_path / "nope.csv"))) == 1


def test_run_csv_without_valid_rows_returns_error(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("ID,Risk level,Impact,Name,Risk description\n", encoding="utf-8")
    assert IngestPlugin().run(_args(csv=str(csv_path))) == 1


def test_run_unreadable_csv_returns_error(monkeypatch, tmp_path):
    csv_path = tmp_path / "broken.csv"
    csv_path.write_text("x\n", encoding="utf-8")

    def boom(_path):
        raise OSError("boom")

    monkeypatch.setattr("mongo_x_ray_risk.plugin.load_risks_from_csv", boom)
    assert IngestPlugin().run(_args(csv=str(csv_path))) == 1
