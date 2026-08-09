"""Persistent, minimal SQLite storage for KrishiMitra farmer memories."""

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "krishimitra.db"


def _connection() -> sqlite3.Connection:
    """Open the on-disk database and ensure its schema exists."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
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
    return connection


def lookup_farmer(user_id: str) -> dict[str, Any] | None:
    """Return one farmer profile, or ``None`` when it has not been saved."""
    try:
        with _connection() as connection:
            row = connection.execute(
                """
                SELECT user_id, name, language_preference, facts, last_interaction
                FROM farmers WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
    except sqlite3.Error:
        logger.exception("Unable to look up farmer memory", extra={"user_id": user_id})
        raise

    if row is None:
        return None

    try:
        facts = json.loads(row[3])
    except (json.JSONDecodeError, TypeError):
        logger.warning("Ignoring invalid facts JSON for user_id=%s", user_id)
        facts = {}

    return {
        "user_id": row[0],
        "name": row[1],
        "language_preference": row[2],
        "facts": facts,
        "last_interaction": row[4],
    }


def save_farmer_memory(
    user_id: str,
    name: str | None,
    language_preference: str | None,
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Merge useful farming facts into an existing profile and persist it."""
    existing = lookup_farmer(user_id)
    merged_facts = (existing or {}).get("facts", {})
    merged_facts.update(
        {key: value for key, value in facts.items() if value is not None}
    )
    profile = {
        "user_id": user_id,
        "name": name or (existing or {}).get("name"),
        "language_preference": language_preference
        or (existing or {}).get("language_preference"),
        "facts": merged_facts,
        "last_interaction": datetime.now(UTC).isoformat(),
    }

    try:
        with _connection() as connection:
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
    except sqlite3.Error:
        logger.exception("Unable to save farmer memory", extra={"user_id": user_id})
        raise

    return profile
