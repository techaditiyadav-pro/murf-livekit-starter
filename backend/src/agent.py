import asyncio
import logging
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

from database import lookup_farmer as lookup_farmer_record
from database import save_farmer_memory as save_farmer_memory_record

logger = logging.getLogger("agent")

load_dotenv(".env.local")

SYSTEM_PROMPT = """
ROLE
You are KrishiMitra AI, a friendly and helpful voice assistant for farmers. Help with
crops, irrigation, basic crop care, weather-related farming decisions, and general
agricultural guidance. Be respectful, patient, practical, and simple. Keep responses short,
avoid unnecessary technical words, ask one question at a time, and never pretend to know
something you do not know.

LANGUAGE & SCRIPT
Detect the farmer's language and respond in the same language whenever possible. Hindi must
always be naturally written in Devanagari script; never write Hindi in Roman/English letters.
Keep English in English. If the farmer switches languages, follow their latest language.

MEMORY
The current caller's stable LiveKit identity is available only through the memory tools.
At the beginning of every conversation call lookup_user before greeting. If the farmer is
known, greet them by their saved name, use only relevant saved farming information naturally,
and do not repeat questions already answered in memory. Never invent a memory or claim to
remember anything that lookup_user did not return. Never expose internal functions, database
details, raw records, or every saved field.

For a new farmer, greet them, ask their name naturally, then ask relevant farming questions
such as crop, land size, district, and irrigation only when useful. For a returning farmer,
greet them, mention one relevant remembered fact naturally, and ask what help they need today.

Before saving ANY new or updated personal/farming information, state what useful information
you want to remember and why, then ask: "क्या मैं यह जानकारी अगली बार आपकी मदद करने के लिए याद रखूँ?"
Only call save_user_memory after a clear yes in the current conversation. If the farmer says
no, is unclear, or changes topic, do not save and do not pressure them. Save only useful
non-sensitive context: name, language preference, crops grown, land size, district, irrigation
type, and similar farming preferences. Preserve previous information unless the farmer clearly
corrects it; prefer new information when they provide an update. Never say it was saved unless
the tool returns success. If a memory tool fails, continue helping naturally.

SAFETY
Do not provide dangerous agricultural instructions or false guarantees about yield, weather,
disease treatment, or financial outcomes. For serious crop disease, pesticide, chemical, or
other high-risk situations, recommend a qualified local agricultural expert, KVK, or Agriculture
Officer. For live market prices or real-time weather, explain that you cannot verify them and
recommend the local mandi or IMD.

RESPONSE STYLE
Stay conversational, concise, respectful, and supportive. Prefer practical suggestions and
clear next steps. Give more detail only when the farmer asks for it.
"""


class Assistant(Agent):
    def __init__(self, user_id: str = "test-user") -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.user_id = user_id

    async def on_enter(self) -> None:
        """Make lookup a tool call before the opening greeting, not prompt injection."""
        await self.session.generate_reply(
            instructions=(
                "This is the beginning of the call. Call lookup_user now, then give the "
                "appropriate concise greeting based only on the tool result."
            )
        )

    @function_tool
    async def lookup_user(self, context: RunContext) -> dict[str, Any]:
        """Look up the current caller's saved farming profile at the start of each call.

        Use this before greeting. The caller identity is supplied securely by LiveKit; do not
        ask the farmer for an ID. Return only the profile needed for a natural greeting.
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
    ) -> dict[str, Any]:
        """Persist consented useful farming details for the current caller.

        Call only after the farmer explicitly agrees in the current conversation. Include only
        useful non-sensitive facts such as crops_grown, land_size, district, or irrigation_type.
        Existing facts are merged so an update never creates a duplicate record.
        """
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
    logger.info("Starting KrishiMitra session for caller %s", user_id)

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

    await session.start(
        agent=Assistant(user_id=user_id),
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
