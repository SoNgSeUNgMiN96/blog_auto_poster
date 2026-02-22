from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class DedupStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ott_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tmdb_id INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    last_posted_at TEXT NOT NULL,
                    UNIQUE(tmdb_id, media_type)
                )
                """
            )

    def is_recently_posted(self, tmdb_id: int, media_type: str, dedup_days: int) -> bool:
        cutoff = (datetime.utcnow() - timedelta(days=dedup_days)).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM ott_sources
                WHERE tmdb_id = ? AND media_type = ? AND last_posted_at >= ?
                LIMIT 1
                """,
                (tmdb_id, media_type, cutoff),
            ).fetchone()
        return row is not None

    def mark_posted(self, tmdb_id: int, media_type: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ott_sources (tmdb_id, media_type, last_posted_at)
                VALUES (?, ?, ?)
                ON CONFLICT(tmdb_id, media_type)
                DO UPDATE SET last_posted_at = excluded.last_posted_at
                """,
                (tmdb_id, media_type, now),
            )
