import logging
from typing import Any

from livekit.agents import Agent, RunContext, function_tool

from database import create_escalation as create_escalation_record
from database import lookup_farmer as lookup_farmer_record
from database import save_farmer_memory as save_farmer_memory_record
from weather_data import WeatherDataClient

logger = logging.getLogger("agent.specialist")

SPECIALIST_SYSTEM_PROMPT = """
ROLE & IDENTITY
You are KrishiMitra's Crop Problem Specialist. Your job is to help farmers understand crop health problems and provide safe, practical, easy-to-understand guidance.

RESPONSIBILITIES
Focus ONLY on crop health, disease symptoms, yellowing/browning leaves, leaf curling, pest/insect attacks, nutrient deficiencies, irrigation crop damage, and troubleshooting plant growth issues.

GUIDANCE & SAFETY RULES
- Speak in simple, respectful language (Hindi, Hinglish, or English as spoken by the farmer).
- Ask short, helpful follow-up questions when necessary (crop name, visible symptoms, affected plant parts, when problem started, irrigation/fertilizer/pesticide usage).
- MUST NOT confidently claim a definitive disease diagnosis based only on a short verbal description.
- Use tentative, diagnostic phrases like:
  - "This could be related to..."
  - "One possible reason is..."
  - "To confirm the exact cause, a local agriculture expert or proper crop inspection may be needed."
- DO NOT recommend dangerous chemical dosages, unverified pesticides, or unsafe agricultural practices.

INTRODUCTION UPON HANDOFF
When taking over a conversation, introduce yourself clearly in Hindi/Hinglish:
"Namaste! Main KrishiMitra ka Crop Problem Specialist hoon."
Immediately acknowledge the farmer's passed problem context without making them repeat what they already said.

SCOPE LIMITS
If the user asks about unrelated topics (like weather forecasts or market prices), politely state:
"Main Crop Problem Specialist hoon. Weather ya general guidance ke liye aap hamare main KrishiMitra assistant se help le sakte hain."

CALL ANALYTICS & LOGGING
- Call `mark_query_answered` whenever you provide useful crop problem guidance.
- Call `create_escalation` when expert human support is requested or required.
"""


class CropProblemSpecialist(Agent):
    """Specialist agent focusing exclusively on crop disease, pest, and growth issues."""

    def __init__(
        self,
        user_id: str = "test-user",
        problem_context: str = "",
    ) -> None:
        super().__init__(instructions=SPECIALIST_SYSTEM_PROMPT)
        self.user_id = user_id
        self.problem_context = problem_context
        self.success_condition_met: bool = False
        self.success_condition_description: str = ""
        self.failure_reason: str = ""
        self.turn_count: int = 0
        self.tools_used: set[str] = set()
        self.human_help_requested: bool = False

    async def on_enter(self) -> None:
        """Called when handoff to specialist occurs."""
        instructions = (
            "You have just taken over as the Crop Problem Specialist. "
            "Introduce yourself clearly: 'Namaste! Main KrishiMitra ka Crop Problem Specialist hoon.' "
        )
        if self.problem_context:
            instructions += (
                f"Acknowledge the farmer's problem context immediately: '{self.problem_context}'. "
                "Do NOT ask them to repeat the problem. Provide tentative diagnostic possibilities using phrases like 'This could be related to...' or 'One possible reason is...', "
                "ask 1-2 short follow-up questions (e.g. affected plant parts, when it started, irrigation/fertilizer used), and offer safe practical checks."
            )
        else:
            instructions += "Ask the farmer to describe their crop health problem."

        await self.session.generate_reply(instructions=instructions)

    @function_tool
    async def get_weather_info(
        self, context: RunContext, district: str
    ) -> dict[str, Any]:
        """Look up agricultural weather data for a district."""
        client = WeatherDataClient()
        res = client.get_weather_by_district(district)
        if res.get("status") == "success":
            self.success_condition_met = True
            self.success_condition_description = (
                f"Weather information provided for {district}"
            )
        return res

    @function_tool
    async def mark_query_answered(
        self, context: RunContext, topic: str
    ) -> dict[str, Any]:
        """Mark that the farmer's crop problem query has been answered."""
        self.success_condition_met = True
        self.success_condition_description = f"Query answered by Specialist: {topic}"
        return {"status": "success", "message": f"Recorded success for topic: {topic}"}

    @function_tool
    async def lookup_user(self, context: RunContext) -> dict[str, Any]:
        """Look up the current caller's saved farming profile."""
        try:
            profile = lookup_farmer_record(self.user_id)
        except Exception:
            logger.exception("Farmer lookup failed for %s", self.user_id)
            return {
                "status": "error",
                "message": "Memory lookup is temporarily unavailable.",
            }
        if profile is None:
            return {"status": "not_found"}
        return {"status": "found", "profile": profile}

    @function_tool
    async def save_user_memory(
        self,
        context: RunContext,
        name: str | None = None,
        language_preference: str | None = None,
        facts: dict[str, str] | None = None,
        permission_granted: bool = False,
    ) -> dict[str, Any]:
        """Persist consented useful farming details for the current caller."""
        if not permission_granted:
            return {
                "status": "consent_required",
                "message": "Ask the farmer for permission before saving any memory.",
            }
        try:
            profile = save_farmer_memory_record(
                self.user_id, name, language_preference, facts or {}
            )
        except Exception:
            logger.exception("Farmer memory save failed for %s", self.user_id)
            return {
                "status": "error",
                "message": "The information could not be saved. Do not claim it was saved.",
            }
        return {"status": "saved", "profile": profile}

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        problem_summary: str,
        what_agent_checked: str = "Crop Problem Specialist evaluated symptoms.",
        urgency: str = "medium",
        language: str = "Hindi",
        preferred_follow_up_method: str = "Phone Call",
        farmer_name: str | None = None,
        permission_granted: bool = False,
    ) -> dict[str, Any]:
        """Create a human help escalation request when expert agricultural support is required.

        MUST ONLY be called AFTER the farmer gives explicit permission in conversation.
        """
        if not permission_granted:
            return {
                "status": "permission_denied",
                "message": "Permission was not granted by the farmer. Do NOT create the escalation.",
            }

        name = farmer_name or "Farmer"
        try:
            profile = lookup_farmer_record(self.user_id)
            if profile and profile.get("name"):
                name = profile["name"]
        except Exception:
            pass

        try:
            res = create_escalation_record(
                farmer_name=name,
                reason=reason,
                problem_summary=problem_summary,
                what_agent_checked=what_agent_checked,
                urgency=urgency,
                language=language,
                preferred_follow_up_method=preferred_follow_up_method,
                permission_granted=permission_granted,
            )
            if res.get("status") == "success":
                self.success_condition_met = True
                ref_id = res.get("reference_id", "")
                self.success_condition_description = (
                    f"Human help escalation created by Specialist (ID: {ref_id})"
                )
            return res
        except Exception:
            logger.exception("Failed to execute create_escalation tool")
            return {
                "status": "error",
                "message": "Request create karne mein technical problem aa rahi hai.",
            }
