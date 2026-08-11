# KrishiMitra AI Day 6 — Linphone outbound calls

This implementation reuses the existing KrishiMitra agent, Murf Falcon TTS,
Deepgram STT, Gemini LLM, SQLite farmer memory, and LiveKit Cloud project. It
adds an explicit LiveKit SIP call and dispatches `my-agent` only after the call
is answered.

## 1. Linphone setup

1. Create a Linphone/SIP account and note its username.
2. Install Linphone on the phone, sign in with that account, and allow the
   microphone permission.
3. Keep Linphone registered and reachable while testing. If a call connects
   without audio, check the app's media-encryption setting and use the setting
   compatible with your SIP account/provider.

## 2. LiveKit Cloud SIP trunk

In LiveKit Cloud, open **Telephony → SIP Trunks** and create an **outbound**
trunk. Use your own username in this configuration:

```json
{
  "name": "linphone-trunk",
  "address": "sip.linphone.org",
  "transport": "SIP_TRANSPORT_TLS",
  "numbers": ["sip:<YOUR_LINPHONE_USERNAME>"]
}
```

Copy the generated outbound trunk ID. LiveKit project **Settings** contains
`LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.

## 3. Environment

Copy `.env.example` to `.env.local` if needed. Fill in the normal LiveKit,
Murf, Deepgram, and Google values plus:

```dotenv
LIVEKIT_SIP_OUTBOUND_TRUNK_ID=ST_your_existing_outbound_trunk_id
LINPHONE_USERNAME=your_linphone_username
LINPHONE_DOMAIN=sip.linphone.org
AGENT_NAME=my-agent
```

Never add `.env.local`, `.env`, API secrets, or SIP passwords to Git.

## 4. Run the demo from `backend/`

In PowerShell terminal 1:

```powershell
uv sync
uv run python src/telephony/outbound/agent.py dev
```

In PowerShell terminal 2:

```powershell
uv run python src/telephony/outbound/dial.py --to <YOUR_LINPHONE_USERNAME>
```

`--to` also accepts `sip:user@sip.linphone.org` or an E.164 number. Use a
stable farmer ID if you want the same SQLite profile and opt-out state across
different destination formats:

```powershell
uv run python src/telephony/outbound/dial.py --to <YOUR_LINPHONE_USERNAME> --farmer-id farmer-demo-1
```

## 5. What to test

1. Linphone rings and the CLI logs `Waiting for user to answer...`.
2. Answer: KrishiMitra identifies itself as an automated farming assistant,
   explains this is a **local/demo** rain warning, and gives the opt-out words.
3. Ask a short Hindi/Hinglish farming question, for example `Aur kya savdhani
   rakhni chahiye?`.
4. Say `band kijiye` or `call mat karna`. The agent confirms, saves
   `outbound_calls_opted_out` in the existing SQLite farmer facts, and removes
   the SIP participant to end the call.
5. Repeat the same command with the same `--farmer-id`; it should refuse before
   placing another call.

## Common errors

- **Missing LIVEKIT_SIP_OUTBOUND_TRUNK_ID:** copy the outbound trunk ID from
  LiveKit Cloud into `.env.local`.
- **No answer / busy / rejected:** verify the Linphone account is signed in,
  the destination is correct, and the trunk address/transport match the SIP
  provider.
- **Agent does not join:** start terminal 1 first and ensure its registered
  name is `my-agent` (or set `AGENT_NAME` to the matching name).
- **No audio:** verify microphone permission, Linphone registration, SIP media
  encryption compatibility, and the LiveKit trunk's TLS settings.

The unit tests validate configuration parsing, destination validation,
opt-out phrase recognition, SQLite persistence, and the existing local-weather
code. A real SIP call still requires your LiveKit and Linphone credentials.
