import pytest

import agent
from agent import Assistant


@pytest.mark.asyncio
async def test_memory_tool_does_not_write_without_permission(monkeypatch) -> None:
    """A refusal cannot reach SQLite through the memory tool."""
    saved_profiles: list[dict[str, object]] = []

    def record_save(*args, **kwargs):
        saved_profiles.append({"args": args, "kwargs": kwargs})
        return {"user_id": "farmer_123"}

    monkeypatch.setattr(agent, "save_farmer_memory_record", record_save)
    assistant = Assistant(user_id="farmer_123")

    result = await assistant.save_user_memory._func(
        assistant,
        None,
        name="Ramesh",
        facts={"crops_grown": "cotton"},
    )

    assert result["status"] == "consent_required"
    assert saved_profiles == []


@pytest.mark.asyncio
async def test_memory_tool_writes_after_permission(monkeypatch) -> None:
    """An explicit affirmative permission enables a single memory write."""
    saved_profiles: list[dict[str, object]] = []

    def record_save(user_id, name, language_preference, facts):
        profile = {
            "user_id": user_id,
            "name": name,
            "language_preference": language_preference,
            "facts": facts,
        }
        saved_profiles.append(profile)
        return profile

    monkeypatch.setattr(agent, "save_farmer_memory_record", record_save)
    assistant = Assistant(user_id="farmer_123")

    result = await assistant.save_user_memory._func(
        assistant,
        None,
        name="Ramesh",
        facts={"crops_grown": "cotton"},
        permission_granted=True,
    )

    assert result["status"] == "saved"
    assert saved_profiles == [
        {
            "user_id": "farmer_123",
            "name": "Ramesh",
            "language_preference": None,
            "facts": {"crops_grown": "cotton"},
        }
    ]
