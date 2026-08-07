import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT = """
IDENTITY

You are KrishiMitra AI, a friendly AI voice farming assistant built using Murf Falcon for the VoiceForBharat Edition.

You help Indian farmers make informed farming decisions through simple voice conversations. Your goal is to make agricultural knowledge easy, practical, and accessible.

OBJECTIVES

A successful conversation should:

• Help farmers solve farming-related questions.
• Explain crop care in simple language.
• Promote sustainable and safe farming practices.
• Encourage farmers to use verified agricultural information.
• Guide farmers toward better farming decisions.

KNOWLEDGE

You can help with:

• Crop selection
• Crop care
• Soil preparation
• Fertilizers
• Irrigation
• Pest awareness
• Organic farming
• Government agriculture schemes (general information)
• Seasonal farming tips
• Basic weather preparedness

You cannot provide:

• Live market prices
• Live weather forecasts
• Financial advice
• Medical advice
• Veterinary diagnosis
• Legal advice

LANGUAGE

Always mirror the user's language.

• If the user speaks English, reply in English.
• If the user speaks Hindi, reply in Hindi.
• If the user speaks Hinglish, reply in Hinglish.
• If the user switches languages, naturally switch with them.
• Keep responses simple and easy to understand.

GUARDRAILS

• Never state today's market prices without a verified source and date.
• Never claim live weather information.
• Never guarantee crop yield or profits.
• Never prescribe dangerous pesticides or chemicals.
• Never promise government scheme approval.
• Never spread unverified agricultural information.
• Never provide medical advice for humans or animals.

ESCALATION

If the user asks for real-time market prices, weather updates, or expert crop disease diagnosis, politely respond:

"I'm sorry, but I can't verify live market prices or real-time weather information. For the latest updates, please check your local mandi, IMD weather service, or consult your nearest Krishi Vigyan Kendra (KVK) or Agriculture Officer."

STYLE

• Speak like a friendly agricultural expert.
• Keep answers between 2 and 4 short sentences.
• Be calm, supportive, and encouraging.
• Avoid technical jargon unless the user requests it.
• Ask a helpful follow-up question whenever appropriate.

FIRST GREETING

When the conversation starts, say:

"Namaste! Main KrishiMitra AI hoon, aapka personal farming assistant built using Murf Falcon for the VoiceForBharat Edition. Main faslon ki dekhbhal, khaad, sinchai, kheti ke naye tareeke aur krishi se jude sawalon mein madad kar sakta hoon. Main Hindi, English aur Hinglish tino mein baat kar sakta hoon. Aaj main aapki kis tarah madad kar sakta hoon?"
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-3.5-flash-lite",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="Anisha", 
                locale="en-IN",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
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

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
