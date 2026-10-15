from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().with_name("telemetry.db")


def get_connection(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(database_path) if database_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def initialize_database(database_path: str | Path | None = None) -> Path:
    path = Path(database_path) if database_path is not None else DEFAULT_DB_PATH
    with get_connection(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hostname TEXT NOT NULL,
                cpu_percent REAL NOT NULL,
                memory_percent REAL NOT NULL,
                disk_percent REAL NOT NULL,
                metrics_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp)"
        )
    return path


def save_snapshot(metrics: dict[str, Any], database_path: str | Path | None = None) -> int:
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a dictionary")

    path = Path(database_path) if database_path is not None else DEFAULT_DB_PATH
    with get_connection(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO snapshots (
                timestamp, hostname, cpu_percent, memory_percent,
                disk_percent, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                metrics["timestamp"],
                metrics["hostname"],
                metrics["cpu_percent"],
                metrics["memory_percent"],
                metrics["disk_percent"],
                json.dumps(metrics, sort_keys=True),
            ),
        )
        return int(cursor.lastrowid)


def get_recent_snapshots(
    limit: int = 20,
    database_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    path = Path(database_path) if database_path is not None else DEFAULT_DB_PATH
    with get_connection(path) as connection:
        rows = connection.execute(
            "SELECT metrics_json FROM snapshots ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [json.loads(row["metrics_json"]) for row in reversed(rows)]


def get_snapshot_count(database_path: str | Path | None = None) -> int:
    path = Path(database_path) if database_path is not None else DEFAULT_DB_PATH
    with get_connection(path) as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM snapshots").fetchone()
    return int(row["total"])
