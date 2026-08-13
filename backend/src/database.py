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
    """Open the on-disk database and ensure its schemas exist."""
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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS farm_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_name TEXT NOT NULL,
            sip_destination TEXT NOT NULL,
            village TEXT NOT NULL,
            crop TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            alert_reason TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            verification_question TEXT NOT NULL,
            verification_answer TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            call_attempts INTEGER DEFAULT 0,
            last_call_outcome TEXT DEFAULT ''
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_id TEXT UNIQUE NOT NULL,
            farmer_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            problem_summary TEXT NOT NULL,
            what_agent_checked TEXT NOT NULL,
            urgency TEXT NOT NULL,
            language TEXT NOT NULL,
            preferred_follow_up_method TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS call_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT UNIQUE NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            channel TEXT NOT NULL DEFAULT 'browser',
            outcome TEXT NOT NULL,
            failure_reason TEXT DEFAULT '',
            success_condition TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    _seed_farm_alerts_if_empty(connection)
    return connection


def _seed_farm_alerts_if_empty(connection: sqlite3.Connection) -> None:
    """Seed initial demo farm alerts if none exist."""
    count = connection.execute("SELECT COUNT(*) FROM farm_alerts").fetchone()[0]
    if count > 0:
        return

    import os

    default_sip_uri = os.getenv(
        "LINPHONE_SIP_URI",
        f"sip:demo@{os.getenv('SIP_OUTBOUND_HOST', 'sip.linphone.org')}",
    )
    now = datetime.now(UTC).isoformat()
    demo_alerts = [
        (
            1,
            "Ramesh Kumar",
            default_sip_uri,
            "Rampur",
            "Wheat",
            "Leaf Rust Disease Risk",
            "High humidity and temperature fluctuation in your zone increase yellow leaf rust fungal risk.",
            "Inspect leaf surfaces for yellow/orange powdery spots and apply recommended bio-fungicide if spots are seen.",
            "Kripya confirm kijiye, kya aapki main crop Wheat (Gehun) hai?",
            "wheat,gehun,yes,haan,ji,sahi hai",
            "pending",
            "Demo alert created for Scenario 1 (Verified + Acknowledged)",
            now,
            now,
            0,
            "Not called yet",
        ),
        (
            2,
            "Suresh Patel",
            default_sip_uri,
            "Kishanganj",
            "Soybean",
            "Stem Borer Pest Warning",
            "Recent rainfall and humidity have triggered stem borer pest activity in neighboring fields.",
            "Check stems for tiny entry holes or wilting shoots. Install pheromone traps if necessary.",
            "Kripya confirm kijiye, kya aapki main crop Soybean hai?",
            "soybean,yes,haan,ji,sahi hai",
            "pending",
            "Demo alert created for Scenario 2 (Verified + Issue Not Observed)",
            now,
            now,
            0,
            "Not called yet",
        ),
        (
            3,
            "Mahesh Verma",
            default_sip_uri,
            "Sonpur",
            "Rice",
            "Irrigation Requirement Reminder",
            "A dry spell is predicted over the next 4 days during critical grain filling stage.",
            "Maintain 2-3 cm standing water in paddy fields to prevent soil drying and yield drop.",
            "Kripya confirm kijiye, kya aapki main crop Rice (Paddy) hai?",
            "rice,chawal,paddy,yes,haan,ji,sahi hai",
            "pending",
            "Demo alert created for Scenario 3 (Verification Failure)",
            now,
            now,
            0,
            "Not called yet",
        ),
    ]

    connection.executemany(
        """
        INSERT INTO farm_alerts (
            id, farmer_name, sip_destination, village, crop, alert_type, alert_reason,
            recommended_action, verification_question, verification_answer, status, notes,
            created_at, updated_at, call_attempts, last_call_outcome
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        demo_alerts,
    )
    connection.commit()


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


def get_farm_alert(alert_id: int) -> dict[str, Any] | None:
    """Retrieve a single farm alert by ID."""
    try:
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM farm_alerts WHERE id = ?", (alert_id,)
            ).fetchone()
            if row:
                return dict(row)
    except sqlite3.Error:
        logger.exception("Unable to look up farm alert %s", alert_id)
        raise
    return None


def get_pending_alert_by_farmer(farmer_identifier: str) -> dict[str, Any] | None:
    """Retrieve the latest alert for a farmer by name or SIP destination."""
    try:
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT * FROM farm_alerts
                WHERE farmer_name LIKE ? OR sip_destination LIKE ?
                ORDER BY id ASC LIMIT 1
                """,
                (f"%{farmer_identifier}%", f"%{farmer_identifier}%"),
            ).fetchone()
            if row:
                return dict(row)
    except sqlite3.Error:
        logger.exception("Unable to look up farm alert for %s", farmer_identifier)
        raise
    return None


def list_farm_alerts() -> list[dict[str, Any]]:
    """List all farm alert records in the database."""
    try:
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM farm_alerts ORDER BY id ASC"
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Unable to list farm alerts")
        return []


def update_farm_alert(
    alert_id: int,
    status: str,
    notes: str = "",
    last_call_outcome: str = "",
) -> dict[str, Any] | None:
    """Update farm alert status, notes, last call outcome, and timestamp."""
    now = datetime.now(UTC).isoformat()
    try:
        with _connection() as connection:
            connection.execute(
                """
                UPDATE farm_alerts
                SET status = ?,
                    notes = ?,
                    last_call_outcome = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    notes,
                    last_call_outcome or f"Call outcome: {status}",
                    now,
                    alert_id,
                ),
            )
            connection.commit()
    except sqlite3.Error:
        logger.exception("Unable to update farm alert %s", alert_id)
        raise
    return get_farm_alert(alert_id)


def record_call_attempt(alert_id: int, outcome: str = "Initiating dial") -> None:
    """Increment call attempts counter and update call outcome timestamp."""
    now = datetime.now(UTC).isoformat()
    try:
        with _connection() as connection:
            connection.execute(
                """
                UPDATE farm_alerts
                SET call_attempts = call_attempts + 1,
                    last_call_outcome = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (outcome, now, alert_id),
            )
            connection.commit()
    except sqlite3.Error:
        logger.exception("Unable to record call attempt for alert %s", alert_id)


def sanitize_text(text: str) -> str:
    """Sanitize user inputs to mask sensitive information such as OTPs, PINs, bank details."""
    import re

    if not text:
        return ""
    # Mask 4-8 digit numbers that look like OTPs / PINs / account numbers
    sanitized = re.sub(r"\b\d{4,8}\b", "[REDACTED_CODE]", text)
    # Mask card numbers (13-19 digits)
    sanitized = re.sub(r"\b\d{13,19}\b", "[REDACTED_CARD]", sanitized)
    # Mask common sensitive phrases
    sensitive_keywords = ["password", "otp", "pin", "cvv", "bank account"]
    for kw in sensitive_keywords:
        pattern = re.compile(rf"\b{kw}\b\s*[:=]?\s*\S+", re.IGNORECASE)
        sanitized = pattern.sub(f"{kw}: [REDACTED]", sanitized)
    return sanitized.strip()


def create_escalation(
    farmer_name: str,
    reason: str,
    problem_summary: str,
    what_agent_checked: str = "User requested human support directly.",
    urgency: str = "medium",
    language: str = "Hindi",
    preferred_follow_up_method: str = "Phone Call",
    permission_granted: bool = True,
) -> dict[str, Any]:
    """Create a new human help escalation record in SQLite with unique reference ID.

    Requires explicit permission_granted = True. Prevents duplicate OPEN requests.
    """
    if not permission_granted:
        return {
            "status": "error",
            "message": "Your request was not submitted because permission is required.",
        }

    cleaned_name = farmer_name.strip() if farmer_name else "Farmer"
    cleaned_reason = reason.strip() if reason else "OTHER"
    cleaned_summary = sanitize_text(problem_summary)
    cleaned_checked = sanitize_text(
        what_agent_checked or "User requested human support directly."
    )
    cleaned_urgency = urgency.lower() if urgency else "medium"
    if cleaned_urgency not in {"low", "medium", "high", "emergency"}:
        cleaned_urgency = "medium"

    valid_reasons = {
        "SERIOUS_CROP_PROBLEM",
        "MARKET_DATA_UNAVAILABLE_OR_STALE",
        "OTHER",
    }
    if cleaned_reason not in valid_reasons:
        cleaned_reason = "OTHER"

    now = datetime.now(UTC).isoformat()
    current_year = datetime.now(UTC).year

    try:
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            # Check for existing duplicate OPEN request
            existing = connection.execute(
                """
                SELECT * FROM escalations
                WHERE farmer_name = ? AND reason = ? AND problem_summary = ? AND status = 'OPEN'
                LIMIT 1
                """,
                (cleaned_name, cleaned_reason, cleaned_summary),
            ).fetchone()

            if existing:
                rec = dict(existing)
                rec["is_duplicate"] = True
                return {
                    "status": "success",
                    "escalation": rec,
                    "reference_id": rec["reference_id"],
                }

            # Generate next sequence number for reference ID
            count_row = connection.execute(
                "SELECT COUNT(*) FROM escalations WHERE reference_id LIKE ?",
                (f"KM-{current_year}-%",),
            ).fetchone()
            seq = (count_row[0] if count_row else 0) + 1
            reference_id = f"KM-{current_year}-{seq:04d}"

            connection.execute(
                """
                INSERT INTO escalations (
                    reference_id, farmer_name, reason, problem_summary,
                    what_agent_checked, urgency, language, preferred_follow_up_method,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
                """,
                (
                    reference_id,
                    cleaned_name,
                    cleaned_reason,
                    cleaned_summary,
                    cleaned_checked,
                    cleaned_urgency,
                    language or "Hindi",
                    preferred_follow_up_method or "Phone Call",
                    now,
                    now,
                ),
            )
            connection.commit()

            created = connection.execute(
                "SELECT * FROM escalations WHERE reference_id = ?", (reference_id,)
            ).fetchone()
            rec = dict(created)
            return {
                "status": "success",
                "escalation": rec,
                "reference_id": reference_id,
            }

    except sqlite3.Error as err:
        logger.exception("Failed to create escalation record")
        return {
            "status": "error",
            "message": f"Database error creating escalation: {err}",
        }


def list_escalations() -> list[dict[str, Any]]:
    """List all escalation records ordered by creation date descending."""
    try:
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM escalations ORDER BY id DESC"
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Unable to list escalations")
        return []


def get_escalation(reference_id: str) -> dict[str, Any] | None:
    """Retrieve a single escalation record by reference ID."""
    try:
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM escalations WHERE reference_id = ?", (reference_id,)
            ).fetchone()
            if row:
                return dict(row)
    except sqlite3.Error:
        logger.exception("Unable to look up escalation %s", reference_id)
    return None


def update_escalation_status(reference_id: str, status: str) -> dict[str, Any] | None:
    """Update status of an escalation record (OPEN, IN_PROGRESS, RESOLVED)."""
    valid_statuses = {"OPEN", "IN_PROGRESS", "RESOLVED"}
    cleaned_status = status.upper()
    if cleaned_status not in valid_statuses:
        return None

    now = datetime.now(UTC).isoformat()
    try:
        with _connection() as connection:
            connection.execute(
                """
                UPDATE escalations
                SET status = ?, updated_at = ?
                WHERE reference_id = ?
                """,
                (cleaned_status, now, reference_id),
            )
            connection.commit()
    except sqlite3.Error:
        logger.exception("Unable to update escalation %s", reference_id)
        return None
    return get_escalation(reference_id)


def record_call_analytics(
    call_id: str,
    started_at: str,
    ended_at: str,
    duration_seconds: int,
    channel: str,
    outcome: str,
    failure_reason: str = "",
    success_condition: str = "",
) -> dict[str, Any]:
    """Record a completed call outcome (SUCCESS or FAILED) into call_analytics table."""
    now = datetime.now(UTC).isoformat()
    cleaned_outcome = outcome.upper()
    if cleaned_outcome not in {"SUCCESS", "FAILED"}:
        cleaned_outcome = "FAILED"

    cleaned_channel = channel.lower() if channel else "browser"
    if cleaned_channel not in {"browser", "sip"}:
        cleaned_channel = "browser"

    cleaned_reason = sanitize_text(failure_reason or "")
    cleaned_condition = sanitize_text(success_condition or "")

    try:
        with _connection() as connection:
            connection.execute(
                """
                INSERT INTO call_analytics (
                    call_id, started_at, ended_at, duration_seconds,
                    channel, outcome, failure_reason, success_condition, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(call_id) DO UPDATE SET
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    duration_seconds = excluded.duration_seconds,
                    channel = excluded.channel,
                    outcome = excluded.outcome,
                    failure_reason = excluded.failure_reason,
                    success_condition = excluded.success_condition
                """,
                (
                    call_id,
                    started_at,
                    ended_at,
                    max(0, duration_seconds),
                    cleaned_channel,
                    cleaned_outcome,
                    cleaned_reason,
                    cleaned_condition,
                    now,
                ),
            )
            connection.commit()

            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM call_analytics WHERE call_id = ?", (call_id,)
            ).fetchone()
            return dict(row) if row else {}
    except sqlite3.Error:
        logger.exception("Unable to record call analytics for call_id=%s", call_id)
        return {}


def list_call_analytics(limit: int = 50) -> list[dict[str, Any]]:
    """List recent call analytics records."""
    try:
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM call_analytics ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error:
        logger.exception("Unable to list call analytics")
        return []


def get_analytics_summary() -> dict[str, Any]:
    """Calculate summary statistics dynamically from call_analytics database."""
    try:
        with _connection() as connection:
            total_calls = connection.execute(
                "SELECT COUNT(*) FROM call_analytics"
            ).fetchone()[0]
            successful_calls = connection.execute(
                "SELECT COUNT(*) FROM call_analytics WHERE outcome = 'SUCCESS'"
            ).fetchone()[0]
            failed_calls = connection.execute(
                "SELECT COUNT(*) FROM call_analytics WHERE outcome = 'FAILED'"
            ).fetchone()[0]

            recent = list_call_analytics(limit=20)
            success_rate = (
                round((successful_calls / total_calls) * 100, 1)
                if total_calls > 0
                else 0.0
            )

            return {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "success_rate": success_rate,
                "recent_calls": recent,
            }
    except sqlite3.Error:
        logger.exception("Unable to get analytics summary")
        return {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "success_rate": 0.0,
            "recent_calls": [],
        }

