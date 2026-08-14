import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from database import create_escalation as create_escalation_record
from database import get_farm_alert as get_farm_alert_record
from database import get_pending_alert_by_farmer as get_pending_alert_by_farmer_record
from database import lookup_farmer as lookup_farmer_record
from database import record_call_analytics as record_call_analytics_record
from database import record_call_attempt as record_call_attempt_record
from database import save_farmer_memory as save_farmer_memory_record
from database import update_farm_alert as update_farm_alert_record
from specialist import CropProblemSpecialist
from weather_data import WeatherDataClient

logger = logging.getLogger("agent")

ENV_LOCAL = Path(__file__).resolve().parent.parent / ".env.local"
if ENV_LOCAL.exists():
    load_dotenv(ENV_LOCAL)
else:
    load_dotenv(".env.local")

SYSTEM_PROMPT = """
ROLE
You are KrishiMitra AI, a friendly and helpful voice assistant for farmers. Help with
crops, irrigation, basic crop care, weather-related farming decisions, agricultural guidance,
and proactive farm alerts. Be respectful, patient, practical, concise, and professional.

LANGUAGE & SCRIPT
Detect the farmer's language and respond in natural Hindi/Hinglish/English.
When responding in Devanagari Hindi, write naturally. Hinglish phrasing like
"Namaste Ramesh ji, main KrishiMitra AI se bol rahi hoon" is also welcome.

MEMORY (DAY 4)
The current caller's stable LiveKit identity is available through memory tools.
On inbound calls, call lookup_user before greeting. For returning farmers, greet them naturally
using remembered facts. Only save new facts with save_user_memory after explicit farmer confirmation.

OUTBOUND FARM ALERT CALL FLOW (DAY 6)
When executing an outbound farm alert call:
1. PROACTIVE GREETING:
   Greet the farmer proactively using their name:
   "Namaste [Farmer Name] ji, main KrishiMitra AI se bol rahi hoon. Aapke khet ke sambandh mein ek important farming alert share karna tha."

2. SAFE FARMER VERIFICATION:
   Before revealing detailed farm information, ask the non-sensitive verification question returned by load_farm_alert.
   Call verify_farmer tool with the farmer's response.
   NEVER ask for OTP, PIN, password, bank details, Aadhaar, or sensitive financial information.
   Allow MAXIMUM 2 verification attempts.
   If verification fails after 2 attempts, call update_farm_alert_status(status="verification_failed", notes="Failed verification") and end call politely without revealing detailed farm info.

3. LOAD & READ THE FARM ALERT:
   Use load_farm_alert tool to retrieve structured alert details.
   Explain the alert clearly and naturally as an early warning or demo alert.
   Example: "Ramesh ji, aapke wheat crop ke liye leaf rust disease ka possible risk detect hua hai. Agle 2-3 din crop ko inspect karna aur preventive steps follow karna important hai."
   Do NOT present guesses as absolute facts. Use phrases like "possible risk", "early warning", "demo alert".

4. ASK FOR FARMER RESPONSE:
   Ask: "Kripya batayein, kya aapne apne khet mein aise symptoms dekhe hain?"
   Listen to natural responses like yes, no, maybe, not sure, will inspect later, busy/call later.

5. UPDATE ALERT STATUS USING TOOL:
   Call update_farm_alert_status tool with appropriate status:
   - 'confirmed': Farmer observed symptoms / acknowledged alert
   - 'needs_inspection': Farmer will inspect field later
   - 'not_observed': Farmer says no symptoms observed
   - 'follow_up_required': Farmer is busy / requests follow-up call
   - 'verification_failed': Farmer failed 2 verification attempts

6. FINAL RESPONSE & CONCLUSION:
   Provide a concise summary:
   "Thank you [Farmer Name] ji. Maine aapka response note kar liya hai. Aap pehle crop ko inspect kar lijiye. KrishiMitra AI aapko farming decisions mein support karne ke liye available hai. Dhanyavaad."

SAFETY
This is a farming demo assistant. Do not make false guarantees or state dangerous pesticide dosages.
For serious crop diseases or chemical treatments, recommend consulting a local KVK or Krishi Adhikari.

HUMAN ESCALATION POLICY (DAY 7)
- Know when to ask for human help instead of guessing.
- ESCALATION SCENARIOS:
  1. SERIOUS CROP PROBLEM: Severe disease, rapidly spreading infection, massive pest attack, severe drying/wilting, devastating crop loss risk, or when you cannot safely diagnose or solve the issue.
  2. MISSING OR OUTDATED MARKET DATA: When market/mandi prices are unavailable, stale, or unverified. NEVER invent or guess a price. Offer human help instead.
- PERMISSION IS MANDATORY: BEFORE calling `create_escalation`, ALWAYS ask for the farmer's permission first.
  Example: "Is problem ke liye main aapki request ek agricultural expert ko bhej sakti hoon. Main sirf aapka naam, problem ka short summary, maine kya check kiya, urgency aur aapki preferred language/follow-up method share karungi. Kya main ye request create kar doon?"
- IF PERMISSION GRANTED (yes, haan, kar do, okay, please do): Call `create_escalation` tool with permission_granted=True.
- IF PERMISSION DENIED (no, nahi, don't, mat karo): DO NOT call `create_escalation`. Respect the decision, offer standard safe guidance, and do not press the farmer.
- CONVEY REFERENCE ID: After `create_escalation` returns a success result with a reference_id (e.g. KM-2026-0001), report the reference ID clearly to the farmer and explain that human support will follow up using their preferred method.
- DO NOT promise immediate responses (e.g., "within 5 minutes" or "expert will call right now"). State honestly that the support team will follow up when available.
- NORMAL FARMING QUESTIONS ("Gehu mein paani kab dena chahiye?") MUST NOT trigger human escalation automatically.
- PRIVACY & SECURITY: NEVER ask for or record OTPs, PINs, passwords, bank account numbers, credit cards, or full chat transcripts.

CALL ANALYTICS & QUERY LOGGING (DAY 8)
- Call `get_weather_info` when asked for weather details or weather-based crop advice.
- Call `mark_query_answered` whenever you provide useful answers to farming or crop questions.
- Call `create_escalation` when creating an expert escalation.
- Call `update_farm_alert_status` during outbound alert calls.
Calling these tools records that the farmer's request was successfully fulfilled.

AGENT HANDOFF POLICY (DAY 9)
- You are the Main Agent (general Farm & Field assistant).
- You handle general farming questions, basic crop info, general livestock/farm questions, sowing time, irrigation, and normal conversation.
- DO NOT try to answer detailed crop disease, yellow leaves, pest attack, plant damage, or crop growth problem diagnosis yourself.
- CRITICAL TOOL INSTRUCTION: When the user asks about crop disease symptoms, pest problems, yellow leaves, plant damage, crop growth problems, or asks for detailed crop-problem guidance, you MUST call the `handoff_to_crop_specialist` function tool immediately. Do NOT reply with text alone without calling `handoff_to_crop_specialist`.
- For normal farming questions (e.g., "What is the best time to sow wheat?"), answer directly and DO NOT call `handoff_to_crop_specialist`.
"""


class Assistant(Agent):
    def __init__(
        self,
        user_id: str = "test-user",
        alert_id: int | None = None,
        is_outbound: bool = False,
    ) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.user_id = user_id
        self.alert_id = alert_id
        self.is_outbound = is_outbound
        self.current_alert: dict[str, Any] | None = None
        self.verification_passed: bool = False
        self.verification_attempts: int = 0
        self.verification_failed: bool = False
        self.success_condition_met: bool = False
        self.success_condition_description: str = ""
        self.failure_reason: str = ""
        self.turn_count: int = 0
        self.tools_used: set[str] = set()
        self.human_help_requested: bool = False

    @function_tool
    async def handoff_to_crop_specialist(
        self, context: RunContext, problem_description: str
    ) -> str:
        """Use this tool when the user describes crop disease symptoms, pest problems, yellow leaves, plant damage, crop growth problems, or asks for detailed crop-problem guidance.

        Do NOT use the tool for normal farming questions.
        """
        logger.info(
            "MainAgent initiating handoff to CropProblemSpecialist for caller %s with problem: %s",
            self.user_id,
            problem_description,
        )
        self.tools_used.add("handoff_specialist")
        self.human_help_requested = True
        try:
            specialist = CropProblemSpecialist(
                user_id=self.user_id, problem_context=problem_description
            )
            self.session.update_agent(specialist)
            self.success_condition_met = True
            self.success_condition_description = (
                f"Handed off to Crop Problem Specialist: {problem_description}"
            )
            return "I understand. This sounds like a specific crop health problem. I'll connect you with our Crop Problem Specialist so we can look into it more carefully."
        except Exception:
            logger.exception("Handoff to CropProblemSpecialist failed")
            return (
                "I'm having trouble connecting you to the crop specialist right now, "
                "but I can still help you with the information you have shared."
            )

    async def on_enter(self) -> None:
        """Opening prompt trigger for inbound or proactive outbound call."""
        if self.is_outbound:
            await self.session.generate_reply(
                instructions=(
                    "This is an OUTBOUND TELEPHONY FARM ALERT call. Call load_farm_alert now. "
                    "Then greet the farmer proactively in Hindi/Hinglish: "
                    "'Namaste [Farmer Name] ji, main KrishiMitra AI se bol rahi hoon. Aapke khet ke sambandh mein ek important farming alert share karna tha.' "
                    "Immediately follow with the non-sensitive verification question returned by load_farm_alert."
                )
            )
        else:
            await self.session.generate_reply(
                instructions=(
                    "This is the beginning of the call. Call lookup_user now, then give the "
                    "appropriate concise greeting based only on the tool result."
                )
            )

    @function_tool
    async def get_weather_info(
        self, context: RunContext, district: str
    ) -> dict[str, Any]:
        """Look up agricultural weather data, forecasts, and farming advice for a district.

        Call this whenever a farmer asks for weather details or weather-related farming advice.
        """
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
        """Mark that the farmer's crop/farm query or request has been successfully answered.

        Call this after providing requested farming info, crop guidance, or answering farmer questions.
        """
        self.success_condition_met = True
        self.success_condition_description = f"Query answered: {topic}"
        return {"status": "success", "message": f"Recorded success for topic: {topic}"}

    @function_tool
    async def lookup_user(self, context: RunContext) -> dict[str, Any]:
        """Look up the current caller's saved farming profile at the start of each call.

        Use this before greeting. Identity is supplied by LiveKit; do not ask the farmer.
        """
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
        """Persist consented useful farming details for the current caller.

        Call only after explicit farmer permission in the current conversation.
        """
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
    async def load_farm_alert(
        self, context: RunContext, alert_id: int | None = None
    ) -> dict[str, Any]:
        """Retrieve structured farm alert details for the current outbound call.

        Returns farmer name, crop, alert type, reason, recommended action, and non-sensitive verification question.
        """
        target_id = alert_id or self.alert_id
        alert = None
        if target_id is not None:
            alert = get_farm_alert_record(target_id)
        if alert is None and self.user_id:
            alert = get_pending_alert_by_farmer_record(self.user_id)
        if alert is None:
            alert = get_farm_alert_record(1)

        if alert is None:
            return {"status": "not_found", "message": "No farm alert record found."}

        self.current_alert = alert
        return {
            "status": "success",
            "alert": {
                "id": alert["id"],
                "farmer_name": alert["farmer_name"],
                "village": alert["village"],
                "crop": alert["crop"],
                "alert_type": alert["alert_type"],
                "alert_reason": alert["alert_reason"],
                "recommended_action": alert["recommended_action"],
                "verification_question": alert["verification_question"],
                "status": alert["status"],
            },
        }

    @function_tool
    async def verify_farmer(
        self, context: RunContext, farmer_id: str, verification_answer: str
    ) -> dict[str, Any]:
        """Verify the farmer's response against the non-sensitive verification question.

        Max 2 attempts allowed. Do not ask for sensitive info (OTP, PIN, Bank details).
        """
        if self.verification_passed:
            return {"status": "already_verified"}

        target_id = self.alert_id or (
            self.current_alert["id"] if self.current_alert else 1
        )
        alert = self.current_alert or get_farm_alert_record(target_id)
        if not alert:
            return {"status": "error", "message": "Alert record not loaded."}

        expected_answers = [
            ans.strip().lower() for ans in alert["verification_answer"].split(",")
        ]
        provided = verification_answer.strip().lower()

        is_match = any(
            expected in provided or provided in expected
            for expected in expected_answers
        )

        if is_match:
            self.verification_passed = True
            return {"status": "verified", "message": "Verification successful."}

        self.verification_attempts += 1
        if self.verification_attempts >= 2:
            self.verification_failed = True
            update_farm_alert_record(
                alert["id"],
                status="verification_failed",
                notes="Failed verification after 2 attempts",
                last_call_outcome="Verification failed",
            )
            return {
                "status": "failed",
                "attempts_made": self.verification_attempts,
                "message": "Verification failed maximum attempts reached.",
            }
        return {
            "status": "incorrect",
            "attempts_made": self.verification_attempts,
            "attempts_remaining": 2 - self.verification_attempts,
            "message": "Incorrect response. Please try one more time.",
        }

    @function_tool
    async def update_farm_alert_status(
        self,
        context: RunContext,
        status: str,
        notes: str = "",
        alert_id: int | None = None,
    ) -> dict[str, Any]:
        """Update the farm alert status in SQLite database after farmer response.

        Allowed statuses: 'confirmed', 'needs_inspection', 'not_observed',
        'follow_up_required', 'verification_failed'.
        """
        valid_statuses = {
            "confirmed",
            "needs_inspection",
            "not_observed",
            "follow_up_required",
            "verification_failed",
        }
        if status not in valid_statuses:
            return {
                "status": "error",
                "message": f"Invalid status '{status}'. Must be one of {list(valid_statuses)}",
            }

        target_id = (
            alert_id
            or self.alert_id
            or (self.current_alert["id"] if self.current_alert else 1)
        )
        updated = update_farm_alert_record(
            target_id,
            status=status,
            notes=notes,
            last_call_outcome=f"Call completed with status: {status}",
        )

        if status != "verification_failed":
            self.success_condition_met = True
            self.success_condition_description = f"Farm alert updated: {status}"
        else:
            self.failure_reason = "Farm alert verification failed"

        # Merge findings into Day 4 memory system
        try:
            farmer_name = (self.current_alert or {}).get("farmer_name") or "Ramesh"
            crop = (self.current_alert or {}).get("crop") or "Wheat"
            save_farmer_memory_record(
                self.user_id,
                farmer_name,
                "hi",
                {
                    "last_alert_discussed": (self.current_alert or {}).get(
                        "alert_type"
                    ),
                    "crop": crop,
                    "last_alert_status": status,
                    "last_alert_notes": notes,
                },
            )
        except Exception:
            logger.exception("Failed to update Day 4 memory during alert status update")

        return {"status": "updated", "record": updated}

    @function_tool
    async def log_call_outcome(
        self,
        context: RunContext,
        outcome: str,
        notes: str = "",
        alert_id: int | None = None,
    ) -> dict[str, Any]:
        """Log the call outcome and notes to the database."""
        target_id = (
            alert_id
            or self.alert_id
            or (self.current_alert["id"] if self.current_alert else 1)
        )
        record_call_attempt_record(target_id, outcome=f"{outcome}: {notes}")
        return {"status": "logged", "outcome": outcome}

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        problem_summary: str,
        what_agent_checked: str = "User requested human support.",
        urgency: str = "medium",
        language: str = "Hindi",
        preferred_follow_up_method: str = "Phone Call",
        farmer_name: str | None = None,
        permission_granted: bool = False,
    ) -> dict[str, Any]:
        """Create a human help escalation request when expert human agricultural support is required.

        MUST ONLY be called AFTER the farmer gives explicit permission in conversation.
        Reasons: 'SERIOUS_CROP_PROBLEM', 'MARKET_DATA_UNAVAILABLE_OR_STALE', 'OTHER'.
        Urgency: 'low', 'medium', 'high', 'emergency'.
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
                    f"Human help escalation created (ID: {ref_id})"
                )
            return res
        except Exception:
            logger.exception("Failed to execute create_escalation tool")
            return {
                "status": "error",
                "message": "Request create karne mein technical problem aa rahi hai. Main aapko galat confirmation nahi dungi.",
            }


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    user_id = participant.identity

    # Detect outbound SIP call / alert session parameters
    alert_id = None
    is_outbound = False

    if participant.metadata:
        try:
            meta = json.loads(participant.metadata)
            alert_id = meta.get("alert_id")
            if meta.get("call_mode") == "outbound_farm_alert":
                is_outbound = True
        except Exception:
            pass

    import contextlib

    if not is_outbound and participant.attributes:
        if participant.attributes.get("call_mode") == "outbound_farm_alert":
            is_outbound = True
        if participant.attributes.get("alert_id"):
            with contextlib.suppress(ValueError):
                alert_id = int(participant.attributes["alert_id"])

    if not is_outbound and (
        "outbound" in ctx.room.name.lower()
        or participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
    ):
        is_outbound = True

    logger.info(
        "Starting KrishiMitra session for caller %s (outbound=%s, alert_id=%s)",
        user_id,
        is_outbound,
        alert_id,
    )

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(model="gemini-3.5-flash-lite"),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    assistant = Assistant(user_id=user_id, alert_id=alert_id, is_outbound=is_outbound)
    from datetime import UTC, datetime

    started_at = datetime.now(UTC)

    try:
        await session.start(
            agent=assistant,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )
    finally:
        ended_at = datetime.now(UTC)
        duration = int((ended_at - started_at).total_seconds())
        channel = "sip" if is_outbound else "browser"

        current_agent = getattr(session, "current_agent", assistant)
        success_met = (
            getattr(current_agent, "success_condition_met", False)
            or assistant.success_condition_met
        )
        success_cond = (
            getattr(current_agent, "success_condition_description", "")
            or assistant.success_condition_description
        )
        fail_reason = (
            getattr(current_agent, "failure_reason", "") or assistant.failure_reason
        )

        tools_set = set(assistant.tools_used)
        if hasattr(current_agent, "tools_used"):
            tools_set.update(current_agent.tools_used)

        human_help = assistant.human_help_requested or getattr(
            current_agent, "human_help_requested", False
        )
        turn_count = max(assistant.turn_count, getattr(current_agent, "turn_count", 0))

        outcome = "SUCCESS" if success_met else "FAILED"
        failure_reason = (
            ""
            if success_met
            else (
                fail_reason
                or "Call ended before requested information or escalation was completed"
            )
        )

        record_call_analytics_record(
            call_id=ctx.room.name or f"call-{int(started_at.timestamp())}",
            started_at=started_at.isoformat(),
            ended_at=ended_at.isoformat(),
            duration_seconds=duration,
            channel=channel,
            outcome=outcome,
            failure_reason=failure_reason,
            success_condition=success_cond,
            turns_count=turn_count,
            tools_used=",".join(sorted(tools_set)),
            human_help_requested=human_help,
        )

    chat_tasks: set[asyncio.Task[None]] = set()

    def handle_chat_message(reader: rtc.TextStreamReader, sender_identity: str) -> None:
        """Pass typed messages to the same AgentSession used for voice."""

        async def respond() -> None:
            if sender_identity != user_id:
                logger.warning("Ignoring chat message from an unlinked participant")
                return
            try:
                message = (await reader.read_all()).strip()
                if message:
                    await session.interrupt()
                    session.generate_reply(user_input=message)
            except Exception:
                logger.exception("Unable to process typed chat message")

        task = asyncio.create_task(respond())
        chat_tasks.add(task)
        task.add_done_callback(chat_tasks.discard)

    ctx.room.register_text_stream_handler("krishimitra-chat", handle_chat_message)


if __name__ == "__main__":
    cli.run_app(server)
