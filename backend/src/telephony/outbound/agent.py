"""Outbound Agent Entry Point for KrishiMitra AI.

Usage:
  uv run python src/telephony/outbound/agent.py dev
"""

import sys
from pathlib import Path

# Add parent directory to python path for imports
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from livekit.agents import cli  # noqa: E402

from agent import server  # noqa: E402

if __name__ == "__main__":
    cli.run_app(server)
