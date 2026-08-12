from pathlib import Path

import database


def test_escalation_database_flow(tmp_path: Path, monkeypatch) -> None:
    """Test escalation creation, reference ID format, sanitization, duplicate protection, and status update."""
    db_path = tmp_path / "krishimitra.db"
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    # Test 1: Refusal without permission
    res_no_perm = database.create_escalation(
        farmer_name="Ramesh",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Yellow leaf rust in wheat crop.",
        permission_granted=False,
    )
    assert res_no_perm["status"] == "error"
    assert "permission is required" in res_no_perm["message"].lower()
    assert len(database.list_escalations()) == 0

    # Test 2: Valid escalation creation with permission
    res_created = database.create_escalation(
        farmer_name="Ramesh Kumar",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Leaf rust spreading fast. My OTP is 654321.",
        what_agent_checked="Checked crop type and symptoms; diagnostic confidence low.",
        urgency="high",
        language="Hindi",
        preferred_follow_up_method="Phone Call",
        permission_granted=True,
    )
    assert res_created["status"] == "success"
    ref_id = res_created["reference_id"]
    assert ref_id.startswith("KM-")
    assert "0001" in ref_id

    # Verify sensitive data sanitization (OTP redacted)
    esc_rec = database.get_escalation(ref_id)
    assert esc_rec is not None
    assert "654321" not in esc_rec["problem_summary"]
    assert "[REDACTED_CODE]" in esc_rec["problem_summary"]
    assert esc_rec["status"] == "OPEN"
    assert esc_rec["urgency"] == "high"

    # Test 3: Duplicate protection - identical request returns existing reference ID
    res_dup = database.create_escalation(
        farmer_name="Ramesh Kumar",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Leaf rust spreading fast. My OTP is 654321.",
        permission_granted=True,
    )
    assert res_dup["status"] == "success"
    assert res_dup["reference_id"] == ref_id
    assert len(database.list_escalations()) == 1

    # Test 4: Update status to IN_PROGRESS and RESOLVED
    updated = database.update_escalation_status(ref_id, "IN_PROGRESS")
    assert updated is not None
    assert updated["status"] == "IN_PROGRESS"

    updated_done = database.update_escalation_status(ref_id, "RESOLVED")
    assert updated_done is not None
    assert updated_done["status"] == "RESOLVED"
