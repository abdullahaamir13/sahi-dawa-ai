"""SQLite-backed patient encounter history.

Not an EMR: a lightweight append-only log keyed by patient_id. Medicine
facts (brand, category) are never copied in -- only medicine_id is stored,
so a later catalogue correction applies retroactively without a migration.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "sahi_dawa.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS encounters (
    encounter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    diagnosis TEXT NOT NULL,
    medicine_id TEXT NOT NULL,
    medicine_name TEXT NOT NULL,
    dosage TEXT,
    encounter_date TEXT NOT NULL
);
"""


class HistoryRepository:
    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            with conn:
                conn.executescript(SCHEMA)
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_encounter(
        self,
        patient_id: str,
        diagnosis: str,
        medicine_id: str,
        medicine_name: str,
        dosage: Optional[str],
    ) -> int:
        today = date.today().isoformat()
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    "INSERT OR IGNORE INTO patients (patient_id, created_at) VALUES (?, ?)",
                    (patient_id, today),
                )
                cursor = conn.execute(
                    """INSERT INTO encounters
                       (patient_id, diagnosis, medicine_id, medicine_name, dosage, encounter_date)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (patient_id, diagnosis, medicine_id, medicine_name, dosage, today),
                )
                return cursor.lastrowid
        finally:
            conn.close()

    def get_encounters(self, patient_id: str) -> List[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT encounter_id, patient_id, diagnosis, medicine_id,
                          medicine_name, dosage, encounter_date
                   FROM encounters WHERE patient_id = ? ORDER BY encounter_id ASC""",
                (patient_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
