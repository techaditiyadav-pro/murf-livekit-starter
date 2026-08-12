"""
Day 7 Human Escalation Test Suite for KrishiMitra AI.

Verifies:
- TEST A: Serious crop problem escalation path (detection -> permission -> YES -> create_escalation -> DB record + reference ID).
- TEST B: Normal conversation path (no escalation created).
- TEST C: Permission denied path (permission asked -> NO -> no escalation created).
- TEST D: Market data unavailable path (get_market_price unavailable -> permission -> YES -> escalation created).
- Privacy & sanitization (OTP, PIN, passwords, bank/card numbers redacted).
- Duplicate protection (existing OPEN escalation returned).
"""

import json

import pytest

from agent import Assistant
from database import FarmerRepository


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text_content = text
        self.content = [text]


@pytest.mark.asyncio
async def test_day7_test_a_serious_crop_problem_escalation(tmp_path) -> None:
    """TEST A: Serious crop problem triggers permission flow and creates DB escalation upon YES."""
    db_path = tmp_path / "krishimitra.db"
    repo = FarmerRepository(db_path)
    assistant = Assistant(user_id="farmer-101", repository=repo)

    user_text = "Meri gehun ki fasal mein bimari bahut tezi se fail rahi hai aur bahut saari fasal kharab ho rahi hai."
    msg = DummyMessage(user_text)

    # 1. Detect serious crop problem
    assert assistant._is_serious_crop_problem(user_text) is True
    await assistant.on_user_turn_completed(None, msg)
    assert assistant._escalation_permission_pending is True
    assert assistant._pending_escalation_reason == "SERIOUS_CROP_PROBLEM"

    # 2. Farmer grants permission ("Haan kar do")
    perm_msg = DummyMessage("Haan kar do, bhej do request")
    await assistant.on_user_turn_completed(None, perm_msg)
    assert assistant._escalation_permission_granted is True

    # 3. Create escalation tool execution
    result = await assistant.create_escalation(
        context=None,
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Wheat disease spreading rapidly. OTP: 987654 and Card: 4111 2222 3333 4444",
        what_agent_checked="Checked symptoms and crop condition. Information insufficient for safe diagnosis.",
        urgency="high",
        language="Hindi",
        preferred_follow_up_method="Phone call",
    )

    # 4. Verify output & database state
    assert "Request created successfully" in result
    assert "KM-2026-" in result

    records = repo.list_escalations()
    assert len(records) == 1
    rec = records[0]
    assert rec["reference_id"].startswith("KM-2026-")
    assert rec["reason"] == "SERIOUS_CROP_PROBLEM"
    assert rec["status"] == "OPEN"
    assert rec["urgency"] == "high"
    assert rec["language"] == "Hindi"
    assert rec["preferred_follow_up_method"] == "Phone call"
    # Sensitive data redacted
    assert "987654" not in rec["problem_summary"]
    assert "4111" not in rec["problem_summary"]


@pytest.mark.asyncio
async def test_day7_test_b_normal_conversation_no_escalation(tmp_path) -> None:
    """TEST B: Normal crop care/irrigation questions do not trigger escalation."""
    db_path = tmp_path / "krishimitra.db"
    repo = FarmerRepository(db_path)
    assistant = Assistant(user_id="farmer-102", repository=repo)

    user_text = "Mujhe gehu ki fasal mein paani kab dena chahiye?"
    msg = DummyMessage(user_text)

    # 1. Normal question check
    assert assistant._is_serious_crop_problem(user_text) is False
    await assistant.on_user_turn_completed(None, msg)

    assert assistant._escalation_permission_pending is False
    assert assistant._escalation_permission_granted is False
    assert len(repo.list_escalations()) == 0


@pytest.mark.asyncio
async def test_day7_test_c_permission_denied(tmp_path) -> None:
    """TEST C: Farmer refusing permission prevents escalation creation."""
    db_path = tmp_path / "krishimitra.db"
    repo = FarmerRepository(db_path)
    assistant = Assistant(user_id="farmer-103", repository=repo)

    user_text = "Puri fasal kharab ho rahi hai tezi se."
    msg = DummyMessage(user_text)
    await assistant.on_user_turn_completed(None, msg)
    assert assistant._escalation_permission_pending is True

    # Farmer declines permission
    decline_msg = DummyMessage("Nahi, request mat bhejna")
    await assistant.on_user_turn_completed(None, decline_msg)

    assert assistant._escalation_permission_pending is False
    assert assistant._escalation_permission_granted is False

    # Attempting to call tool directly without permission fails
    fail_res = await assistant.create_escalation(
        context=None,
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Crop damage",
        what_agent_checked="Checked symptoms",
    )
    assert "Permission has not been confirmed" in fail_res
    assert len(repo.list_escalations()) == 0


@pytest.mark.asyncio
async def test_day7_test_d_market_data_unavailable(tmp_path) -> None:
    """TEST D: Missing/stale market data offers human help, requires permission, sets urgency medium."""
    db_path = tmp_path / "krishimitra.db"
    repo = FarmerRepository(db_path)
    assistant = Assistant(user_id="farmer-104", repository=repo)

    # 1. Market tool returns unavailable result without guessing price
    mkt_res_str = await assistant.get_market_price(None, crop="gehu", mandi="Indore")
    mkt_res = json.loads(mkt_res_str)
    assert mkt_res["status"] == "unavailable"
    assert assistant._escalation_permission_pending is True
    assert assistant._pending_escalation_reason == "MARKET_DATA_UNAVAILABLE_OR_STALE"

    # 2. Farmer grants permission
    perm_msg = DummyMessage("Haan expert se baat karayein")
    await assistant.on_user_turn_completed(None, perm_msg)
    assert assistant._escalation_permission_granted is True

    # 3. Escalation tool created
    res = await assistant.create_escalation(
        context=None,
        reason="MARKET_DATA_UNAVAILABLE_OR_STALE",
        problem_summary="Requested wheat mandi price for Indore. Data unavailable.",
        what_agent_checked="Checked MarketDataClient provider.",
        urgency="medium",
        language="Hindi",
        preferred_follow_up_method="SMS",
    )
    assert "Request created successfully" in res

    records = repo.list_escalations()
    assert len(records) == 1
    assert records[0]["reason"] == "MARKET_DATA_UNAVAILABLE_OR_STALE"
    assert records[0]["urgency"] == "medium"


@pytest.mark.asyncio
async def test_day7_duplicate_protection(tmp_path) -> None:
    """Duplicate escalation requests for the same open issue return existing reference ID."""
    db_path = tmp_path / "krishimitra.db"
    repo = FarmerRepository(db_path)

    r1, dup1 = repo.create_escalation(
        farmer_name="Ramesh",
        farmer_identifier="farmer-999",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Pest infestation in cotton crop.",
        what_agent_checked="Asked symptoms.",
        urgency="high",
        language="Hindi",
        preferred_follow_up_method="Call",
    )
    assert dup1 is False

    r2, dup2 = repo.create_escalation(
        farmer_name="Ramesh",
        farmer_identifier="farmer-999",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Pest infestation in cotton crop.",
        what_agent_checked="Asked symptoms.",
        urgency="high",
        language="Hindi",
        preferred_follow_up_method="Call",
    )
    assert dup2 is True
    assert r1["reference_id"] == r2["reference_id"]
    assert len(repo.list_escalations()) == 1
