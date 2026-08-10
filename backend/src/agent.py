import asyncio
import json
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

from database import FarmerRepository
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
"""


class Assistant(Agent):
    def __init__(
        self,
        user_id: str = "anonymous",
        repository: FarmerRepository | None = None,
        farmer_memory: dict[str, Any] | None = None,
    ) -> None:
        self.user_id = user_id
        self.repository = repository or FarmerRepository()
        self.farmer_memory = farmer_memory

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
                "\n\nNO PREVIOUS FARMER MEMORY WAS FOUND. "
                "Treat this as a new farmer."
            )

        super().__init__(
            instructions=SYSTEM_PROMPT + memory_context
        )

    async def on_enter(self) -> None:
        """
        Do NOT call lookup_farmer() here.

        The initial farmer memory is loaded directly from the database
        before the AgentSession starts. This avoids Gemini function-call
        ordering errors before a user turn exists.
        """

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
                "Do not call any tools for the opening greeting.\n\n"
                + greeting
            )
        )

    @function_tool
    async def lookup_farmer(
        self,
        context: RunContext,
    ) -> str:
        """Look up persistent memory for the current farmer."""

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
            return (
                "No farmer profile found. Treat this as a new farmer."
            )

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
        facts: dict[str, Any] | None = None,
    ) -> str:
        """
        Save farmer information only after explicit consent.
        """

        logger.info("Saving farmer memory for user_id=%s", self.user_id)

        try:
            farmer = self.repository.save_farmer_memory(
                self.user_id,
                name,
                language_preference,
                facts or {},
            )
        except Exception:
            logger.exception("Farmer memory save failed")
            return (
                "Memory save failed. Do not claim that the information "
                "was saved."
            )

        if isinstance(farmer, dict):
            saved_fields = list(farmer.get("facts", {}).keys())
            if saved_fields:
                logger.info(
                    "Farmer memory saved: %s",
                    ", ".join(saved_fields),
                )

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
        result = await asyncio.to_thread(
            WeatherDataClient().get_weather_by_district, district
        )
        return json.dumps(result, ensure_ascii=False)


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    await ctx.connect()

    participants = list(ctx.room.remote_participants.values())

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
            "Initial farmer memory lookup failed. "
            "Starting without memory."
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
            tokenizer=tokenize.basic.SentenceTokenizer(
                min_sentence_len=2
            ),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],

        # Important: prevents the Gemini tool-call ordering issue
        # that was occurring with lookup_farmer().
        preemptive_generation=False,
    )

    await session.start(
        agent=Assistant(
            user_id=user_id,
            repository=repository,
            farmer_memory=farmer_memory,
        ),
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


if __name__ == "__main__":
    cli.run_app(server)
