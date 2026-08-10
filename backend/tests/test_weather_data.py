import csv

from weather_data import WeatherDataClient


def write_dataset(path, rows: list[dict[str, str]]) -> None:
    fields = [
        "district",
        "date",
        "temperature_c",
        "humidity_percent",
        "rain_probability_percent",
        "weather_condition",
        "wind_speed_kmph",
        "farming_advice",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_returns_structured_local_weather_for_normalized_district(tmp_path) -> None:
    dataset = tmp_path / "weather_data.csv"
    write_dataset(
        dataset,
        [
            {
                "district": "Bhopal",
                "date": "2026-08-10",
                "temperature_c": "28",
                "humidity_percent": "72",
                "rain_probability_percent": "65",
                "weather_condition": "Cloudy",
                "wind_speed_kmph": "14",
                "farming_advice": "Plan outdoor work carefully due to possible rain.",
            }
        ],
    )

    result = WeatherDataClient(dataset).get_weather_by_district("BHOPAL")

    assert result == {
        "status": "success",
        "district": "Bhopal",
        "date": "2026-08-10",
        "temperature_c": 28,
        "humidity_percent": 72,
        "rain_probability_percent": 65,
        "weather_condition": "Cloudy",
        "wind_speed_kmph": 14,
        "farming_advice": "Plan outdoor work carefully due to possible rain.",
        "data_source": "LOCAL/DEMO DATA — NOT LIVE WEATHER",
    }


def test_returns_not_found_for_unsupported_district(tmp_path) -> None:
    dataset = tmp_path / "weather_data.csv"
    write_dataset(
        dataset,
        [
            {
                "district": "Bhopal",
                "date": "2026-08-10",
                "temperature_c": "28",
                "humidity_percent": "72",
                "rain_probability_percent": "65",
                "weather_condition": "Cloudy",
                "wind_speed_kmph": "14",
                "farming_advice": "Plan outdoor work carefully due to possible rain.",
            }
        ],
    )

    result = WeatherDataClient(dataset).get_weather_by_district("Delhi")

    assert result["status"] == "not_found"
    assert "Delhi" in result["message"]


def test_returns_unavailable_when_dataset_is_missing(tmp_path) -> None:
    result = WeatherDataClient(tmp_path / "weather_data.csv").get_weather_by_district(
        "Bhopal"
    )

    assert result["status"] == "unavailable"
    assert "weather data" in result["message"]


def test_returns_unavailable_when_dataset_is_empty(tmp_path) -> None:
    dataset = tmp_path / "weather_data.csv"
    write_dataset(dataset, [])

    result = WeatherDataClient(dataset).get_weather_by_district("Bhopal")

    assert result["status"] == "unavailable"


def test_returns_unavailable_for_malformed_data(tmp_path) -> None:
    dataset = tmp_path / "weather_data.csv"
    dataset.write_text("district,date\nBhopal,2026-08-10\n", encoding="utf-8")

    result = WeatherDataClient(dataset).get_weather_by_district("Bhopal")

    assert result["status"] == "unavailable"
