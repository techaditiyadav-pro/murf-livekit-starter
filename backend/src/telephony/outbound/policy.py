"""Deterministic recognition of explicit outbound-call opt-out requests."""

import re

OPT_OUT_PATTERNS = (
    r"\bstop\b",
    r"\bdon'?t call me\b",
    r"\bno more calls?\b",
    r"\bband kijiye\b",
    r"\bcall mat karna\b",
    r"\bmujhe call nahi chahiye\b",
    r"\bfuture calls? mat karna\b",
)


def is_opt_out_request(text: str) -> bool:
    """Return true only for a clear request to stop future outbound calls."""
    normalized = " ".join(text.casefold().split())
    return any(re.search(pattern, normalized) for pattern in OPT_OUT_PATTERNS)
