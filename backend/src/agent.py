import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from livekit import api
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
from livekit.plugins import deepgram, google, murf, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from crop_specialist import CropSpecialist
from database import FarmerRepository
from escalation_api import start_escalation_api
from market_data import MarketDataClient
from telephony.outbound.policy import is_opt_out_request
from weather_data import WeatherDataClient

logger = logging.getLogger("agent")

load_dotenv(".env.local")


SYSTEM_PROMPT = """
You are KrishiMitra AI, a friendly and intelligent Indian farming assistant.

Help farmers with crop care, irrigation, crop planning, soil preparation,
fertilizers, pest awareness, organic farming, seasonal farming, and general
agricultural guidance.

Always respond in the farmer's language.
If the farmer speaks Hindi, use Devanagari script.
If the farmer speaks English, respond in English.
If the farmer uses Hinglish, use natural Hindi + English.

Keep voice responses short, natural, friendly and practical.

You have persistent farmer memory through:
- lookup_farmer()
- save_farmer_memory()

You have get_weather_by_district(district), which uses LOCAL/DEMO DATA and is
not live weather. Use it automatically whenever a farmer asks for weather,
today's weather, temperature, humidity, rain possibility, weather conditions,
or weather-related farming advice for a specific district. Never invent weather
values. If the district is missing, ask: "Bilkul, main weather check kar sakta
hoon. Aap kis district ka weather jaana chahte hain?" Do not guess a district,
unless saved memory clearly contains one. For successful results, naturally say
the exact data date and clearly say it is local/demo data, not live weather.
Never read JSON. If data is unavailable, say that weather data is unavailable
and you cannot confirm weather right now. If no district record is found, say
you do not have local weather data for that district and will not guess.

Never ask the farmer for an internal user ID.
Never invent an ID.
Never expose raw JSON or database details.

Only save information after the farmer clearly gives permission.
Never claim information was saved unless the save tool succeeds.

Do not claim live weather, live mandi prices, government eligibility,
crop diagnosis, medical advice, veterinary diagnosis, legal advice, or
financial advice without a verified source.

For live or local information, recommend official sources such as IMD,
local Mandi, Krishi Vigyan Kendra, or Agriculture Officer.

Be respectful, patient, encouraging and farmer-friendly.

KRISHIMITRA HUMAN ESCALATION POLICY:
- Do not try to solve every problem yourself. Escalate only (1) serious crop
  problems: rapid disease spread, major pest infestation, widespread damage,
  severe drying/wilting, likely major loss, or any case you cannot safely assess;
  and (2) missing, unavailable, invalid, or stale mandi/market price data.
- Use get_market_price(crop, mandi) for any mandi-price question. Never invent,
  estimate, or present an unverified market price. Its unavailable result means
  human help is needed.
- Before calling create_escalation, explain why help is needed and ask explicit
  permission. Say that only name (if known), a short problem summary, what you
  checked, urgency, language, and preferred follow-up method will be shared.
  Wait for a clear yes/haan/okay/kar do before calling the tool. A no means do
  not create anything and do not pressure the farmer.
- Keep the summary short and useful; never include OTPs, PINs, passwords, bank
  details, account/card numbers, or a full conversation. Do not create duplicate
  requests. After success give the reference ID and say support will follow up
  when available, without promising a response time.
- Normal crop-care questions remain normal assistance and must not be escalated.

DAY 9 — AGENT HANDOFF POLICY:
- You have a handoff_to_crop_specialist tool available.
- When the user describes specific crop disease symptoms, pest problems,
  yellowing/browning/wilting leaves, plant damage, crop growth abnormalities,
  or asks for detailed crop-problem diagnosis, you MUST use the
  handoff_to_crop_specialist tool to transfer the conversation.
- Before calling the tool, briefly tell the farmer:
  "I'll connect you to our crop specialist who can help with this."
- Pass the user's exact problem description as the context parameter.
- Do NOT attempt to diagnose crop diseases, identify pests, or provide
  detailed crop-problem guidance yourself. That is the specialist's job.
- For normal farming questions (sowing times, irrigation, soil prep, general
  crop info, livestock, fertilizer basics), answer directly without handoff.

For an outbound demo weather-alert call, clearly say that you are KrishiMitra AI,
an automated agricultural assistant, and that the alert uses local/demo weather
data rather than live weather. If the farmer says stop, band kijiye, call mat
karna, don't call me, no more calls, or an equivalent request, immediately call
opt_out_of_outbound_calls(), give a brief Hindi/Hinglish confirmation, and end
the call. Do not continue the alert after an opt-out request.
"""


class Assistant(Agent):
    def __init__(
        self,
        user_id: str = "anonymous",
        repository: FarmerRepository | None = None,
        farmer_memory: dict[str, Any] | None = None,
        outbound_alert: bool = False,
        room_name: str | None = None,
        livekit_api: Any | None = None,
    ) -> None:
        self.user_id = user_id
        self.repository = repository or FarmerRepository()
        self.farmer_memory = farmer_memory
        self.outbound_alert = outbound_alert
        self.room_name = room_name
        self.livekit_api = livekit_api
        self._opt_out_end_task: asyncio.Task[None] | None = None
        self._escalation_permission_pending = False
        self._escalation_permission_granted = False
        self._pending_escalation_reason: str | None = None
        # Day 8 — call analytics tracking
        self._success_condition_met = False
        self._success_condition_reason: str | None = None
        self._call_started_at = datetime.now(UTC)
        self._user_turns = 0
        self._assistant_turns = 0
        self._tools_used: list[str] = []
        self._used_search = False
        self._human_help_requested = False
        self._language: str | None = None

        memory_context = ""

        if farmer_memory:
            memory_context = (
                "\n\nFARMER MEMORY FOR THIS SESSION:\n"
                + json.dumps(
                    farmer_memory,
                    ensure_ascii=False,
                    default=str,
                )
                + "\nUse this memory naturally when relevant. "
                "Do not reveal raw JSON or internal database details."
            )
        else:
            memory_context = (
                "\n\nNO PREVIOUS FARMER MEMORY WAS FOUND. Treat this as a new farmer."
            )

        super().__init__(instructions=SYSTEM_PROMPT + memory_context)

    async def on_enter(self) -> None:
        """
        Do NOT call lookup_farmer() here.

        The initial farmer memory is loaded directly from the database
        before the AgentSession starts. This avoids Gemini function-call
        ordering errors before a user turn exists.
        """

        if self.outbound_alert:
            await self.session.generate_reply(
                instructions=(
                    "Speak this opening naturally in Hindi/Hinglish, without tools: "
                    "Namaste, main KrishiMitra AI hoon, automated kheti sahayak. "
                    "Main aapke registered crop ke liye demo weather warning dene "
                    "ke liye call kar raha hoon. Agar aap future mein aise calls "
                    "nahi chahte, bas stop, band kijiye, ya call mat karna keh dijiye. "
                    "Hamare local demo weather data mein baarish ki sambhavna hai, "
                    "isliye kati hui fasal ko dhak kar aur zaroori kaam baarish se "
                    "pehle kar lena behtar rahega. Kya aap is alert ke baare mein "
                    "aur jaankari chahenge?"
                )
            )
            return

        if self.farmer_memory:
            name = self.farmer_memory.get("name")

            if name:
                greeting = (
                    f"नमस्ते {name} जी! आपका फिर से स्वागत है। "
                    "आज मैं आपकी खेती से जुड़ी किस समस्या में मदद कर सकता हूँ?"
                )
            else:
                greeting = (
                    "नमस्ते! आपका फिर से स्वागत है। "
                    "आज मैं आपकी खेती से जुड़ी किस समस्या में मदद कर सकता हूँ?"
                )
        else:
            greeting = (
                "नमस्ते! मैं KrishiMitra AI हूँ, आपका डिजिटल खेती सहायक। "
                "मैं फसल, सिंचाई, मिट्टी, खाद और खेती से जुड़ी सामान्य जानकारी "
                "में आपकी मदद कर सकता हूँ। आज आप किस बारे में जानना चाहते हैं?"
            )

        await self.session.generate_reply(
            instructions=(
                "Give this short opening greeting. "
                "Do not call any tools for the opening greeting.\n\n" + greeting
            )
        )

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Make explicit outbound-call opt-outs non-optional for the LLM."""
        self._user_turns += 1
        if not self._success_condition_met:
            self._success_condition_met = True
            self._success_condition_reason = "Conversation completed successfully"
        text = new_message.text_content or ""
        if self.outbound_alert and is_opt_out_request(new_message.text_content or ""):
            new_message.content.append(
                "SYSTEM INSTRUCTION: This is an explicit opt-out. Immediately "
                "call opt_out_of_outbound_calls, briefly confirm in Hindi/Hinglish, "
                "and do not continue the weather-alert conversation."
            )
        if self._escalation_permission_pending and self._is_affirmative(text):
            self._escalation_permission_granted = True
            reason = self._pending_escalation_reason or "SERIOUS_CROP_PROBLEM"
            new_message.content.append(
                f"SYSTEM INSTRUCTION: The farmer granted permission for human escalation. "
                f"Call the create_escalation tool now with reason {reason}, a short sanitized problem summary, "
                "what was checked, urgency, language, and preferred follow-up method."
            )
        elif self._escalation_permission_pending and self._is_negative(text):
            self._escalation_permission_pending = False
            self._escalation_permission_granted = False
            self._pending_escalation_reason = None
            new_message.content.append(
                "SYSTEM INSTRUCTION: The farmer declined escalation. Respect that "
                "choice, do not call create_escalation, and continue normal help if possible."
            )
        elif self._is_serious_crop_problem(text):
            self._escalation_permission_pending = True
            self._pending_escalation_reason = "SERIOUS_CROP_PROBLEM"
            new_message.content.append(
                "SYSTEM INSTRUCTION: This appears to be a serious crop problem. "
                "Do not diagnose or create a request yet. Briefly explain why expert "
                "help is needed and ask explicit permission to share a short summary."
            )

    @staticmethod
    def _is_affirmative(text: str) -> bool:
        return bool(
            re.search(
                r"\b(yes|yeah|okay|ok|haan|han|ha|kar do|bhej do|send it|please do)\b",
                text,
                re.I,
            )
        )

    @staticmethod
    def _is_negative(text: str) -> bool:
        return bool(
            re.search(r"\b(no|nahi|nahin|mat karo|don't|do not|not now)\b", text, re.I)
        )

    @staticmethod
    def _is_serious_crop_problem(text: str) -> bool:
        serious = r"(rapid|tezi se|bahut tezi|spread|fail rahi|widespread|puri fasal|major|bahut zyada|severe|devastat|kharab ho rahi|sookh|drying|wilting)"
        crop = r"(crop|fasal|gehun|gehu|wheat|pest|keede|disease|bimari)"
        return bool(re.search(serious, text, re.I) and re.search(crop, text, re.I))

    @function_tool
    async def lookup_farmer(
        self,
        context: RunContext,
    ) -> str:
        """Look up persistent memory for the current farmer."""
        if "lookup_farmer" not in self._tools_used:
            self._tools_used.append("lookup_farmer")

        logger.info("Looking up farmer memory for user_id=%s", self.user_id)

        try:
            farmer = self.repository.lookup_farmer(self.user_id)
        except Exception:
            logger.exception("Farmer memory lookup failed")
            return (
                "Memory lookup failed. Continue normally without assuming "
                "previous farmer information."
            )

        if farmer is None:
            return "No farmer profile found. Treat this as a new farmer."

        return json.dumps(
            farmer,
            ensure_ascii=False,
            default=str,
        )

    @function_tool
    async def save_farmer_memory(
        self,
        context: RunContext,
        name: str | None = None,
        language_preference: str | None = None,
        facts_json: str = "{}",
    ) -> str:
        """
        Save farmer information only after explicit consent.
        """
        if "save_farmer_memory" not in self._tools_used:
            self._tools_used.append("save_farmer_memory")

        logger.info("Saving farmer memory for user_id=%s", self.user_id)

        try:
            facts = json.loads(facts_json)
            if not isinstance(facts, dict):
                return "Memory save failed. Use a JSON object for facts."
            farmer = self.repository.save_farmer_memory(
                self.user_id,
                name,
                language_preference,
                facts,
            )
        except Exception:
            logger.exception("Farmer memory save failed")
            return "Memory save failed. Do not claim that the information was saved."

        if isinstance(farmer, dict):
            saved_fields = list(farmer.get("facts", {}).keys())
            if saved_fields:
                logger.info(
                    "Farmer memory saved: %s",
                    ", ".join(saved_fields),
                )

        self._success_condition_met = True
        self._success_condition_reason = "Farmer memory saved"
        return "The farmer information was saved successfully."

    @function_tool
    async def get_weather_by_district(
        self,
        context: RunContext,
        district: str,
    ) -> str:
        """
        Look up local/demo weather data for one Madhya Pradesh district.

        Use whenever the farmer asks about current/today's weather, temperature,
        humidity, rain probability, weather conditions, or farming weather advice
        for a specific district. This is LOCAL/DEMO DATA, never live weather.
        If the district is absent, ask which district before calling this tool.
        """
        if "get_weather_by_district" not in self._tools_used:
            self._tools_used.append("get_weather_by_district")
        self._used_search = True
        result = await asyncio.to_thread(
            WeatherDataClient().get_weather_by_district, district
        )
        if result.get("status") == "success":
            self._success_condition_met = True
            self._success_condition_reason = "Weather data provided"
        return json.dumps(result, ensure_ascii=False)

    @function_tool
    async def get_market_price(self, context: RunContext, crop: str, mandi: str) -> str:
        """Check a verified current mandi price. Never use it to guess a price."""
        if "get_market_price" not in self._tools_used:
            self._tools_used.append("get_market_price")
        self._used_search = True
        result = await asyncio.to_thread(
            MarketDataClient().get_market_price, crop, mandi
        )
        self._escalation_permission_pending = True
        self._pending_escalation_reason = "MARKET_DATA_UNAVAILABLE_OR_STALE"
        return json.dumps(result, ensure_ascii=False)

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        problem_summary: str,
        what_agent_checked: str,
        urgency: str = "high",
        language: str | None = None,
        preferred_follow_up_method: str | None = None,
    ) -> str:
        """Create a human-support request only after the farmer explicitly agrees."""
        if "create_escalation" not in self._tools_used:
            self._tools_used.append("create_escalation")
        self._human_help_requested = True
        if not self._escalation_permission_granted:
            return (
                "Permission has not been confirmed. Do not create an escalation. "
                "Ask the farmer for clear permission first."
            )
        if reason == "MARKET_DATA_UNAVAILABLE_OR_STALE":
            urgency = "medium"
        try:
            memory = (
                self.farmer_memory or self.repository.lookup_farmer(self.user_id) or {}
            )
            record, duplicate = self.repository.create_escalation(
                farmer_name=memory.get("name"),
                farmer_identifier=self.user_id if self.user_id != "anonymous" else None,
                reason=reason,
                problem_summary=problem_summary,
                what_agent_checked=what_agent_checked,
                urgency=urgency,
                language=language or memory.get("language_preference"),
                preferred_follow_up_method=preferred_follow_up_method,
            )
        except Exception:
            logger.exception("Escalation creation failed")
            return (
                "Escalation creation failed. Tell the farmer honestly that there is "
                "a technical problem and do not say the request was created."
            )
        finally:
            self._escalation_permission_pending = False
            self._escalation_permission_granted = False
        if duplicate:
            self._success_condition_met = True
            self._success_condition_reason = "Human escalation (existing request)"
            return f"An open request already exists. Reference ID: {record['reference_id']}."
        self._success_condition_met = True
        self._success_condition_reason = "Human escalation created"
        return (
            f"Request created successfully. Reference ID: {record['reference_id']}. "
            "Tell the farmer human agricultural support will review it when available "
            "and follow up using the preferred method; do not promise a time."
        )

    @function_tool
    async def opt_out_of_outbound_calls(self, context: RunContext) -> str:
        """Record an explicit request to stop all future outbound alert calls."""
        if "opt_out_of_outbound_calls" not in self._tools_used:
            self._tools_used.append("opt_out_of_outbound_calls")
        logger.info("Recording outbound call opt-out for user_id=%s", self.user_id)
        try:
            self.repository.opt_out_of_outbound_calls(self.user_id)
            self._opt_out_end_task = asyncio.create_task(
                self._end_outbound_call_after_confirmation()
            )
        except Exception:
            logger.exception("Outbound opt-out could not be fully completed")
            return "The opt-out could not be saved. Apologize and ask the farmer to try again."
        return (
            "Opt-out saved. Give the short confirmation now; the call will end "
            "immediately after it finishes."
        )

    @function_tool
    async def handoff_to_crop_specialist(
        self,
        context: RunContext,
        problem_context: str,
    ) -> str:
        """Transfer the conversation to the Crop Problem Specialist agent.

        Use this tool ONLY when the user describes crop disease symptoms, pest
        problems, yellowing/browning/wilting leaves, plant damage, crop growth
        abnormalities, or asks for detailed crop-problem diagnosis or guidance.

        Do NOT use this tool for normal farming questions like sowing times,
        irrigation schedules, soil preparation, general crop information,
        livestock questions, or basic fertilizer advice.

        Args:
            problem_context: The user's exact problem description and any
                relevant details already collected during the conversation.
                This is passed to the specialist so the farmer does not
                have to repeat themselves.
        """
        if "handoff_to_crop_specialist" not in self._tools_used:
            self._tools_used.append("handoff_to_crop_specialist")
        logger.info(
            "Handoff to crop specialist requested. Context: %s",
            problem_context[:200],
        )
        try:
            specialist = CropSpecialist(
                handoff_context=problem_context,
                farmer_memory=self.farmer_memory,
            )
            await self.session.update_agent(specialist)
            self._success_condition_met = True
            self._success_condition_reason = "Handoff to crop specialist"
            return (
                "Handoff successful. The Crop Problem Specialist has taken over "
                "the conversation. Do not continue responding — the specialist "
                "will handle it from here."
            )
        except Exception:
            logger.exception("Handoff to crop specialist failed")
            return (
                "I'm having trouble connecting you to the crop specialist right now, "
                "but I can still help you with the information you have shared."
            )

    async def _end_outbound_call_after_confirmation(self) -> None:
        """Leave enough time for the confirmation TTS before ending the SIP call."""
        if not self.livekit_api or not self.room_name:
            return
        await asyncio.sleep(4)
        try:
            await self.livekit_api.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=self.room_name,
                    identity=self.user_id,
                )
            )
            logger.info("Outbound SIP call ended after opt-out confirmation")
        except Exception:
            logger.exception("Could not end outbound SIP call after opt-out")


server = AgentServer()

start_escalation_api()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    await ctx.connect()

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant) -> None:
        logger.info(
            "participant_connected identity=%s kind=%s",
            participant.identity,
            participant.kind,
        )

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant) -> None:
        logger.info(
            "track_subscribed identity=%s kind=%s source=%s",
            participant.identity,
            track.kind,
            publication.source,
        )

    participants = list(ctx.room.remote_participants.values())

    for participant in participants:
        logger.info(
            "participant_connected identity=%s kind=%s (already in room)",
            participant.identity,
            participant.kind,
        )

    if participants:
        user_id = participants[0].identity
        logger.info("Farmer identity detected: %s", user_id)
    else:
        user_id = ctx.room.name
        logger.warning(
            "No remote participant found. Using room name as fallback: %s",
            user_id,
        )

    repository = FarmerRepository()

    farmer_memory = None

    try:
        farmer_memory = repository.lookup_farmer(user_id)

        if farmer_memory:
            logger.info("Existing farmer memory found.")
        else:
            logger.info("No previous farmer memory found.")

    except Exception:
        logger.exception(
            "Initial farmer memory lookup failed. Starting without memory."
        )

    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi",
        ),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Important: prevents the Gemini tool-call ordering issue
        # that was occurring with lookup_farmer().
        preemptive_generation=False,
    )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event) -> None:
        logger.info(
            "user_input_transcribed final=%s language=%s transcript=%s",
            event.is_final,
            event.language,
            event.transcript,
        )
        if event.language:
            assistant._language = str(event.language)
        if event.is_final:
            logger.info("USER TRANSCRIPT: %s", event.transcript)

    @session.on("user_state_changed")
    def on_user_state_changed(event) -> None:
        logger.info(
            "user_state_changed %s -> %s",
            event.old_state,
            event.new_state,
        )

    @session.on("agent_state_changed")
    def on_agent_state_changed(event) -> None:
        logger.info(
            "agent_state_changed %s -> %s",
            event.old_state,
            event.new_state,
        )

    @session.on("conversation_item_added")
    def on_conversation_item_added(event) -> None:
        item = event.item
        role = getattr(item, "role", "unknown")
        if role == "assistant":
            assistant._assistant_turns += 1
        logger.info(
            "conversation_item_added role=%s text=%s",
            role,
            getattr(item, "text_content", None),
        )

    is_outbound = getattr(ctx.job, "metadata", "") == "krishimitra-weather-alert"
    assistant = Assistant(
        user_id=user_id,
        repository=repository,
        farmer_memory=farmer_memory,
        outbound_alert=is_outbound,
        room_name=ctx.room.name,
        livekit_api=ctx.api,
    )

    # Day 8 — record comprehensive call analytics when participant disconnects
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant) -> None:
        logger.info("participant_disconnected identity=%s", participant.identity)
        try:
            now = datetime.now(UTC)
            duration = int((now - assistant._call_started_at).total_seconds())
            channel = "sip" if is_outbound else "browser"
            total_turns = assistant._user_turns + assistant._assistant_turns
            outcome = (
                "HUMAN_HELP"
                if assistant._human_help_requested
                else (
                    "SUCCESS"
                    if (assistant._success_condition_met or assistant._user_turns > 0)
                    else "FAILED"
                )
            )
            failure_reason = (
                None
                if outcome in ("SUCCESS", "HUMAN_HELP")
                else "Call ended before conversation or success condition was met"
            )
            success_condition = assistant._success_condition_reason or (
                "General conversation" if assistant._user_turns > 0 else None
            )
            repository.save_call_analytics(
                call_id=ctx.room.name,
                started_at=assistant._call_started_at.isoformat(),
                ended_at=now.isoformat(),
                duration_seconds=duration,
                channel=channel,
                outcome=outcome,
                turns_count=total_turns,
                user_turns=assistant._user_turns,
                tools_used=assistant._tools_used,
                used_search=assistant._used_search,
                human_help_requested=assistant._human_help_requested,
                language=assistant._language,
                failure_reason=failure_reason,
                success_condition=success_condition,
            )
            logger.info(
                "Call analytics saved: call_id=%s outcome=%s turns=%d tools=%s duration=%ds",
                ctx.room.name,
                outcome,
                total_turns,
                assistant._tools_used,
                duration,
            )
        except Exception:
            logger.exception("Failed to save call analytics")

    await session.start(
        agent=assistant,
        room=ctx.room,
        # Use LiveKit's direct room audio input. Do not insert a custom SIP
        # noise-cancellation processor before VAD and Deepgram STT.
        room_options=room_io.RoomOptions(close_on_disconnect=False),
    )


if __name__ == "__main__":
    cli.run_app(server)
