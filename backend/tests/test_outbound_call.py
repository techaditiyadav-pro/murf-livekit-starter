import pytest

from telephony.outbound.dial import (
    OutboundCallError,
    validate_configuration,
    validate_destination,
)
from telephony.outbound.policy import is_opt_out_request


def test_accepts_supported_outbound_destinations() -> None:
    assert validate_destination("+919876543210") == "+919876543210"
    assert validate_destination("sip:farmer@example.com") == "farmer"
    assert validate_destination("sips:farmer@example.com") == "farmer"


@pytest.mark.parametrize("destination", ["invalid target with spaces!!"])
def test_rejects_invalid_outbound_destinations(destination: str) -> None:
    with pytest.raises(OutboundCallError, match="Invalid destination"):
        validate_destination(destination)


@pytest.mark.parametrize(
    "phrase",
    [
        "stop",
        "don't call me again",
        "no more calls please",
        "band kijiye",
        "call mat karna",
        "mujhe call nahi chahiye",
        "future calls mat karna",
    ],
)
def test_detects_explicit_opt_out_phrases(phrase: str) -> None:
    assert is_opt_out_request(phrase) is True


def test_does_not_treat_a_weather_question_as_an_opt_out() -> None:
    assert is_opt_out_request("Kitni baarish hogi?") is False


def test_rejects_an_invalid_livekit_url(monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "not-a-url")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    monkeypatch.setenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID", "trunk")

    with pytest.raises(OutboundCallError, match="LIVEKIT_URL must"):
        validate_configuration()
