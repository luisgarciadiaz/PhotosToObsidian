from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    return Path(__file__).parent.parent / "photos_to_obsidian.db"


def init_db(db_path: Optional[Path] = None) -> None:
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""DROP TABLE IF EXISTS processed_files""")

    cursor.execute("""
        CREATE TABLE processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            status TEXT NOT NULL,
            tries INTEGER NOT NULL,
            last_tried_at TEXT NOT NULL,
            note_path TEXT,
            ocr_engine_used TEXT,
            ocr_confidence REAL
        )
    """)

    conn.commit()
    conn.close()


def upsert_attempt(
    file_path: Path,
    status: str,
    engine: str,
    note_path: Optional[Path] = None,
    ocr_confidence: float = 0.0,
    db_path: Optional[Path] = None,
) -> None:
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        init_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    file_name = file_path.name
    file_path_str = str(file_path.absolute())

    cursor.execute(
        "SELECT id, tries FROM processed_files WHERE file_path = ?",
        (file_path_str,),
    )
    row = cursor.fetchone()

    now = datetime.now(timezone.utc).isoformat()

    if row is None:
        cursor.execute(
            """
            INSERT INTO processed_files
            (file_name, file_path, status, tries, last_tried_at, note_path, ocr_engine_used, ocr_confidence)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                file_name,
                file_path_str,
                status,
                now,
                str(note_path) if note_path else None,
                engine,
                ocr_confidence,
            ),
        )
    else:
        record_id, current_tries = row
        cursor.execute(
            """
            UPDATE processed_files
            SET status = ?, tries = ?, last_tried_at = ?, note_path = ?, ocr_engine_used = ?, ocr_confidence = ?
            WHERE id = ?
            """,
            (
                status,
                current_tries + 1,
                now,
                str(note_path) if note_path else None,
                engine,
                ocr_confidence,
                record_id,
            ),
        )

    conn.commit()
    conn.close()


def get_tries(file_path: Path, db_path: Optional[Path] = None) -> int:
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT tries FROM processed_files WHERE file_path = ?",
        (str(file_path.absolute()),),
    )
    row = cursor.fetchone()

    conn.close()

    if row is None:
        return 0

    return row[0]


def get_all_records(db_path: Optional[Path] = None) -> list[dict]:
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT file_name, status, tries, last_tried_at, note_path, ocr_engine_used, ocr_confidence
        FROM processed_files
        ORDER BY last_tried_at DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    records = []
    for row in rows:
        records.append({
            "file_name": row[0],
            "status": row[1],
            "tries": row[2],
            "last_tried_at": row[3],
            "note_path": row[4],
            "ocr_engine_used": row[5],
        })

    return records


def clear_success_records(db_path: Optional[Path] = None) -> None:
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM processed_files WHERE status = ?", ("success",))

    conn.commit()
    conn.close()