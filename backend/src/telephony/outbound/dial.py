"""
KrishiMitra - Day 6 Outbound Weather Alert Call

Places a consent-based outbound SIP call to the
anushkadubey12 Linphone account using LiveKit SIP.

IMPORTANT:
LiveKit sip_call_to expects a SIP USER or phone number,
not a complete SIP URI.

Target:
    Linphone username: anushkadubey12
    SIP domain: sip.linphone.org
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from livekit import api


# ============================================================
# PATH CONFIGURATION
# ============================================================

SOURCE_ROOT = Path(__file__).resolve().parents[2]

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

BACKEND_ROOT = Path(__file__).resolve().parents[3]


# ============================================================
# DATABASE
# ============================================================

from database import FarmerRepository


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger("krishimitra.outbound")


# ============================================================
# FIXED LINPHONE DESTINATION
# ============================================================

LINPHONE_USERNAME = "anushkadubey12"
LINPHONE_DOMAIN = "sip.linphone.org"

# LiveKit sip_call_to MUST receive only:
# anushkadubey12
#
# NOT:
# sip:anushkadubey12@sip.linphone.org

SIP_CALL_TO = LINPHONE_USERNAME

FULL_SIP_URI = (
    f"sip:{LINPHONE_USERNAME}@{LINPHONE_DOMAIN}"
)


# ============================================================
# CONSTANTS
# ============================================================

E164_NUMBER = re.compile(
    r"^\+[1-9]\d{7,14}$"
)

SIP_ADDRESS = re.compile(
    r"^sips?:[^\s@]+@[^\s@]+$",
    re.IGNORECASE,
)


OUTBOUND_ALERT_METADATA = {
    "outbound": True,
    "type": "weather_alert",
    "project": "KrishiMitra",
}


# ============================================================
# RESULT / ERROR CLASSES
# ============================================================

class OutboundCallError(RuntimeError):
    """Developer-actionable outbound call error."""


@dataclass(frozen=True)
class OutboundCallResult:
    room_name: str
    participant_identity: str


# ============================================================
# ENVIRONMENT
# ============================================================

def load_environment() -> None:
    """
    Load backend/.env first and backend/.env.local second.
    .env.local overrides .env.
    """

    load_dotenv(
        BACKEND_ROOT / ".env"
    )

    load_dotenv(
        BACKEND_ROOT / ".env.local",
        override=True,
    )


# ============================================================
# DESTINATION VALIDATION
# ============================================================

def validate_destination(
    destination: str | None = None,
) -> str:
    """
    Always normalize the destination to the SIP username.

    For this project the target is:

        anushkadubey12

    Full SIP URI is accepted as input, but converted to
    the username before being passed to LiveKit.
    """

    # If nothing is provided, use the fixed target.
    if not destination:
        return SIP_CALL_TO

    value = destination.strip()

    if not value:
        return SIP_CALL_TO

    # --------------------------------------------------------
    # E.164 phone number
    # --------------------------------------------------------

    if E164_NUMBER.fullmatch(value):
        return value

    # --------------------------------------------------------
    # Full SIP URI
    # --------------------------------------------------------

    if SIP_ADDRESS.fullmatch(value):

        without_scheme = re.sub(
            r"^sips?:",
            "",
            value,
            flags=re.IGNORECASE,
        )

        username = (
            without_scheme
            .split("@", 1)[0]
            .strip()
        )

        if username:
            return username

    # --------------------------------------------------------
    # Plain SIP username
    # --------------------------------------------------------

    if re.fullmatch(
        r"[A-Za-z0-9._-]+",
        value,
    ):
        return value

    raise OutboundCallError(
        "Invalid destination. "
        "Use an SIP username such as "
        "anushkadubey12."
    )


# ============================================================
# REQUIRED ENVIRONMENT HELPER
# ============================================================

def _required_environment(
    name: str,
) -> str:

    value = os.getenv(
        name,
        "",
    ).strip()

    if not value:

        raise OutboundCallError(
            f"Missing {name}. "
            f"Add it to backend/.env.local."
        )

    return value


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================

def validate_configuration() -> str:

    livekit_url = _required_environment(
        "LIVEKIT_URL"
    )

    if not livekit_url.startswith(
        (
            "ws://",
            "wss://",
            "http://",
            "https://",
        )
    ):

        raise OutboundCallError(
            "LIVEKIT_URL must start with "
            "ws://, wss://, http:// or https://."
        )

    _required_environment(
        "LIVEKIT_API_KEY"
    )

    _required_environment(
        "LIVEKIT_API_SECRET"
    )

    # Support both variable names.
    trunk_id = (
        os.getenv(
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID",
            "",
        ).strip()
        or os.getenv(
            "LIVEKIT_OUTBOUND_TRUNK_ID",
            "",
        ).strip()
    )

    if not trunk_id:

        raise OutboundCallError(
            "Missing LIVEKIT_SIP_OUTBOUND_TRUNK_ID "
            "or LIVEKIT_OUTBOUND_TRUNK_ID."
        )

    return trunk_id


# ============================================================
# MAIN OUTBOUND CALL
# ============================================================

async def make_outbound_call(
    destination: str | None = None,
    *,
    farmer_id: str | None = None,
) -> OutboundCallResult:

    # --------------------------------------------------------
    # Step 1: Normalize destination
    # --------------------------------------------------------

    destination = validate_destination(
        destination
    )

    # --------------------------------------------------------
    # Safety check:
    # Make sure we are calling the intended account.
    # --------------------------------------------------------

    if destination != LINPHONE_USERNAME:

        raise OutboundCallError(
            "This KrishiMitra demo is configured to call "
            f"{LINPHONE_USERNAME}. "
            f"Received destination: {destination}"
        )

    # --------------------------------------------------------
    # Step 2: Validate LiveKit configuration
    # --------------------------------------------------------

    trunk_id = validate_configuration()

    agent_name = (
        os.getenv(
            "AGENT_NAME",
            "my-agent",
        ).strip()
        or "my-agent"
    )

    # Farmer ID
    farmer_id = (
        farmer_id
        or destination
    ).strip()

    # --------------------------------------------------------
    # Step 3: Check opt-out
    # --------------------------------------------------------

    repository = FarmerRepository()

    if repository.has_outbound_opt_out(
        farmer_id
    ):

        raise OutboundCallError(
            "This farmer has opted out. "
            "No outbound call was placed."
        )

    # --------------------------------------------------------
    # Step 4: Create unique room
    # --------------------------------------------------------

    room_name = (
        "krishimitra-alert-"
        f"{uuid.uuid4().hex[:12]}"
    )

    # --------------------------------------------------------
    # Logging
    # --------------------------------------------------------

    logger.info("=" * 65)

    logger.info(
        "KrishiMitra - Outbound Weather Alert Call"
    )

    logger.info("=" * 65)

    logger.info(
        "Linphone Account: %s",
        FULL_SIP_URI,
    )

    logger.info(
        "LiveKit sip_call_to: %s",
        SIP_CALL_TO,
    )

    logger.info(
        "Farmer ID: %s",
        farmer_id,
    )

    logger.info(
        "Room: %s",
        room_name,
    )

    logger.info(
        "Agent: %s",
        agent_name,
    )

    logger.info(
        "SIP Trunk: %s",
        trunk_id,
    )

    logger.info("=" * 65)

    # --------------------------------------------------------
    # Step 5: LiveKit credentials
    # --------------------------------------------------------

    livekit_url = _required_environment(
        "LIVEKIT_URL"
    )

    livekit_api_key = _required_environment(
        "LIVEKIT_API_KEY"
    )

    livekit_api_secret = _required_environment(
        "LIVEKIT_API_SECRET"
    )

    # --------------------------------------------------------
    # LiveKit API
    # --------------------------------------------------------

    async with api.LiveKitAPI(
        url=livekit_url,
        api_key=livekit_api_key,
        api_secret=livekit_api_secret,
    ) as client:

        try:

            # ==================================================
            # STEP 1 - CREATE ROOM
            # ==================================================

            logger.info(
                "[STEP 1] Creating LiveKit room..."
            )

            await client.room.create_room(
                api.CreateRoomRequest(
                    name=room_name
                )
            )

            logger.info(
                "[OK] Room created: %s",
                room_name,
            )

            # ==================================================
            # STEP 2 - DISPATCH AGENT
            # ==================================================

            logger.info(
                "[STEP 2] Dispatching KrishiMitra agent..."
            )

            dispatch_request = (
                api.CreateAgentDispatchRequest(
                    agent_name=agent_name,
                    room=room_name,
                    metadata=json.dumps(
                        OUTBOUND_ALERT_METADATA
                    ),
                )
            )

            dispatch = (
                await client.agent_dispatch.create_dispatch(
                    dispatch_request
                )
            )

            logger.info(
                "[OK] Agent dispatched: %s",
                dispatch.id,
            )

            # ==================================================
            # STEP 3 - CREATE SIP PARTICIPANT
            # ==================================================

            logger.info(
                "[STEP 3] Creating outbound SIP call..."
            )

            # --------------------------------------------------
            # VERY IMPORTANT
            #
            # LiveKit receives:
            #
            #     sip_call_to="anushkadubey12"
            #
            # NOT:
            #
            #     sip_call_to="sip:anushkadubey12@sip.linphone.org"
            # --------------------------------------------------

            logger.info(
                "[DEBUG] SIP destination user: %s",
                SIP_CALL_TO,
            )

            sip_request = (
                api.CreateSIPParticipantRequest(

                    sip_trunk_id=trunk_id,

                    # THE IMPORTANT FIX
                    sip_call_to=SIP_CALL_TO,

                    room_name=room_name,

                    participant_identity=(
                        f"learner-{LINPHONE_USERNAME}"
                    ),

                    participant_name=(
                        "KrishiMitra Farmer"
                    ),

                    display_name=(
                        "KrishiMitra AI"
                    ),

                    participant_attributes={
                        "krishimitra.outbound_alert":
                            "weather",

                        "krishimitra.farmer_id":
                            farmer_id,
                    },

                    # LiveKit expects timedelta.
                    ringing_timeout=timedelta(
                        seconds=30
                    ),

                    max_call_duration=timedelta(
                        seconds=300
                    ),

                    wait_until_answered=True,

                    play_dialtone=True,
                )
            )

            # --------------------------------------------------
            # Send SIP request
            # --------------------------------------------------

            sip_info = (
                await client.sip.create_sip_participant(
                    sip_request,
                    timeout=45,
                )
            )

            # ==================================================
            # STEP 4 - ANSWERED
            # ==================================================

            logger.info(
                "[SUCCESS] Outbound SIP call answered!"
            )

            logger.info(
                "[SUCCESS] Participant: %s",
                sip_info.participant_identity,
            )

            logger.info(
                "[SUCCESS] SIP Call ID: %s",
                sip_info.sip_call_id,
            )

            logger.info(
                "[KrishiMitra] Farmer connected."
            )

            logger.info(
                "[KrishiMitra] Weather alert conversation started."
            )

            logger.info(
                "[KrishiMitra] Agent is now handling the call."
            )

            return OutboundCallResult(
                room_name=room_name,
                participant_identity=(
                    sip_info.participant_identity
                ),
            )

        except Exception as error:

            logger.exception(
                "[KrishiMitra] Outbound SIP call failed."
            )

            raise OutboundCallError(
                "LiveKit could not complete the "
                "outbound call.\n\n"
                "Target:\n"
                f"  {FULL_SIP_URI}\n\n"
                "LiveKit sip_call_to:\n"
                f"  {SIP_CALL_TO}\n\n"
                "Possible causes:\n"
                "- anushkadubey12 is not registered in Linphone\n"
                "- Linphone app is offline\n"
                "- SIP trunk configuration is incorrect\n"
                "- Invalid LiveKit SIP trunk ID\n"
                "- LiveKit credentials are incorrect\n"
                "- SIP provider rejected the call\n\n"
                f"API error: {error}"
            ) from error


# ============================================================
# CLI
# ============================================================

def main() -> None:

    load_environment()

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s - "
            "%(name)s - "
            "%(levelname)s - "
            "%(message)s"
        ),
    )

    parser = argparse.ArgumentParser(
        description=(
            "KrishiMitra outbound weather alert "
            "call to anushkadubey12."
        )
    )

    parser.add_argument(
        "--to",
        default=LINPHONE_USERNAME,
        help=(
            "Linphone username. "
            "Default: anushkadubey12"
        ),
    )

    parser.add_argument(
        "--farmer-id",
        default=LINPHONE_USERNAME,
        help=(
            "Stable farmer ID used for "
            "memory and opt-out checks."
        ),
    )

    args = parser.parse_args()

    result = asyncio.run(
        make_outbound_call(
            args.to,
            farmer_id=args.farmer_id,
        )
    )

    print()
    print("=" * 65)
    print(
        "KrishiMitra outbound call is active"
    )
    print("=" * 65)

    print(
        f"Target: {FULL_SIP_URI}"
    )

    print(
        f"LiveKit sip_call_to: {SIP_CALL_TO}"
    )

    print(
        f"Room: {result.room_name}"
    )

    print(
        f"Participant: "
        f"{result.participant_identity}"
    )

    print("=" * 65)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except OutboundCallError as error:

        logger.error(
            "[KrishiMitra] %s",
            error,
        )

        sys.exit(1)