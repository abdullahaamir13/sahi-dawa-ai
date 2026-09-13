import sqlite3

from app.services.history import HistoryRepository


def test_save_and_get_encounters_roundtrip(tmp_path):
    repo = HistoryRepository(db_path=tmp_path / "history.db")
    repo.save_encounter("P001", "Bacterial infection", "MED001", "GRASIL", "100mg")
    repo.save_encounter("P001", "Cold", "MED002", "GRASIL", "250mg")

    encounters = repo.get_encounters("P001")
    assert len(encounters) == 2
    assert encounters[0]["medicine_id"] == "MED001"
    assert encounters[1]["medicine_id"] == "MED002"
    assert encounters[0]["encounter_id"] < encounters[1]["encounter_id"]


def test_encounters_isolated_per_patient(tmp_path):
    repo = HistoryRepository(db_path=tmp_path / "history.db")
    repo.save_encounter("P001", "d", "MED001", "GRASIL", "100mg")
    repo.save_encounter("P002", "d", "MED001", "GRASIL", "100mg")

    assert len(repo.get_encounters("P001")) == 1
    assert len(repo.get_encounters("P002")) == 1


def test_unknown_patient_has_no_encounters(tmp_path):
    repo = HistoryRepository(db_path=tmp_path / "history.db")
    assert repo.get_encounters("NOBODY") == []


def test_repeated_save_does_not_duplicate_patient_row(tmp_path):
    db_path = tmp_path / "history.db"
    repo = HistoryRepository(db_path=db_path)
    repo.save_encounter("P001", "d1", "MED001", "GRASIL", "100mg")
    repo.save_encounter("P001", "d2", "MED002", "GRASIL", "250mg")

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM patients WHERE patient_id = ?", ("P001",)
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_dosage_is_optional(tmp_path):
    repo = HistoryRepository(db_path=tmp_path / "history.db")
    repo.save_encounter("P001", "d", "MED001", "GRASIL", None)

    encounters = repo.get_encounters("P001")
    assert encounters[0]["dosage"] is None
