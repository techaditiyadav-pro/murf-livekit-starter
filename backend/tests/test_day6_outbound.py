"""Tests for Day 6 Outbound Farm Alert Voice Agent features."""

from pathlib import Path

import pytest

import database
from agent import Assistant


@pytest.fixture(autouse=True)
def isolated_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate database to a temporary directory for tests."""
    test_db_path = tmp_path / "krishimitra_test.db"
    monkeypatch.setattr(database, "DATABASE_PATH", test_db_path)


def test_farm_alerts_initial_seeding() -> None:
    """Verify that demo farm alerts are seeded on database initialization."""
    alerts = database.list_farm_alerts()
    assert len(alerts) == 3

    ramesh = alerts[0]
    assert ramesh["id"] == 1
    assert ramesh["farmer_name"] == "Ramesh Kumar"
    assert ramesh["crop"] == "Wheat"
    assert ramesh["status"] == "pending"
    assert "Wheat" in ramesh["verification_question"]

    suresh = alerts[1]
    assert suresh["id"] == 2
    assert suresh["farmer_name"] == "Suresh Patel"
    assert suresh["crop"] == "Soybean"

    mahesh = alerts[2]
    assert mahesh["id"] == 3
    assert mahesh["farmer_name"] == "Mahesh Verma"
    assert mahesh["crop"] == "Rice"


def test_farm_alert_crud_and_status_update() -> None:
    """Verify loading and updating alert status in SQLite database."""
    alert = database.get_farm_alert(1)
    assert alert is not None
    assert alert["status"] == "pending"

    # Test status update
    updated = database.update_farm_alert(
        alert_id=1,
        status="confirmed",
        notes="Farmer Ramesh confirmed observing yellow spots on wheat leaves",
        last_call_outcome="Call completed successfully",
    )
    assert updated is not None
    assert updated["status"] == "confirmed"
    assert (
        updated["notes"]
        == "Farmer Ramesh confirmed observing yellow spots on wheat leaves"
    )
    assert updated["last_call_outcome"] == "Call completed successfully"


@pytest.mark.asyncio
async def test_assistant_load_farm_alert_tool() -> None:
    """Verify Assistant load_farm_alert function tool returns structured data."""
    assistant = Assistant(user_id="ramesh_123", alert_id=1, is_outbound=True)
    res = await assistant.load_farm_alert(context=None, alert_id=1)

    assert res["status"] == "success"
    alert_info = res["alert"]
    assert alert_info["farmer_name"] == "Ramesh Kumar"
    assert alert_info["crop"] == "Wheat"
    assert "verification_question" in alert_info


@pytest.mark.asyncio
async def test_assistant_verify_farmer_success_and_failure() -> None:
    """Verify non-sensitive farmer verification logic and max 2 attempts enforcement."""
    assistant = Assistant(user_id="test_farmer", alert_id=1, is_outbound=True)
    await assistant.load_farm_alert(context=None, alert_id=1)

    # Attempt 1: Incorrect answer
    res1 = await assistant.verify_farmer(
        context=None, farmer_id="test_farmer", verification_answer="Cotton"
    )
    assert res1["status"] == "incorrect"
    assert res1["attempts_made"] == 1
    assert res1["attempts_remaining"] == 1

    # Attempt 2: Correct answer ("Wheat")
    res2 = await assistant.verify_farmer(
        context=None, farmer_id="test_farmer", verification_answer="Gehun"
    )
    assert res2["status"] == "verified"
    assert assistant.verification_passed is True

    # Test Failure after 2 incorrect attempts on another instance
    assistant_failed = Assistant(user_id="test_farmer_2", alert_id=3, is_outbound=True)
    await assistant_failed.load_farm_alert(context=None, alert_id=3)

    fail1 = await assistant_failed.verify_farmer(
        context=None, farmer_id="test_farmer_2", verification_answer="Cotton"
    )
    assert fail1["status"] == "incorrect"

    fail2 = await assistant_failed.verify_farmer(
        context=None, farmer_id="test_farmer_2", verification_answer="Sugarcane"
    )
    assert fail2["status"] == "failed"
    assert assistant_failed.verification_failed is True

    # Verify DB status updated to verification_failed
    db_alert = database.get_farm_alert(3)
    assert db_alert["status"] == "verification_failed"


@pytest.mark.asyncio
async def test_assistant_update_farm_alert_status_tool() -> None:
    """Verify update_farm_alert_status tool updates DB and Day 4 memory."""
    assistant = Assistant(user_id="test_farmer", alert_id=2, is_outbound=True)
    await assistant.load_farm_alert(context=None, alert_id=2)

    res = await assistant.update_farm_alert_status(
        context=None,
        status="not_observed",
        notes="Farmer Suresh checked soybean crop and did not find stem borer holes",
        alert_id=2,
    )
    assert res["status"] == "updated"
    assert res["record"]["status"] == "not_observed"

    # Verify Day 4 memory profile was also updated
    profile = database.lookup_farmer("test_farmer")
    assert profile is not None
    assert profile["facts"]["last_alert_status"] == "not_observed"
