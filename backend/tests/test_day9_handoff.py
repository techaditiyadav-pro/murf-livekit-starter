import pytest
from livekit.agents import AgentSession, inference, llm
from livekit.agents.voice.run_result import AgentHandoffEvent, FunctionCallEvent

from agent import Assistant
from specialist import CropProblemSpecialist


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4o-mini")


@pytest.mark.asyncio
async def test_normal_question_no_handoff() -> None:
    """TEST 1: Normal farming question should be answered by Main Agent without handoff."""
    async with (
        _llm() as llm,
        AgentSession(llm=llm) as session,
    ):
        assistant = Assistant(user_id="test-farmer-1")
        await session.start(assistant)

        result = await session.run(user_input="What is the best time to sow wheat?")

        has_messages = False
        while True:
            try:
                ev_assert = result.expect.next_event()
                ev = ev_assert.event()
                if getattr(getattr(ev, "item", None), "role", None) == "assistant":
                    has_messages = True
            except AssertionError:
                break

        assert has_messages, "No assistant response received for normal question"
        assert isinstance(session.current_agent, Assistant), (
            "Agent should remain Assistant"
        )


@pytest.mark.asyncio
async def test_specialist_question_triggers_handoff() -> None:
    """TEST 2: Crop disease/pest question triggers handoff to CropProblemSpecialist with context."""
    async with (
        _llm() as llm,
        AgentSession(llm=llm) as session,
    ):
        assistant = Assistant(user_id="test-farmer-2")
        await session.start(assistant)

        result = await session.run(
            user_input="My wheat crop leaves are turning yellow and I see small insects on them. What should I do?"
        )

        tool_called = False
        handoff_occurred = False

        while True:
            try:
                ev_assert = result.expect.next_event()
                ev = ev_assert.event()
                if (
                    isinstance(ev, FunctionCallEvent)
                    and ev.item.name == "handoff_to_crop_specialist"
                ):
                    tool_called = True
                elif isinstance(ev, AgentHandoffEvent):
                    handoff_occurred = True
            except AssertionError:
                break

        assert tool_called, "handoff_to_crop_specialist tool should be called"
        assert handoff_occurred, "AgentHandoffEvent should occur"
        assert isinstance(session.current_agent, CropProblemSpecialist), (
            "Session active agent should be CropProblemSpecialist"
        )
        assert session.current_agent.problem_context != "", (
            "Specialist should receive problem context"
        )


@pytest.mark.asyncio
async def test_failed_handoff_graceful_recovery() -> None:
    """TEST 3: Safe handling when handoff fails."""
    assistant = Assistant(user_id="test-farmer-3")

    def mock_failing_update_agent(agent):
        raise RuntimeError("Simulated LiveKit Agent Session error")

    class MockSession:
        def update_agent(self, agent):
            mock_failing_update_agent(agent)

    res = await assistant.handoff_to_crop_specialist(
        context=None, problem_description="Yellowing leaves"
    )
    assert "trouble connecting" in res.lower() or "unavailable" in res.lower()
