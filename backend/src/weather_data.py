"""Local/demo weather lookup for KrishiMitra AI Day 5."""

import csv
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent.weather_data")

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "weather_data.csv"
REQUIRED_COLUMNS = {
    "district",
    "date",
    "temperature_c",
    "humidity_percent",
    "rain_probability_percent",
    "weather_condition",
    "wind_speed_kmph",
    "farming_advice",
}
DISTRICT_ALIASES = {
    "\u092d\u094b\u092a\u093e\u0932": "Bhopal",
    "\u0907\u0902\u0926\u094c\u0930": "Indore",
    "\u091c\u092c\u0932\u092a\u0941\u0930": "Jabalpur",
    "\u0917\u094d\u0935\u093e\u0932\u093f\u092f\u0930": "Gwalior",
    "\u0938\u093e\u0917\u0930": "Sagar",
    "\u0909\u091c\u094d\u091c\u0948\u0928": "Ujjain",
    "\u0930\u0940\u0935\u093e": "Rewa",
    "\u0938\u0924\u0928\u093e": "Satna",
    "\u0935\u093f\u0926\u093f\u0936\u093e": "Vidisha",
    "\u0928\u0930\u094d\u092e\u0926\u093e\u092a\u0941\u0930\u092e": "Narmadapuram",
}


class WeatherDataClient:
    """Read one district's weather record from the checked-in demo CSV."""

    def __init__(self, dataset_path: Path = DATASET_PATH) -> None:
        self.dataset_path = dataset_path

    def get_weather_by_district(self, district: str) -> dict[str, Any]:
        district = district.strip()
        if not district:
            return self._not_found_result("that district")

        canonical_district = DISTRICT_ALIASES.get(district.casefold(), district.title())
        logger.info("Weather tool called: district=%s", canonical_district)
        try:
            with self.dataset_path.open(newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(
                    reader.fieldnames
                ):
                    logger.warning("Weather dataset has missing or invalid columns")
                    return self._unavailable_result()
                rows = list(reader)
        except (OSError, csv.Error, UnicodeDecodeError):
            logger.exception("Weather dataset could not be read")
            return self._unavailable_result()

        if not rows:
            logger.warning("Weather dataset is empty")
            return self._unavailable_result()

        row = next(
            (
                item
                for item in rows
                if item.get("district", "").casefold() == canonical_district.casefold()
            ),
            None,
        )
        if row is None:
            logger.info("No local weather record found: district=%s", canonical_district)
            return self._not_found_result(canonical_district)

        try:
            result = {
                "status": "success",
                "district": row["district"],
                "date": row["date"],
                "temperature_c": int(row["temperature_c"]),
                "humidity_percent": int(row["humidity_percent"]),
                "rain_probability_percent": int(row["rain_probability_percent"]),
                "weather_condition": row["weather_condition"],
                "wind_speed_kmph": int(row["wind_speed_kmph"]),
                "farming_advice": row["farming_advice"],
                "data_source": "LOCAL/DEMO DATA — NOT LIVE WEATHER",
            }
        except (KeyError, TypeError, ValueError):
            logger.warning("Weather dataset has an invalid record")
            return self._unavailable_result()

        logger.info("Local weather data received: district=%s, date=%s", result["district"], result["date"])
        return result

    @staticmethod
    def _not_found_result(district: str) -> dict[str, str]:
        return {
            "status": "not_found",
            "message": (
                f"No local demo weather data was found for {district}. Do not guess "
                "weather values."
            ),
        }

    @staticmethod
    def _unavailable_result() -> dict[str, str]:
        return {
            "status": "unavailable",
            "message": (
                "Local weather data is unavailable, so weather cannot be confirmed "
                "right now. Do not guess weather values."
            ),
        }
