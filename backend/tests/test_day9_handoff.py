"""Day 9 — Specialist agent and handoff unit tests."""

from agent import Assistant
from crop_specialist import CropSpecialist


def test_crop_specialist_initialization_with_context() -> None:
    context = "Farmer reports wheat leaves turning yellow with slow growth."
    specialist = CropSpecialist(
        handoff_context=context,
        farmer_memory={"name": "Ramesh", "crops_grown": "wheat"},
    )

    assert "Crop Problem Specialist" in specialist.instructions
    assert context in specialist.instructions
    assert "Ramesh" in specialist.instructions
    assert "wheat" in specialist.instructions


def test_crop_specialist_initialization_without_context() -> None:
    specialist = CropSpecialist()

    assert "Crop Problem Specialist" in specialist.instructions
    assert "FARMER'S PROBLEM CONTEXT" not in specialist.instructions


def test_crop_specialist_safety_guidelines() -> None:
    specialist = CropSpecialist()
    instructions = specialist.instructions

    # Must contain cautious diagnostic phrasing instructions
    assert (
        "This could be related to" in instructions or "possible reason" in instructions
    )
    # Must contain restriction on prescribing hazardous pesticides
    assert (
        "NEVER prescribe specific hazardous chemical pesticide" in instructions
        or "pesticide" in instructions
    )


def test_main_agent_has_handoff_tool() -> None:
    assistant = Assistant()
    # Check that handoff_to_crop_specialist is registered as a tool
    tool_names = [t.info.name for t in assistant._tools]
    assert "handoff_to_crop_specialist" in tool_names


def test_main_agent_and_specialist_have_distinct_roles() -> None:
    assistant = Assistant()
    specialist = CropSpecialist()

    assert "KrishiMitra AI" in assistant.instructions
    assert "Crop Problem Specialist" in specialist.instructions
    # Main agent has memory tools and weather tools; specialist is focused on crop health
    assert "get_weather_by_district" in [t.info.name for t in assistant._tools]
