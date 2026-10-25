"""SQLite-backed structured logging for API prediction calls."""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "predict_logs.sqlite3"
DB_PATH = Path(os.getenv("PREDICT_LOG_DB", str(DEFAULT_DB_PATH)))


def init_db() -> None:
    """Create the prediction log table if it does not already exist."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS predict_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                drug_name TEXT NOT NULL,
                latency_ms REAL NOT NULL
            )
            """
        )
        connection.commit()


def log_predict_call(drug_name: str, latency_ms: float) -> None:
    """Persist one structured prediction-call log row."""

    init_db()
    timestamp = datetime.now(UTC).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO predict_logs (timestamp, drug_name, latency_ms)
            VALUES (?, ?, ?)
            """,
            (timestamp, drug_name, latency_ms),
        )
        connection.commit()

