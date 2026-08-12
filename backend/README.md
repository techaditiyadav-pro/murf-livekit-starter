# Backend — Voice Agent with Murf Falcon TTS

The Python backend for the Voice Agent Starter. It runs a real-time voice AI pipeline using [LiveKit Agents](https://docs.livekit.io/agents), connecting Murf Falcon TTS, Deepgram STT, and Google Gemini into a single conversational agent.

## How It Works

```
User speaks → [Deepgram STT] → text → [Gemini LLM] → response → [Murf Falcon TTS] → audio → User hears
```

LiveKit handles the real-time audio transport. The agent connects to LiveKit as a participant, listens for user speech, and responds with synthesized audio.

## Setup

### 1. Install dependencies

```bash
cd backend
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env.local
```

Fill in your keys in `.env.local`:

| Variable             | Where to get it                                           |
| -------------------- | --------------------------------------------------------- |
| `LIVEKIT_URL`        | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `LIVEKIT_API_KEY`    | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `LIVEKIT_API_SECRET` | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `MURF_API_KEY`       | [murf.ai/api/dashboard](https://murf.ai/api/dashboard)    |
| `DEEPGRAM_API_KEY`   | [deepgram.com](https://console.deepgram.com/)             |
| `GOOGLE_API_KEY`     | [aistudio.google.com](https://aistudio.google.com/apikey) |

For LiveKit Cloud users, you can auto-populate LiveKit credentials:

```bash
lk cloud auth
lk app env -w -d .env.local
```

### 3. Download models

```bash
uv run python src/agent.py download-files
```

This downloads Silero VAD and the LiveKit turn detector models.

### 4. Run the agent

```bash
# Development mode (auto-reload)
uv run python src/agent.py dev

# Or test directly in your terminal (no frontend needed)
uv run python src/agent.py console

# Production
uv run python src/agent.py start
```

### Farmer memory and typed chat

KrishiMitra keeps consented farmer preferences in the durable SQLite database at
`backend/data/krishimitra.db`. The LiveKit participant identity is used as the database key;
the agent looks it up when a session starts and uses the same `AgentSession` for both spoken
and typed messages. A farmer must explicitly agree before the agent calls the memory save tool.

The browser offers **Start Chat** as well as voice calling. Both paths connect to the same
agent, so they share the active conversation and the saved farmer profile.

To run the local persistence checks:

```bash
uv run pytest tests/test_database.py
```

### Day 6 — Outbound Farm Alert Telephony

KrishiMitra AI can proactively call a farmer via LiveKit SIP telephony using a Linphone SIP
account. The call flow is:

```
KrishiMitra AI → LiveKit Agent Worker → LiveKit SIP Outbound Trunk → Linphone SIP → Farmer's Linphone app
```

#### Environment variables required for Day 6

Add these to `backend/.env.local` (copy from `.env.example`):

| Variable | Description |
|---|---|
| `LIVEKIT_SIP_OUTBOUND_TRUNK_ID` | LiveKit outbound SIP trunk ID (starts with `ST_`) |
| `LINPHONE_SIP_URI` | Your Linphone SIP URI (e.g. `sip:username@sip.linphone.org`) |
| `SIP_OUTBOUND_HOST` | SIP proxy host (e.g. `sip.linphone.org`) |
| `AGENT_NAME` | LiveKit agent name (default: `my-agent`) |

#### How to create the outbound SIP trunk

1. Log in to [LiveKit Cloud](https://cloud.livekit.io/) → **SIP** → **Outbound Trunks**
2. Create a new outbound trunk using your Linphone SIP credentials
3. Copy the trunk ID (starts with `ST_`) into `LIVEKIT_SIP_OUTBOUND_TRUNK_ID`

#### Running an outbound farm alert call

**Terminal 1 — Start the agent worker:**

```bash
cd backend
uv run python src/telephony/outbound/agent.py dev
```

**Terminal 2 — Trigger the outbound call:**

```bash
cd backend
# Scenario 1: Ramesh / Wheat — farmer verifies and acknowledges symptoms
uv run python src/telephony/outbound/dial.py --alert-id 1

# Scenario 2: Suresh / Soybean — farmer verifies but says no symptoms
uv run python src/telephony/outbound/dial.py --alert-id 2

# Scenario 3: Mahesh / Rice — verification fails after 2 attempts
uv run python src/telephony/outbound/dial.py --alert-id 3

# Optional: specify a Linphone username explicitly
uv run python src/telephony/outbound/dial.py --to username --alert-id 1
```

If `--to` is omitted, the dial script reads `LINPHONE_SIP_URI` from the environment.

#### Test scenarios

| Alert ID | Farmer | Crop | Expected flow |
|---|---|---|---|
| 1 | Ramesh Kumar | Wheat | Verifies crop → alert explained → farmer confirms symptoms → status: `confirmed` |
| 2 | Suresh Patel | Soybean | Verifies crop → alert explained → farmer says no symptoms → status: `not_observed` |
| 3 | Mahesh Verma | Rice | Gives wrong crop twice → alert NOT revealed → status: `verification_failed` |

#### Troubleshooting Day 6

| Symptom | Likely cause | File to check |
|---|---|---|
| `MISSING ENVIRONMENT VARIABLES` | `.env.local` not loaded | `src/telephony/outbound/dial.py` lines 41–44 |
| `FARM ALERT NOT FOUND` | Database not seeded | `src/database.py` — run `uv run pytest tests/test_database.py` |
| `Agent dispatch creation notice` | Agent worker not running | Start Terminal 1 before Terminal 2 |
| `SIP OUTBOUND CALL PLACED` but no ring | Wrong trunk ID | Verify `LIVEKIT_SIP_OUTBOUND_TRUNK_ID` in LiveKit Cloud dashboard |
| Linphone not ringing | SIP credentials on trunk | Check Linphone SIP credentials in LiveKit Cloud outbound trunk config |
| Call connects but no audio | Agent not dispatched in time | Re-run Terminal 2 after confirming Terminal 1 shows `connected` |


All configuration lives in [`src/agent.py`](src/agent.py).

### System prompt

The `SYSTEM_PROMPT` constant at the top of `agent.py` controls what your agent does. Change it to build any voice-powered use case.

#### Example prompts

**Customer Support (default):**

```
You are a friendly and efficient customer support agent for a tech company. Help users with account issues, billing questions, and product troubleshooting. Be concise, empathetic, and solution-oriented. If you don't know something, say so honestly and offer to escalate.
```

**Language Tutor:**

```
You are a patient and encouraging language tutor helping the user practice conversational Spanish. Speak primarily in Spanish but switch to English to explain grammar or vocabulary when needed. Correct mistakes gently and suggest better phrasing. Keep conversations natural and fun.
```

**AI Receptionist:**

```
You are a professional receptionist for a medical clinic. Help callers schedule appointments, answer questions about office hours and services, and take messages for doctors. Be warm but efficient. Ask for the caller's name and reason for calling upfront.
```

**Interview Coach:**

```
You are an experienced interview coach. Conduct mock interviews with the user for software engineering roles. Ask one behavioral or technical question at a time, let the user answer fully, then give specific feedback on their response — what was strong, what could improve, and a suggested reframe. Keep the tone encouraging but honest.
```

**Sales Assistant:**

```
You are a knowledgeable sales assistant for an electronics store. Help customers find the right product by asking about their needs, budget, and preferences. Compare options clearly, highlight trade-offs, and make a recommendation. Never be pushy — focus on helping the customer make the best decision for them.
```

**Fitness Coach:**

```
You are an upbeat personal fitness coach. Help users plan workouts, suggest exercises for specific muscle groups, and answer questions about form and technique. Ask about their fitness level and any injuries before recommending exercises. Keep instructions clear and motivating.
```

**Storyteller / Bedtime Narrator:**

```
You are a creative storyteller who tells original bedtime stories for children aged 4–8. Ask the child (or parent) for a character name, a favorite animal, and a setting, then weave a short, calming story. Use vivid but simple language. End each story on a peaceful, sleepy note.
```

**Meeting Summarizer:**

```
You are a meeting assistant. The user will describe what happened in a meeting or read you their notes. Summarize the key decisions, action items (with owners if mentioned), and any open questions. Be concise and structured. Ask clarifying questions if something is ambiguous.
```

**Trivia Game Host:**

```
You are an enthusiastic trivia game host. Ask the user one trivia question at a time from a mix of categories — science, history, pop culture, geography, and sports. Wait for their answer, tell them if they're right or wrong, give a brief fun fact, then move to the next question. Keep score and announce it every 5 questions.
```

**Mental Health Check-in Companion:**

```
You are a gentle, non-clinical wellness companion. Help users talk through their day, reflect on how they're feeling, and practice simple grounding exercises like deep breathing or gratitude lists. You are not a therapist — if the user expresses serious distress or mentions self-harm, gently encourage them to reach out to a professional or crisis helpline.
```

### Voice

Set the `voice` argument in the `murf.TTS(...)` call:

```python
tts=murf.TTS(
    voice="en-US-matthew",    # Change this
    style="Conversation",
    tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
    text_pacing=True
)
```

Some voice options:

| Voice ID | Description                      |
| -------- | -------------------------------- |
| `Anisha` | Indian English, female (default) |
| `Pooja`  | Indian English, female           |
| `Samar`  | Indian English, male             |
| `Amara`  | US English, female               |
| `Hazel`  | UK English, female               |
| `Bertie` | UK English, male                 |
| `Gordon` | US English, male                 |

Browse all 150+ voices: [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library).

### STT (Speech-to-Text)

Default is Deepgram Nova-3. Change in the `AgentSession(stt=...)` call:

```python
stt=deepgram.STT(model="nova-3")
```

### LLM

Default is Google Gemini. To switch:

- **Gemini (default):** Set `GOOGLE_API_KEY` in `.env.local`
- **OpenAI:** Set `OPENAI_API_KEY`, install `livekit-agents[openai]`, and change the `llm=` argument

## Testing

The project includes an eval suite based on the LiveKit Agents [testing framework](https://docs.livekit.io/agents/build/testing/):

```bash
uv run pytest
```

Tests are in [`tests/test_agent.py`](tests/test_agent.py) and use LLM-as-judge evaluations to verify the agent behaves correctly (friendly greetings, grounding, refusing harmful requests).

To run tests in CI, you'll need to add `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` as repository secrets.

## Deployment

### Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/tIVCF1?referralCode=cNjn2P&utm_medium=integration&utm_source=template&utm_campaign=generic)

Set these environment variables in Railway:

- `MURF_API_KEY`
- `DEEPGRAM_API_KEY`
- `GOOGLE_API_KEY`
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`

### Docker

A production-ready [Dockerfile](Dockerfile) is included:

```bash
docker build -t murf-voice-agent .
docker run --env-file .env.local murf-voice-agent
```

## Project Structure

```
backend/
├── src/
│   └── agent.py          # Agent entrypoint — pipeline, prompt, config
├── tests/
│   └── test_agent.py     # LLM-judged eval suite
├── .env.example           # Environment variable template
├── pyproject.toml         # Python dependencies (uv)
├── Dockerfile             # Production container
└── railway.toml           # Railway deploy config
```

## Links

- [Murf Falcon TTS Docs](https://murf.ai/api/docs/text-to-speech/streaming)
- [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library)
- [LiveKit Agents Docs](https://docs.livekit.io/agents)
- [Deepgram Nova-3 Docs](https://developers.deepgram.com)

## License

MIT — see [LICENSE](LICENSE).
