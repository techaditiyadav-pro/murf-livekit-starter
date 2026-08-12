"""Outbound SIP Dialing Script for KrishiMitra AI.

Initiates a LiveKit SIP outbound call to a farmer using Linphone SIP trunking.

Usage:
  uv run python src/telephony/outbound/dial.py --alert-id 1
  uv run python src/telephony/outbound/dial.py --to username --alert-id 2
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to sys.path for database imports
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import livekit.api as api  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from database import (  # noqa: E402
    get_farm_alert,
    record_call_attempt,
    update_farm_alert,
)

# Setup logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("outbound_dial")

# Load environment variables from backend/.env.local or root .env.local
ENV_LOCAL = SRC_DIR.parent / ".env.local"
if ENV_LOCAL.exists():
    load_dotenv(ENV_LOCAL)
else:
    load_dotenv()


def format_sip_destination(raw_destination: str | None = None) -> str:
    """Format target destination into a valid SIP URI using environment defaults."""
    if not raw_destination:
        env_uri = os.getenv("LINPHONE_SIP_URI")
        if env_uri:
            return env_uri.strip()
        host = os.getenv("SIP_OUTBOUND_HOST", "sip.linphone.org")
        return f"sip:demo@{host}"

    raw = raw_destination.strip()
    if raw.startswith("sip:"):
        return raw

    if "@" in raw:
        return f"sip:{raw}"

    host = os.getenv("SIP_OUTBOUND_HOST", "sip.linphone.org")
    return f"sip:{raw}@{host}"


async def initiate_outbound_call(
    destination: str | None = None,
    alert_id: int = 1,
    custom_room: str | None = None,
) -> bool:
    """Initiate an outbound LiveKit SIP call and assign KrishiMitra AI agent worker."""
    logger.info("==================================================")
    logger.info("  🌾 KrishiMitra AI — Outbound SIP Call Dispatch  ")
    logger.info("==================================================")

    # 1. Validate Environment Variables safely
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    trunk_id = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID") or os.getenv(
        "LIVEKIT_OUTBOUND_TRUNK_ID"
    )
    agent_name = os.getenv("AGENT_NAME", "my-agent")
    linphone_uri = os.getenv("LINPHONE_SIP_URI")
    sip_host = os.getenv("SIP_OUTBOUND_HOST", "sip.linphone.org")

    logger.info("🔍 Environment Configuration Check:")
    logger.info(
        "   LIVEKIT_URL                  : %s",
        "configured" if livekit_url else "MISSING",
    )
    logger.info(
        "   LIVEKIT_API_KEY              : %s", "configured" if api_key else "MISSING"
    )
    logger.info(
        "   LIVEKIT_API_SECRET           : %s",
        "configured" if api_secret else "MISSING",
    )
    logger.info(
        "   LIVEKIT_SIP_OUTBOUND_TRUNK_ID: %s", trunk_id if trunk_id else "MISSING"
    )
    logger.info(
        "   LINPHONE_SIP_URI             : %s",
        "configured" if linphone_uri else "MISSING",
    )
    logger.info("   SIP_OUTBOUND_HOST            : %s", sip_host)
    logger.info("   AGENT_NAME                   : %s", agent_name)

    missing_env = []
    if not livekit_url:
        missing_env.append("LIVEKIT_URL")
    if not api_key:
        missing_env.append("LIVEKIT_API_KEY")
    if not api_secret:
        missing_env.append("LIVEKIT_API_SECRET")
    if not trunk_id:
        missing_env.append("LIVEKIT_SIP_OUTBOUND_TRUNK_ID")

    if missing_env:
        logger.error("❌ MISSING ENVIRONMENT VARIABLES: %s", ", ".join(missing_env))
        logger.error(
            "Please ensure LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and "
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID are set in backend/.env.local"
        )
        return False

    # 2. Fetch Farm Alert Record from Database
    alert = get_farm_alert(alert_id)
    if not alert:
        logger.error("❌ FARM ALERT NOT FOUND for alert_id=%s", alert_id)
        logger.error("Please specify a valid demo alert ID (e.g. 1, 2, or 3).")
        return False

    sip_to = format_sip_destination(destination)
    room_name = custom_room or f"outbound-alert-{alert_id}-{int(time.time())}"
    farmer_name = alert["farmer_name"]
    crop = alert["crop"]
    alert_type = alert["alert_type"]

    logger.info("📋 Target Farmer      : %s (%s)", farmer_name, alert["village"])
    logger.info("🌾 Target Crop        : %s", crop)
    logger.info("⚠️  Alert Type        : %s", alert_type)
    logger.info("📞 Destination SIP    : %s", sip_to)
    logger.info("🔑 Outbound Trunk ID  : %s", trunk_id)
    logger.info("🏠 LiveKit Room Name  : %s", room_name)
    logger.info("🤖 Agent Worker Name  : %s", agent_name)

    # 3. Record Call Attempt in Database
    record_call_attempt(alert_id, f"Initiating dial to {sip_to}")

    # 4. Initiate Call via LiveKit API Client
    try:
        async with api.LiveKitAPI(livekit_url, api_key, api_secret) as lkapi:
            # Step A: Dispatch Agent to the room
            logger.info(
                "🔄 Dispatching agent worker '%s' to room '%s'...",
                agent_name,
                room_name,
            )
            dispatch_req = api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=json.dumps(
                    {
                        "alert_id": alert_id,
                        "call_mode": "outbound_farm_alert",
                        "farmer_name": farmer_name,
                    }
                ),
            )
            try:
                dispatch = await lkapi.agent_dispatch.create_dispatch(dispatch_req)
                logger.info(
                    "✅ Agent Dispatch Created Successfully! (ID: %s)",
                    getattr(dispatch, "id", "created"),
                )
            except Exception as dispatch_err:
                logger.warning(
                    "⚠️  Agent dispatch creation notice: %s. Proceeding with SIP participant creation...",
                    dispatch_err,
                )

            # Step B: Create Outbound SIP Participant
            logger.info(
                "📞 Calling SIP destination '%s' via trunk '%s'...", sip_to, trunk_id
            )
            sip_req = api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=sip_to,
                room_name=room_name,
                participant_identity=f"farmer_{alert_id}",
                participant_name=farmer_name,
                participant_attributes={
                    "alert_id": str(alert_id),
                    "call_mode": "outbound_farm_alert",
                },
                participant_metadata=json.dumps(
                    {
                        "alert_id": alert_id,
                        "call_mode": "outbound_farm_alert",
                        "farmer_name": farmer_name,
                    }
                ),
                play_dialtone=True,
            )

            sip_info = await lkapi.sip.create_sip_participant(sip_req)
            sip_participant_id = getattr(sip_info, "participant_id", "created")
            logger.info("🎉 SIP OUTBOUND CALL PLACED SUCCESSFULLY!")
            logger.info("   SIP Participant ID : %s", sip_participant_id)
            logger.info("   Room Name          : %s", room_name)
            logger.info("   Status             : Call dispatched to Linphone target")

            # Update DB last call outcome
            update_farm_alert(
                alert_id,
                status=alert["status"],
                notes=alert.get("notes", ""),
                last_call_outcome=f"Dialing active: call placed to {sip_to}",
            )
            return True

    except Exception as exc:
        logger.exception("❌ OUTBOUND SIP DIAL FAILED: %s", exc)
        update_farm_alert(
            alert_id,
            status=alert["status"],
            notes=alert.get("notes", ""),
            last_call_outcome=f"Dialing failed: {exc}",
        )
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="KrishiMitra AI — Outbound Farm Alert Telephony Dial Command"
    )
    parser.add_argument(
        "--to",
        type=str,
        default=None,
        help="Target Linphone username or full SIP URI. Defaults to LINPHONE_SIP_URI from environment.",
    )
    parser.add_argument(
        "--alert-id",
        type=int,
        default=1,
        help="Demo Farm Alert ID to load from database (1: Wheat/LeafRust, 2: Soybean/Pest, 3: Rice/Irrigation)",
    )
    parser.add_argument(
        "--room",
        type=str,
        default=None,
        help="Optional custom LiveKit room name for the session",
    )

    args = parser.parse_args()

    success = asyncio.run(
        initiate_outbound_call(
            destination=args.to,
            alert_id=args.alert_id,
            custom_room=args.room,
        )
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
