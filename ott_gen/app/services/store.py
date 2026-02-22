from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CandidateItem:
    id: int
    tmdb_id: int
    media_type: str
    source: str
    title: str
    overview: str
    original_overview: str
    enriched_overview: str
    rating: str
    genres: str
    year: str
    provider_names: str
    poster_url: str
    still_urls: list[str]
    status: str
    generated_at: str | None
    b_post_id: int | None
    error_message: str | None


class Store:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tmdb_id INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    overview TEXT NOT NULL,
                    original_overview TEXT NOT NULL DEFAULT '',
                    enriched_overview TEXT NOT NULL DEFAULT '',
                    rating TEXT NOT NULL,
                    genres TEXT NOT NULL,
                    year TEXT NOT NULL,
                    provider_names TEXT NOT NULL,
                    poster_url TEXT NOT NULL,
                    still_urls TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    generated_at TEXT,
                    b_post_id INTEGER,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tmdb_id, media_type)
                )
                """
            )
            self._ensure_column(conn, "candidates", "original_overview", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "candidates", "enriched_overview", "TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_stats (
                    ymd TEXT PRIMARY KEY,
                    generated_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawler_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        col_names = {str(c[1]) for c in cols}
        if column not in col_names:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def upsert_candidate(
        self,
        *,
        tmdb_id: int,
        media_type: str,
        source: str,
        title: str,
        overview: str,
        original_overview: str,
        enriched_overview: str,
        rating: str,
        genres: str,
        year: str,
        provider_names: str,
        poster_url: str,
        still_urls: list[str],
        dedup_days: int,
    ) -> bool:
        now = self._now()
        still_json = json.dumps(still_urls, ensure_ascii=False)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, status, generated_at FROM candidates WHERE tmdb_id=? AND media_type=?",
                (tmdb_id, media_type),
            ).fetchone()
            if row:
                current_status = str(row["status"] or "")
                if current_status in {"generated", "generating"}:
                    return False
                conn.execute(
                    """
                    UPDATE candidates
                    SET source=?, title=?, overview=?, original_overview=?, enriched_overview=?, rating=?, genres=?, year=?,
                        provider_names=?, poster_url=?, still_urls=?,
                        status='queued', error_message=NULL, updated_at=?
                    WHERE id=?
                    """,
                    (
                        source,
                        title,
                        overview,
                        original_overview,
                        enriched_overview,
                        rating,
                        genres,
                        year,
                        provider_names,
                        poster_url,
                        still_json,
                        now,
                        row["id"],
                    ),
                )
                return True

            conn.execute(
                """
                INSERT INTO candidates (
                    tmdb_id, media_type, source, title, overview, original_overview, enriched_overview, rating, genres, year,
                    provider_names, poster_url, still_urls, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)
                """,
                (
                    tmdb_id,
                    media_type,
                    source,
                    title,
                    overview,
                    original_overview,
                    enriched_overview,
                    rating,
                    genres,
                    year,
                    provider_names,
                    poster_url,
                    still_json,
                    now,
                    now,
                ),
            )
            return True

    def count_candidates(self, status: str = "queued", min_overview_length: int = 0) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM candidates WHERE status=? AND LENGTH(overview) >= ?",
                (status, max(0, min_overview_length)),
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def list_candidates(
        self,
        status: str = "queued",
        limit: int = 50,
        offset: int = 0,
        min_overview_length: int = 0,
    ) -> list[CandidateItem]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM candidates
                WHERE status=? AND LENGTH(overview) >= ?
                ORDER BY updated_at DESC
                LIMIT ?
                OFFSET ?
                """,
                (status, max(0, min_overview_length), limit, max(0, offset)),
            ).fetchall()
        return [self._to_item(r) for r in rows]

    def get_candidate(self, candidate_id: int) -> CandidateItem | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        return self._to_item(row) if row else None

    def get_next_queued(self, limit: int, min_overview_length: int = 0) -> list[CandidateItem]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM candidates
                WHERE status='queued' AND LENGTH(overview) >= ?
                ORDER BY
                    CASE
                        WHEN source LIKE 'latest_daily%' THEN 0
                        WHEN source LIKE 'backfill%' THEN 1
                        ELSE 2
                    END ASC,
                    updated_at ASC
                LIMIT ?
                """,
                (max(0, min_overview_length), limit),
            ).fetchall()
        return [self._to_item(r) for r in rows]

    def acquire_generation_lock(self, candidate_id: int) -> bool:
        now = self._now()
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE candidates
                SET status='generating', updated_at=?
                WHERE id=? AND status='queued'
                """,
                (now, candidate_id),
            )
            return cur.rowcount > 0

    def update_overview_texts(self, candidate_id: int, overview: str, original_overview: str, enriched_overview: str) -> None:
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE candidates
                SET overview=?, original_overview=?, enriched_overview=?, updated_at=?
                WHERE id=?
                """,
                (overview, original_overview, enriched_overview, now, candidate_id),
            )

    def mark_generated(self, candidate_id: int, b_post_id: int | None) -> None:
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE candidates
                SET status='generated', generated_at=?, b_post_id=?, error_message=NULL, updated_at=?
                WHERE id=?
                """,
                (now, b_post_id, now, candidate_id),
            )

    def mark_failed(self, candidate_id: int, error: str) -> None:
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE candidates
                SET status='failed', error_message=?, updated_at=?
                WHERE id=?
                """,
                (error[:2000], now, candidate_id),
            )

    def reset_to_queued(self, candidate_id: int) -> bool:
        now = self._now()
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE candidates
                SET status='queued', generated_at=NULL, b_post_id=NULL, error_message=NULL, updated_at=?
                WHERE id=?
                """,
                (now, candidate_id),
            )
            return cur.rowcount > 0

    def delete_candidate(self, candidate_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM candidates WHERE id=?", (candidate_id,))
            return cur.rowcount > 0

    def today_generated_count(self) -> int:
        ymd = datetime.utcnow().strftime("%Y-%m-%d")
        with self._conn() as conn:
            row = conn.execute("SELECT generated_count FROM daily_stats WHERE ymd=?", (ymd,)).fetchone()
        return int(row["generated_count"]) if row else 0

    def increment_today_generated(self, n: int = 1) -> None:
        ymd = datetime.utcnow().strftime("%Y-%m-%d")
        now = self._now()
        with self._conn() as conn:
            row = conn.execute("SELECT generated_count FROM daily_stats WHERE ymd=?", (ymd,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE daily_stats SET generated_count=generated_count+?, updated_at=? WHERE ymd=?",
                    (n, now, ymd),
                )
            else:
                conn.execute(
                    "INSERT INTO daily_stats (ymd, generated_count, updated_at) VALUES (?, ?, ?)",
                    (ymd, n, now),
                )

    def get_state(self, key: str, default: str = "") -> str:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM crawler_state WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        return str(row["value"] or default)

    def get_state_int(self, key: str, default: int = 0) -> int:
        raw = self.get_state(key, str(default))
        try:
            return int(raw)
        except Exception:
            return default

    def set_state(self, key: str, value: str) -> None:
        now = self._now()
        with self._conn() as conn:
            row = conn.execute("SELECT key FROM crawler_state WHERE key=?", (key,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE crawler_state SET value=?, updated_at=? WHERE key=?",
                    (value, now, key),
                )
            else:
                conn.execute(
                    "INSERT INTO crawler_state (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, now),
                )

    def _to_item(self, row: sqlite3.Row) -> CandidateItem:
        return CandidateItem(
            id=int(row["id"]),
            tmdb_id=int(row["tmdb_id"]),
            media_type=str(row["media_type"]),
            source=str(row["source"]),
            title=str(row["title"]),
            overview=str(row["overview"]),
            original_overview=str(row["original_overview"] or ""),
            enriched_overview=str(row["enriched_overview"] or ""),
            rating=str(row["rating"]),
            genres=str(row["genres"]),
            year=str(row["year"]),
            provider_names=str(row["provider_names"]),
            poster_url=str(row["poster_url"]),
            still_urls=json.loads(row["still_urls"] or "[]"),
            status=str(row["status"]),
            generated_at=row["generated_at"],
            b_post_id=row["b_post_id"],
            error_message=row["error_message"],
        )
