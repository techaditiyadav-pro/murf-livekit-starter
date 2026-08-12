from database import FarmerRepository


def test_escalation_is_sanitized_and_duplicate_safe(tmp_path) -> None:
    repository = FarmerRepository(tmp_path / "krishimitra.db")
    request, duplicate = repository.create_escalation(
        farmer_name="Ramesh",
        farmer_identifier="farmer-1",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Wheat disease is spreading. OTP: 123456 and card 4111 1111 1111 1111",
        what_agent_checked="Asked crop, symptoms, and severity.",
        urgency="high",
        language="Hindi",
        preferred_follow_up_method="Phone call",
    )

    again, is_duplicate = repository.create_escalation(
        farmer_name="Ramesh",
        farmer_identifier="farmer-1",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Wheat disease is spreading. OTP: 123456 and card 4111 1111 1111 1111",
        what_agent_checked="Asked crop, symptoms, and severity.",
        urgency="high",
        language="Hindi",
        preferred_follow_up_method="Phone call",
    )

    assert duplicate is False
    assert is_duplicate is True
    assert again["reference_id"] == request["reference_id"]
    assert request["reference_id"].startswith("KM-")
    assert "123456" not in request["problem_summary"]
    assert "4111" not in request["problem_summary"]
    assert repository.list_escalations()[0]["status"] == "OPEN"


def test_escalation_status_can_be_updated(tmp_path) -> None:
    repository = FarmerRepository(tmp_path / "krishimitra.db")
    request, _ = repository.create_escalation(
        farmer_name=None,
        farmer_identifier=None,
        reason="MARKET_DATA_UNAVAILABLE_OR_STALE",
        problem_summary="Verified mandi data is unavailable for wheat.",
        what_agent_checked="Checked verified market source.",
        urgency="medium",
        language=None,
        preferred_follow_up_method=None,
    )
    updated = repository.update_escalation_status(
        request["reference_id"], "IN_PROGRESS"
    )
    assert updated is not None
    assert updated["status"] == "IN_PROGRESS"
