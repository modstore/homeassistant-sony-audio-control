"""Tests for API timing and discovery tracking."""
from __future__ import annotations

from typing import Any

import pytest

from custom_components.sony_audio_control.sony.client import SonyAudioClient
from custom_components.sony_audio_control.sony.exceptions import SonyAudioApiError


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self._data = data

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self, content_type: str | None = None) -> Any:
        return self._data


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
        self.requests.append((url, json))
        return FakeResponse(self.responses.pop(0))


@pytest.mark.asyncio
async def test_api_timing_recorded_on_success() -> None:
    session = FakeSession([{"id": 1, "result": [{"status": "active"}]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    await client.power_status()

    assert "getPowerStatus" in client.successful_methods
    assert "getPowerStatus" not in client.failed_methods
    assert "getPowerStatus" in client.api_timings
    timing = client.api_timings["getPowerStatus"]
    assert timing["method"] == "getPowerStatus"
    assert isinstance(timing["duration_ms"], int)
    assert timing["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_api_timing_recorded_on_api_error() -> None:
    session = FakeSession([{"id": 1, "error": [12, "Unsupported"]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    with pytest.raises(SonyAudioApiError):
        await client.call("system", "getPowerStatus")

    assert "getPowerStatus" in client.failed_methods
    assert "getPowerStatus" not in client.successful_methods
    assert "getPowerStatus" in client.api_timings
    assert client.api_timings["getPowerStatus"]["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_api_timing_recorded_on_connection_error() -> None:
    class BadResponse:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        def raise_for_status(self):
            raise ConnectionError("Network unreachable")
        async def json(self, content_type=None):
            return {}

    class BadSession:
        def post(self, url, json):
            return BadResponse()

    client = SonyAudioClient(BadSession(), "192.168.1.14")  # type: ignore[arg-type]

    # call() directly should raise because connection errors are not caught by try_call
    from custom_components.sony_audio_control.sony.exceptions import SonyAudioConnectionError

    with pytest.raises(SonyAudioConnectionError):
        await client.call("system", "getPowerStatus")

    assert "getPowerStatus" in client.failed_methods
    assert "getPowerStatus" in client.api_timings


@pytest.mark.asyncio
async def test_sony_error_codes_recorded() -> None:
    session = FakeSession([{"id": 1, "error": [12, "Unsupported"]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    with pytest.raises(SonyAudioApiError):
        await client.call("system", "getPowerStatus")

    assert len(client.sony_error_codes) == 1
    assert client.sony_error_codes[0]["method"] == "getPowerStatus"
    assert client.sony_error_codes[0]["error"] == [12, "Unsupported"]


@pytest.mark.asyncio
async def test_try_call_does_not_raise_and_tracks_failure() -> None:
    session = FakeSession([{"id": 1, "error": [12, "Unsupported"]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.try_call("system", "getPowerStatus")

    assert result is None
    assert "getPowerStatus" in client.failed_methods
    assert "getPowerStatus" in client.api_timings


@pytest.mark.asyncio
async def test_successful_methods_accumulate() -> None:
    session = FakeSession([
        {"id": 1, "result": [{"status": "active"}]},
        {"id": 2, "result": [[{"target": "", "volume": 30, "mute": "off"}]]},
    ])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    await client.power_status()
    await client.volume_information()

    assert "getPowerStatus" in client.successful_methods
    assert "getVolumeInformation" in client.successful_methods
    assert len(client.api_timings) == 2
