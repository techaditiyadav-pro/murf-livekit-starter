import json
import time
import urllib.request

from database import FarmerRepository
from escalation_api import EscalationHandler, start_escalation_api


def test_escalation_api_endpoints(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "krishimitra.db"
    repo = FarmerRepository(db_path)

    # Seed an escalation
    record, _ = repo.create_escalation(
        farmer_name="Ramesh",
        farmer_identifier="farmer-api-test",
        reason="SERIOUS_CROP_PROBLEM",
        problem_summary="Rapid leaf disease spread in wheat.",
        what_agent_checked="Checked symptoms.",
        urgency="high",
        language="Hindi",
        preferred_follow_up_method="Phone call",
    )
    ref_id = record["reference_id"]

    monkeypatch.setenv("ESCALATION_API_PORT", "8999")
    monkeypatch.setattr(EscalationHandler, "repository", repo)

    start_escalation_api()
    time.sleep(0.5)

    # 1. GET /api/escalations
    req = urllib.request.Request("http://127.0.0.1:8999/api/escalations")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "escalations" in data
        assert len(data["escalations"]) >= 1
        assert data["escalations"][0]["reference_id"] == ref_id

    # 2. PATCH /api/escalations/{ref_id}
    patch_data = json.dumps({"status": "IN_PROGRESS"}).encode("utf-8")
    patch_req = urllib.request.Request(
        f"http://127.0.0.1:8999/api/escalations/{ref_id}",
        data=patch_data,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(patch_req) as resp:
        assert resp.status == 200
        updated = json.loads(resp.read().decode("utf-8"))
        assert updated["status"] == "IN_PROGRESS"

    assert repo.list_escalations()[0]["status"] == "IN_PROGRESS"

    # 3. POST /api/escalations
    post_payload = json.dumps(
        {
            "farmer_name": "Suresh",
            "reason": "OTHER",
            "problem_summary": "Need help with soil testing.",
            "urgency": "medium",
            "language": "Hindi",
            "preferred_follow_up_method": "Phone Call",
        }
    ).encode("utf-8")
    post_req = urllib.request.Request(
        "http://127.0.0.1:8999/api/escalations",
        data=post_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(post_req) as resp:
        assert resp.status == 201
        created = json.loads(resp.read().decode("utf-8"))
        assert created["farmer_name"] == "Suresh"
        assert created["reference_id"].startswith("KM-2026-")
        assert created["reason"] == "OTHER"
        assert created["what_agent_checked"] == "User requested human support directly."

