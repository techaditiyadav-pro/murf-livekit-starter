"""Day 8 — Call Analytics unit tests."""

from pathlib import Path

from database import FarmerRepository


def test_call_analytics_storage_and_kpis(tmp_path: Path) -> None:
    db_path = tmp_path / "test_krishimitra.db"
    repo = FarmerRepository(db_path)

    # Empty state check
    empty_summary = repo.get_analytics_summary()
    assert empty_summary["total_calls"] == 0
    assert empty_summary["successful_calls"] == 0
    assert empty_summary["failed_calls"] == 0
    assert empty_summary["success_rate"] == 0.0
    assert repo.get_recent_calls() == []

    # Record 1: Successful weather query call with tool usage
    repo.save_call_analytics(
        call_id="call-001",
        started_at="2026-08-14T10:00:00Z",
        ended_at="2026-08-14T10:01:30Z",
        duration_seconds=90,
        channel="browser",
        outcome="SUCCESS",
        turns_count=4,
        user_turns=2,
        tools_used=["get_weather_by_district"],
        used_search=True,
        human_help_requested=False,
        language="hi",
        success_condition="Weather data provided",
    )

    # Record 2: Call with human-help escalation
    repo.save_call_analytics(
        call_id="call-002",
        started_at="2026-08-14T10:05:00Z",
        ended_at="2026-08-14T10:07:00Z",
        duration_seconds=120,
        channel="browser",
        outcome="HUMAN_HELP",
        turns_count=6,
        user_turns=3,
        tools_used=["create_escalation"],
        used_search=False,
        human_help_requested=True,
        language="en",
        success_condition="Human escalation created",
    )

    # Record 3: Failed call (disconnected immediately)
    repo.save_call_analytics(
        call_id="call-003",
        started_at="2026-08-14T10:10:00Z",
        ended_at="2026-08-14T10:10:10Z",
        duration_seconds=10,
        channel="browser",
        outcome="FAILED",
        turns_count=0,
        user_turns=0,
        tools_used=[],
        used_search=False,
        human_help_requested=False,
        failure_reason="User disconnected immediately",
    )

    # Test summary KPIs
    summary = repo.get_analytics_summary()
    assert summary["total_calls"] == 3
    assert (
        summary["successful_calls"] == 2
    )  # SUCCESS + HUMAN_HELP count as successful interactions
    assert summary["failed_calls"] == 1
    assert summary["human_help_calls"] == 1
    assert (
        summary["tool_usage_calls"] == 2
    )  # call-001 (search) and call-002 (tools_used)
    assert summary["success_rate"] == 66.7
    assert summary["avg_duration_seconds"] == round((90 + 120 + 10) / 3, 1)

    # Test recent calls retrieval
    recent = repo.get_recent_calls()
    assert len(recent) == 3
    # Check that tools_used is parsed back into a list
    c1 = next(c for c in recent if c["call_id"] == "call-001")
    assert c1["tools_used"] == ["get_weather_by_district"]
    assert c1["used_search"] == 1
    assert c1["outcome"] == "SUCCESS"


def test_call_analytics_idempotence(tmp_path: Path) -> None:
    db_path = tmp_path / "test_krishimitra.db"
    repo = FarmerRepository(db_path)

    repo.save_call_analytics(
        call_id="call-dup",
        started_at="2026-08-14T10:00:00Z",
        ended_at="2026-08-14T10:00:30Z",
        duration_seconds=30,
        outcome="SUCCESS",
    )

    # Re-inserting the same call_id should not duplicate or crash (INSERT OR IGNORE)
    repo.save_call_analytics(
        call_id="call-dup",
        started_at="2026-08-14T10:00:00Z",
        ended_at="2026-08-14T10:00:30Z",
        duration_seconds=30,
        outcome="SUCCESS",
    )

    summary = repo.get_analytics_summary()
    assert summary["total_calls"] == 1
