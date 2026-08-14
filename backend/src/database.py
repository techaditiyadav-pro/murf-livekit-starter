"""Persistent, privacy-conscious storage for KrishiMitra farmer profiles."""

import json
import re
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS escalations (
                    reference_id TEXT PRIMARY KEY,
                    farmer_name TEXT,
                    farmer_identifier TEXT,
                    reason TEXT NOT NULL,
                    problem_summary TEXT NOT NULL,
                    what_agent_checked TEXT NOT NULL,
                    urgency TEXT NOT NULL CHECK (urgency IN ('low', 'medium', 'high', 'emergency')),
                    language TEXT NOT NULL,
                    preferred_follow_up_method TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS call_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT NOT NULL UNIQUE,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    channel TEXT NOT NULL DEFAULT 'browser',
                    outcome TEXT NOT NULL,
                    turns_count INTEGER NOT NULL DEFAULT 0,
                    user_turns INTEGER NOT NULL DEFAULT 0,
                    tools_used TEXT NOT NULL DEFAULT '[]',
                    used_search INTEGER NOT NULL DEFAULT 0,
                    human_help_requested INTEGER NOT NULL DEFAULT 0,
                    language TEXT,
                    failure_reason TEXT,
                    success_condition TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            # Automatic column migration for existing databases
            existing_cols = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(call_analytics)"
                ).fetchall()
            }
            columns_to_add = [
                ("turns_count", "INTEGER NOT NULL DEFAULT 0"),
                ("user_turns", "INTEGER NOT NULL DEFAULT 0"),
                ("tools_used", "TEXT NOT NULL DEFAULT '[]'"),
                ("used_search", "INTEGER NOT NULL DEFAULT 0"),
                ("human_help_requested", "INTEGER NOT NULL DEFAULT 0"),
                ("language", "TEXT"),
            ]
            for col_name, col_def in columns_to_add:
                if col_name not in existing_cols:
                    connection.execute(
                        f"ALTER TABLE call_analytics ADD COLUMN {col_name} {col_def}"
                    )

    @staticmethod
    def _sanitize_summary(value: str) -> str:
        """Remove secrets and keep human-facing escalation notes concise."""
        value = " ".join(value.split())[:600]
        patterns = (
            r"(?i)\b(?:otp|pin|password|passcode)\s*[:=-]?\s*\S+",
            r"(?i)\b(?:account|bank|card)\s*(?:number|no\.?|details?)?\s*[:=-]?\s*[\d -]{6,}",
            r"\b(?:\d[ -]?){12,19}\b",
        )
        for pattern in patterns:
            value = re.sub(pattern, "[redacted]", value)
        return value or "Farmer requested human assistance."

    def _next_escalation_reference(self, connection: sqlite3.Connection) -> str:
        year = datetime.now(UTC).year
        prefix = f"KM-{year}-"
        row = connection.execute(
            "SELECT reference_id FROM escalations WHERE reference_id LIKE ? "
            "ORDER BY reference_id DESC LIMIT 1",
            (f"{prefix}%",),
        ).fetchone()
        sequence = int(row["reference_id"].rsplit("-", 1)[1]) + 1 if row else 1
        return f"{prefix}{sequence:04d}"

    def create_escalation(
        self,
        *,
        farmer_name: str | None,
        farmer_identifier: str | None,
        reason: str,
        problem_summary: str,
        what_agent_checked: str,
        urgency: str,
        language: str | None,
        preferred_follow_up_method: str | None,
    ) -> tuple[dict[str, Any], bool]:
        """Create an OPEN request, or return the matching open request."""
        allowed_reasons = {
            "SERIOUS_CROP_PROBLEM",
            "MARKET_DATA_UNAVAILABLE_OR_STALE",
            "OTHER",
        }
        if reason not in allowed_reasons:
            raise ValueError("Unsupported escalation reason")
        if urgency not in {"low", "medium", "high", "emergency"}:
            raise ValueError("Unsupported urgency")

        summary = self._sanitize_summary(problem_summary)
        checked = self._sanitize_summary(what_agent_checked)
        identifier = (farmer_identifier or "").strip() or None
        with self._connect() as connection:
            if identifier:
                duplicate = connection.execute(
                    "SELECT * FROM escalations WHERE farmer_identifier = ? AND reason = ? "
                    "AND problem_summary = ? AND status = 'OPEN' ORDER BY created_at DESC LIMIT 1",
                    (identifier, reason, summary),
                ).fetchone()
                if duplicate:
                    return self._escalation_dict(duplicate), True
            reference_id = self._next_escalation_reference(connection)
            record = {
                "reference_id": reference_id,
                "farmer_name": (
                    self._sanitize_summary(farmer_name)
                    if farmer_name and farmer_name.strip()
                    else None
                ),
                "farmer_identifier": identifier,
                "reason": reason,
                "problem_summary": summary,
                "what_agent_checked": checked,
                "urgency": urgency,
                "language": (language or "not specified").strip()[:40],
                "preferred_follow_up_method": (
                    preferred_follow_up_method or "not specified"
                ).strip()[:80],
                "status": "OPEN",
                "created_at": datetime.now(UTC).isoformat(),
            }
            connection.execute(
                """
                INSERT INTO escalations (
                    reference_id, farmer_name, farmer_identifier, reason,
                    problem_summary, what_agent_checked, urgency, language,
                    preferred_follow_up_method, status, created_at
                ) VALUES (
                    :reference_id, :farmer_name, :farmer_identifier, :reason,
                    :problem_summary, :what_agent_checked, :urgency, :language,
                    :preferred_follow_up_method, :status, :created_at
                )
                """,
                record,
            )
        return record, False

    @staticmethod
    def _escalation_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def list_escalations(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT reference_id, farmer_name, reason, problem_summary, "
                "what_agent_checked, urgency, language, preferred_follow_up_method, "
                "status, created_at FROM escalations "
                "ORDER BY CASE status WHEN 'OPEN' THEN 0 WHEN 'IN_PROGRESS' THEN 1 ELSE 2 END, "
                "created_at DESC"
            ).fetchall()
        return [self._escalation_dict(row) for row in rows]

    def update_escalation_status(
        self, reference_id: str, status: str
    ) -> dict[str, Any] | None:
        if status not in {"OPEN", "IN_PROGRESS", "RESOLVED"}:
            raise ValueError("Unsupported escalation status")
        with self._connect() as connection:
            connection.execute(
                "UPDATE escalations SET status = ? WHERE reference_id = ?",
                (status, reference_id),
            )
            row = connection.execute(
                "SELECT reference_id, farmer_name, reason, problem_summary, "
                "what_agent_checked, urgency, language, preferred_follow_up_method, "
                "status, created_at FROM escalations WHERE reference_id = ?",
                (reference_id,),
            ).fetchone()
        return self._escalation_dict(row) if row else None

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

    def has_outbound_opt_out(self, user_id: str) -> bool:
        """Return whether this farmer withdrew consent for future alert calls."""
        farmer = self.lookup_farmer(user_id)
        return bool((farmer or {}).get("facts", {}).get("outbound_calls_opted_out"))

    def opt_out_of_outbound_calls(self, user_id: str) -> dict[str, Any]:
        """Persist an explicit request not to receive future outbound calls."""
        return self.save_farmer_memory(
            user_id=user_id,
            name=None,
            language_preference=None,
            facts={"outbound_calls_opted_out": True},
        )

    # ------------------------------------------------------------------
    # Call analytics (Day 8)
    # ------------------------------------------------------------------

    def save_call_analytics(
        self,
        *,
        call_id: str,
        started_at: str,
        ended_at: str,
        duration_seconds: int,
        channel: str = "browser",
        outcome: str = "SUCCESS",
        turns_count: int = 0,
        user_turns: int = 0,
        tools_used: list[str] | str = "[]",
        used_search: bool = False,
        human_help_requested: bool = False,
        language: str | None = None,
        failure_reason: str | None = None,
        success_condition: str | None = None,
    ) -> dict[str, Any]:
        """Insert a call analytics record (idempotent via UNIQUE call_id)."""
        tools_json = (
            json.dumps(tools_used, ensure_ascii=False)
            if isinstance(tools_used, list)
            else str(tools_used or "[]")
        )
        record = {
            "call_id": call_id,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": max(duration_seconds, 0),
            "channel": channel,
            "outcome": outcome,
            "turns_count": max(turns_count, 0),
            "user_turns": max(user_turns, 0),
            "tools_used": tools_json,
            "used_search": 1 if used_search else 0,
            "human_help_requested": 1 if human_help_requested else 0,
            "language": language,
            "failure_reason": failure_reason,
            "success_condition": success_condition,
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO call_analytics (
                    call_id, started_at, ended_at, duration_seconds,
                    channel, outcome, turns_count, user_turns, tools_used,
                    used_search, human_help_requested, language,
                    failure_reason, success_condition, created_at
                ) VALUES (
                    :call_id, :started_at, :ended_at, :duration_seconds,
                    :channel, :outcome, :turns_count, :user_turns, :tools_used,
                    :used_search, :human_help_requested, :language,
                    :failure_reason, :success_condition, :created_at
                )
                """,
                record,
            )
        return record

    def get_analytics_summary(self) -> dict[str, Any]:
        """Return aggregated KPIs and performance metrics from call_analytics."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_calls,
                    SUM(CASE WHEN outcome IN ('SUCCESS', 'COMPLETED', 'HUMAN_HELP') THEN 1 ELSE 0 END) AS successful_calls,
                    SUM(CASE WHEN outcome = 'FAILED' THEN 1 ELSE 0 END) AS failed_calls,
                    SUM(CASE WHEN human_help_requested = 1 OR outcome = 'HUMAN_HELP' THEN 1 ELSE 0 END) AS human_help_calls,
                    SUM(CASE WHEN used_search = 1 OR (tools_used IS NOT NULL AND tools_used != '[]' AND tools_used != '') THEN 1 ELSE 0 END) AS tool_usage_calls,
                    AVG(duration_seconds) AS avg_duration_seconds,
                    AVG(turns_count) AS avg_turns,
                    AVG(user_turns) AS avg_user_turns
                FROM call_analytics
                """
            ).fetchone()

        total = row["total_calls"] or 0
        successful = row["successful_calls"] or 0
        failed = row["failed_calls"] or 0
        human_help = row["human_help_calls"] or 0
        tool_usage = row["tool_usage_calls"] or 0
        avg_dur = round(float(row["avg_duration_seconds"] or 0), 1)
        avg_turns = round(float(row["avg_turns"] or row["avg_user_turns"] or 0), 1)
        success_rate = round((successful / total) * 100, 1) if total > 0 else 0.0

        return {
            "total_calls": total,
            "successful_calls": successful,
            "failed_calls": failed,
            "human_help_calls": human_help,
            "tool_usage_calls": tool_usage,
            "avg_duration_seconds": avg_dur,
            "avg_turns": avg_turns,
            "success_rate": success_rate,
        }

    def get_recent_calls(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent call records with parsed metadata."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT call_id, started_at, ended_at, duration_seconds,
                       channel, outcome, turns_count, user_turns, tools_used,
                       used_search, human_help_requested, language,
                       failure_reason, success_condition, created_at
                FROM call_analytics
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            try:
                d["tools_used"] = json.loads(d.get("tools_used") or "[]")
            except Exception:
                d["tools_used"] = []
            results.append(d)
        return results
