"""Safe placeholder for mandi data until a verified provider is configured."""

from __future__ import annotations


class MarketDataClient:
    """Returns an explicit unavailable result instead of estimating a price."""

    def get_market_price(self, crop: str, mandi: str) -> dict[str, str]:
        return {
            "status": "unavailable",
            "crop": crop,
            "mandi": mandi,
            "message": (
                "No verified current mandi-price source is configured for this "
                "project. Do not estimate or invent a price."
            ),
        }
