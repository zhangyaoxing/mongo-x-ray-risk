"""Tests for CSV risk register parsing."""

from mongo_x_ray_risk.shared import load_risks_from_csv


def _write(tmp_path, text, name="risks.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_parses_new_column_names_and_ignores_other_notes(tmp_path):
    csv_path = _write(
        tmp_path,
        "ID,Risk level,Impact,Name,Risk description,Other Notes\n"
        "R1,High,Medium,Replication Lag,oplog falls behind,internal note\n"
        "R2,Medium,Low,Missing Index,no matching index,\n",
    )
    risks = load_risks_from_csv(csv_path)
    assert [r.id for r in risks] == ["R1", "R2"]
    assert risks[0].risk_level == "High"
    assert risks[0].impact == "Medium"
    assert risks[0].name == "Replication Lag"
    assert risks[0].description == "oplog falls behind"
    assert risks[1].description == "no matching index"


def test_accepts_old_casing_of_headers(tmp_path):
    csv_path = _write(
        tmp_path,
        "ID,Risk Level,Impact,Name,Risk Description\nR1,High,Medium,Replication Lag,oplog falls behind\n",
    )
    risks = load_risks_from_csv(csv_path)
    assert risks[0].risk_level == "High"
    assert risks[0].description == "oplog falls behind"


def test_ignores_unknown_columns(tmp_path):
    csv_path = _write(
        tmp_path,
        "ID,Risk level,Impact,Name,Risk description,Random field,Owner\n"
        "R1,High,Medium,Replication Lag,oplog falls behind,whatever,alice\n",
    )
    risks = load_risks_from_csv(csv_path)
    assert len(risks) == 1
    assert risks[0].id == "R1"


def test_skips_rows_without_id_or_name(tmp_path):
    csv_path = _write(
        tmp_path,
        "ID,Risk level,Impact,Name,Risk description\n"
        "R1,High,Medium,Replication Lag,oplog falls behind\n"
        ",High,Medium,No Id,has id? no\n"
        "R3,Low,Low,,no name\n",
    )
    risks = load_risks_from_csv(csv_path)
    assert [r.id for r in risks] == ["R1"]


def test_handles_bom_utf8(tmp_path):
    csv_path = tmp_path / "bom.csv"
    csv_path.write_bytes(b"\xef\xbb\xbfID,Risk level,Impact,Name,Risk description\nR1,Low,Low,Backup Failure,failing\n")
    risks = load_risks_from_csv(csv_path)
    assert risks[0].id == "R1"
    assert risks[0].name == "Backup Failure"
