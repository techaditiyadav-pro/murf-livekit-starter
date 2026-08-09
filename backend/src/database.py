"""Persistent, privacy-conscious storage for KrishiMitra farmer profiles."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "krishimitra.db"


class FarmerRepository:
    """SQLite repository; each operation opens its own short-lived connection."""

    def __init__(self, database_path: Path | str = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS farmers (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    language_preference TEXT,
                    facts TEXT NOT NULL DEFAULT '{}',
                    last_interaction TEXT NOT NULL
                )
                """
            )

    def lookup_farmer(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT user_id, name, language_preference, facts, last_interaction "
                "FROM farmers WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            facts = json.loads(row["facts"])
        except json.JSONDecodeError:
            facts = {}
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": facts,
            "last_interaction": row["last_interaction"],
        }

    def save_farmer_memory(
        self,
        user_id: str,
        name: str | None,
        language_preference: str | None,
        facts: dict[str, Any],
    ) -> dict[str, Any]:
        """Upsert a profile, retaining previous facts omitted by a later update."""
        existing = self.lookup_farmer(user_id)
        merged_facts = {**(existing or {}).get("facts", {}), **facts}
        profile = {
            "user_id": user_id,
            "name": name or (existing or {}).get("name"),
            "language_preference": language_preference
            or (existing or {}).get("language_preference"),
            "facts": merged_facts,
            "last_interaction": datetime.now(UTC).isoformat(),
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO farmers (user_id, name, language_preference, facts, last_interaction)
                VALUES (:user_id, :name, :language_preference, :facts, :last_interaction)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    language_preference = excluded.language_preference,
                    facts = excluded.facts,
                    last_interaction = excluded.last_interaction
                """,
                {**profile, "facts": json.dumps(merged_facts, ensure_ascii=False)},
            )
        return profile
