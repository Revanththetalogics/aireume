"""O*NET SQLite cache manager.

Manages a local SQLite database containing O*NET occupational data
for occupation-aware skill validation. No external dependencies.
"""

import sqlite3
import logging
import os
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS onet_occupation (
    soc_code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS onet_technology_skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    soc_code TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    commodity_code INTEGER,
    commodity_title TEXT,
    is_hot_technology INTEGER DEFAULT 0,
    is_in_demand INTEGER DEFAULT 0,
    UNIQUE(soc_code, skill_name)
);

CREATE TABLE IF NOT EXISTS onet_alternate_title (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    soc_code TEXT NOT NULL,
    title TEXT NOT NULL,
    short_title TEXT
);

CREATE TABLE IF NOT EXISTS onet_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_tech_skill_soc ON onet_technology_skill(soc_code);
CREATE INDEX IF NOT EXISTS idx_tech_skill_name ON onet_technology_skill(skill_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_alt_title ON onet_alternate_title(title COLLATE NOCASE);
"""


class ONETCache:
    """SQLite-backed cache for O*NET occupational data."""

    def __init__(self, db_path: str):
        """Open or create the SQLite cache at *db_path*."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    def is_populated(self) -> bool:
        """Return True if the cache contains at least one occupation."""
        cur = self._conn.execute(
            "SELECT COUNT(*) FROM onet_occupation LIMIT 1"
        )
        return cur.fetchone()[0] > 0

    def get_version(self) -> Optional[str]:
        """Return the O*NET version stored in metadata, or None."""
        cur = self._conn.execute(
            "SELECT value FROM onet_metadata WHERE key = 'version' LIMIT 1"
        )
        row = cur.fetchone()
        return row[0] if row else None

    def set_metadata(self, key: str, value: str) -> None:
        """Upsert a metadata key/value pair."""
        self._conn.execute(
            """
            INSERT INTO onet_metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self._conn.commit()

    def upsert_occupation(self, soc_code: str, title: str, description: str) -> None:
        """Insert or replace an occupation record."""
        self._conn.execute(
            """
            INSERT INTO onet_occupation (soc_code, title, description)
            VALUES (?, ?, ?)
            ON CONFLICT(soc_code) DO UPDATE SET
                title = excluded.title,
                description = excluded.description
            """,
            (soc_code, title, description),
        )

    def upsert_technology_skill(
        self,
        soc_code: str,
        skill_name: str,
        commodity_code: Optional[int],
        commodity_title: Optional[str],
        is_hot: bool,
        is_in_demand: bool,
    ) -> None:
        """Insert or replace a technology skill record."""
        self._conn.execute(
            """
            INSERT INTO onet_technology_skill
                (soc_code, skill_name, commodity_code, commodity_title,
                 is_hot_technology, is_in_demand)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(soc_code, skill_name) DO UPDATE SET
                commodity_code = excluded.commodity_code,
                commodity_title = excluded.commodity_title,
                is_hot_technology = excluded.is_hot_technology,
                is_in_demand = excluded.is_in_demand
            """,
            (
                soc_code,
                skill_name,
                commodity_code,
                commodity_title,
                1 if is_hot else 0,
                1 if is_in_demand else 0,
            ),
        )

    def upsert_alternate_title(
        self,
        soc_code: str,
        title: str,
        short_title: Optional[str],
    ) -> None:
        """Insert or replace an alternate title record."""
        self._conn.execute(
            """
            INSERT INTO onet_alternate_title (soc_code, title, short_title)
            VALUES (?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            (soc_code, title, short_title),
        )

    def get_occupation(self, soc_code: str) -> Optional[Dict]:
        """Return occupation dict for a given SOC code, or None."""
        cur = self._conn.execute(
            "SELECT soc_code, title, description FROM onet_occupation WHERE soc_code = ? LIMIT 1",
            (soc_code,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_skills_for_occupation(self, soc_code: str) -> List[Dict]:
        """Return all technology skills mapped to *soc_code*."""
        cur = self._conn.execute(
            """
            SELECT skill_name, commodity_code, commodity_title,
                   is_hot_technology, is_in_demand
            FROM onet_technology_skill
            WHERE soc_code = ?
            ORDER BY is_hot_technology DESC, is_in_demand DESC, skill_name
            """,
            (soc_code,),
        )
        return [dict(row) for row in cur.fetchall()]

    def find_soc_by_title(self, job_title: str) -> List[Tuple[str, str, float]]:
        """Find SOC codes matching *job_title* using case-insensitive LIKE.

        Returns a list of tuples: (soc_code, title, score).
        Score is 1.0 for exact alternate-title matches, 0.5 for LIKE matches.
        """
        norm = job_title.strip().lower()
        # Exact match on alternate titles first
        cur = self._conn.execute(
            """
            SELECT DISTINCT o.soc_code, o.title
            FROM onet_occupation o
            JOIN onet_alternate_title a ON o.soc_code = a.soc_code
            WHERE lower(a.title) = ?
            """,
            (norm,),
        )
        exact = cur.fetchall()

        # LIKE match on occupation title and alternate titles
        like_pattern = f"%{norm}%"
        cur = self._conn.execute(
            """
            SELECT DISTINCT o.soc_code, o.title
            FROM onet_occupation o
            LEFT JOIN onet_alternate_title a ON o.soc_code = a.soc_code
            WHERE o.title LIKE ? ESCAPE '\\'
               OR a.title LIKE ? ESCAPE '\\'
            """,
            (like_pattern, like_pattern),
        )
        like_rows = cur.fetchall()

        results = []
        seen = set()
        for row in exact:
            key = row[0]
            if key not in seen:
                seen.add(key)
                results.append((row[0], row[1], 1.0))
        for row in like_rows:
            key = row[0]
            if key not in seen:
                seen.add(key)
                results.append((row[0], row[1], 0.5))
        return results

    def get_all_hot_technologies(self) -> List[str]:
        """Return distinct skill names marked as hot technology."""
        cur = self._conn.execute(
            """
            SELECT DISTINCT skill_name
            FROM onet_technology_skill
            WHERE is_hot_technology = 1
            ORDER BY skill_name
            """
        )
        return [row[0] for row in cur.fetchall()]

    def skill_exists_for_occupation(self, skill_name: str, soc_code: str) -> bool:
        """Return True if *skill_name* is mapped to *soc_code*."""
        cur = self._conn.execute(
            """
            SELECT 1 FROM onet_technology_skill
            WHERE soc_code = ? AND skill_name = ? COLLATE NOCASE
            LIMIT 1
            """,
            (soc_code, skill_name),
        )
        return cur.fetchone() is not None

    def commit(self) -> None:
        """Commit any pending transactions."""
        self._conn.commit()
