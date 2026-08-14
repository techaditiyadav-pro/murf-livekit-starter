import importlib
from pathlib import Path

import pytest

import database
from agent import Assistant


def test_call_analytics_storage_and_summary(tmp_path: Path, monkeypatch) -> None:
    """Test recording call outcomes into SQLite database and querying summary metrics."""
    database_path = tmp_path / "krishimitra.db"
    monkeypatch.setattr(database, "DATABASE_PATH", database_path)

    restarted_db = importlib.reload(database)
    monkeypatch.setattr(restarted_db, "DATABASE_PATH", database_path)

    # Initial state should be empty
    summary = restarted_db.get_analytics_summary()
    assert summary["total_calls"] == 0
    assert summary["successful_calls"] == 0
    assert summary["failed_calls"] == 0
    assert summary["success_rate"] == 0.0
    assert summary["avg_duration_seconds"] == 0.0
    assert summary["avg_turns"] == 0.0
    assert summary["human_help_count"] == 0

    # Record a successful call
    call1 = restarted_db.record_call_analytics(
        call_id="call-001",
        started_at="2026-08-13T10:00:00Z",
        ended_at="2026-08-13T10:02:30Z",
        duration_seconds=150,
        channel="browser",
        outcome="SUCCESS",
        success_condition="Weather information provided for Bhopal",
        turns_count=4,
        tools_used="weather_data",
        human_help_requested=False,
    )
    assert call1["outcome"] == "SUCCESS"
    assert call1["channel"] == "browser"
    assert call1["turns_count"] == 4
    assert call1["tools_used"] == "weather_data"

    # Record a failed call with human help request
    call2 = restarted_db.record_call_analytics(
        call_id="call-002",
        started_at="2026-08-13T10:10:00Z",
        ended_at="2026-08-13T10:10:30Z",
        duration_seconds=30,
        channel="sip",
        outcome="FAILED",
        failure_reason="Caller requested escalation",
        turns_count=2,
        tools_used="create_escalation",
        human_help_requested=True,
    )
    assert call2["outcome"] == "FAILED"
    assert call2["channel"] == "sip"

    # Check updated summary
    updated = restarted_db.get_analytics_summary()
    assert updated["total_calls"] == 2
    assert updated["successful_calls"] == 1
    assert updated["failed_calls"] == 1
    assert (
        updated["total_calls"] == updated["successful_calls"] + updated["failed_calls"]
    )
    assert updated["success_rate"] == 50.0
    assert updated["avg_duration_seconds"] == 90.0
    assert updated["avg_turns"] == 3.0
    assert updated["human_help_count"] == 1


@pytest.mark.asyncio
async def test_assistant_success_condition_tracking() -> None:
    """Test that Assistant class tracks success conditions correctly when tools are executed."""
    assistant = Assistant(user_id="test_farmer")

    # Initial state: unfulfilled
    assert not assistant.success_condition_met

    # Executing weather query sets success_condition_met and records tool usage
    res = await assistant.get_weather_info(None, "Bhopal")
    assert res["status"] == "success"
    assert assistant.success_condition_met
    assert "Bhopal" in assistant.success_condition_description

    # Reset assistant for query answering
    assistant2 = Assistant(user_id="test_farmer_2")
    assert not assistant2.success_condition_met
    await assistant2.mark_query_answered(None, "Wheat irrigation schedule")
    assert assistant2.success_condition_met
    assert "Wheat irrigation schedule" in assistant2.success_condition_description
