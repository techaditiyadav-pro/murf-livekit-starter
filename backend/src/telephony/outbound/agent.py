"""Run the existing KrishiMitra agent worker for Day 6 outbound calls."""

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from livekit.agents import cli  # noqa: E402

from agent import server  # noqa: E402

if __name__ == "__main__":
    cli.run_app(server)
