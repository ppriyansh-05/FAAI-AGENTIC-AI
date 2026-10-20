"""Local SQLite persistence layer for AccessAble AI audit runs."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path("accessable_ai.db")


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize audit history table."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                input_source TEXT,
                input_fingerprint TEXT,
                finding_count INTEGER,
                high_count INTEGER,
                medium_count INTEGER,
                low_count INTEGER,
                resolved_fix_count INTEGER,
                retry_iterations INTEGER,
                engine_mode TEXT,
                status TEXT
            )
        """)
        conn.commit()


def record_audit(
    audit_id: str,
    input_source: str,
    raw_html: str,
    finding_count: int,
    counts: dict[str, int],
    resolved_fix_count: int,
    retry_iterations: int,
    engine_mode: str,
    status: str,
    db_path: Path = DB_PATH,
) -> None:
    """Records audit summary using cryptographic fingerprint instead of storing full raw HTML."""
    init_db(db_path)
    fingerprint = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()[:16]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO audit_history 
            (id, timestamp, input_source, input_fingerprint, finding_count, high_count, medium_count, low_count, resolved_fix_count, retry_iterations, engine_mode, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                time.time(),
                input_source,
                fingerprint,
                finding_count,
                counts.get("High", 0),
                counts.get("Medium", 0),
                counts.get("Low", 0),
                resolved_fix_count,
                retry_iterations,
                engine_mode,
                status,
            ),
        )
        conn.commit()


def get_audit_history(limit: int = 20, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Returns recent audit runs."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM audit_history ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
