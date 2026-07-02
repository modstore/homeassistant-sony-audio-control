"""Tests for source list parsing, source selection and source icons."""
from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

# Mock DataUpdateCoordinator before importing coordinator
_ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
_ha_helpers_update_coordinator.UpdateFailed = Exception

class _Subscriptable(type):
    def __getitem__(cls, item):
        return cls

class _MockDataUpdateCoordinator(metaclass=_Subscriptable):
    def __init__(self, hass, logger, name=None, update_interval=None, update_method=None, request_refresh_debouncer=None):
        self.hass = hass
        self.name = name
        self.update_interval = update_interval

_ha_helpers_update_coordinator.DataUpdateCoordinator = _MockDataUpdateCoordinator
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_helpers_update_coordinator
sys.modules["homeassistant"] = ModuleType("homeassistant")
sys.modules["homeassistant.core"] = ModuleType("homeassistant.core")
sys.modules["homeassistant.helpers"] = ModuleType("homeassistant.helpers")

from custom_components.sony_audio_control.coordinator import _source_icon  # noqa: E402
from custom_components.sony_audio_control.sony.client import SonyAudioClient  # noqa: E402


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
async def test_get_av_sources_parses_source_list() -> None:
    sources = [
        {"source": "extInput:hdmi?port=1", "title": "HDMI1", "meta": "meta:hdmi1"},
        {"source": "extInput:hdmi?port=2", "title": "HDMI2", "meta": "meta:hdmi2"},
        {"source": "extInput:tv", "title": "TV", "meta": "meta:tv"},
        {"source": "extInput:bt", "title": "Bluetooth", "meta": "meta:bt"},
    ]
    session = FakeSession([{"id": 1, "result": [sources]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_av_sources()

    assert len(result) == 4
    assert result[0]["source"] == "extInput:hdmi?port=1"
    assert result[0]["title"] == "HDMI1"
    req = session.requests[0]
    assert req[1]["method"] == "getSourceList"


@pytest.mark.asyncio
async def test_get_av_sources_returns_empty_on_error() -> None:
    session = FakeSession([{"id": 1, "error": [12, "Unsupported"]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_av_sources()

    assert result == []
    assert "getSourceList" in client.failed_methods


@pytest.mark.asyncio
async def test_source_list_in_state() -> None:
    from custom_components.sony_audio_control.sony.models import SonySource, SonyState

    sources = [
        SonySource(uri="extInput:hdmi?port=1", title="HDMI1"),
        SonySource(uri="extInput:tv", title="TV"),
    ]
    state = SonyState(sources=sources)
    assert len(state.sources) == 2
    assert state.sources[0].title == "HDMI1"


def test_source_icon_mapping() -> None:
    assert _source_icon("TV") == "mdi:television"
    assert _source_icon("Bluetooth Audio") == "mdi:bluetooth"
    assert _source_icon("USB") == "mdi:usb"
    assert _source_icon("HDMI1") == "mdi:video-input-hdmi"
    assert _source_icon("Network") == "mdi:lan"
    assert _source_icon("Spotify") == "mdi:spotify"
    assert _source_icon("FM Tuner") is None


def test_source_icon_case_insensitive() -> None:
    assert _source_icon("hdmi2") == "mdi:video-input-hdmi"
    assert _source_icon("BLUETOOTH") == "mdi:bluetooth"
    assert _source_icon("tv") == "mdi:television"
