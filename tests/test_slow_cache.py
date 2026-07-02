"""Tests for coordinator slow cache behavior."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock

import pytest

# Minimal mocks for Home Assistant
_ha = ModuleType("homeassistant")
_ha.core = ModuleType("homeassistant.core")
_ha.core.HomeAssistant = type("HomeAssistant", (), {})
_ha_helpers = ModuleType("homeassistant.helpers")
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
_ha_helpers.update_coordinator = _ha_helpers_update_coordinator

sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.helpers"] = _ha_helpers
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_helpers_update_coordinator

# Remove cached coordinator module so it re-imports with our mock
if "custom_components.sony_audio_control.coordinator" in sys.modules:
    del sys.modules["custom_components.sony_audio_control.coordinator"]

from custom_components.sony_audio_control.coordinator import SonyAudioCoordinator  # noqa: E402
from custom_components.sony_audio_control.sony.models import SonySystem  # noqa: E402


class FakeClient:
    def __init__(self):
        self.host = "192.168.1.14"
        self.port = 10000
        self.get_speaker_settings = AsyncMock(return_value={})
        self.get_sound_settings = AsyncMock(return_value={})
        self.get_volume = AsyncMock(return_value=None)
        self.power_status = AsyncMock(return_value={"status": "active"})
        self.playing_content_info = AsyncMock(return_value={"uri": "extInput:hdmi?port=1", "source": "HDMI1"})
        self.supported_api_info = AsyncMock(return_value={"services": []})
        self.get_system = AsyncMock(return_value=SonySystem(mac="38:18:4c:4e:e1:d5", firmware="M41.R.0518", raw={"modelName": "STR-DN1080"}))
        self.get_av_sources = AsyncMock(return_value=[
            {"source": "extInput:hdmi?port=1", "title": "HDMI1"},
            {"source": "extInput:hdmi?port=2", "title": "HDMI2"},
        ])
        self.api_timings = {}
        self.successful_methods = set()
        self.failed_methods = set()
        self.sony_error_codes = []


def _make_hass():
    hass = type("Hass", (), {})()
    hass.config = type("Config", (), {"path": lambda *p: "/tmp/ha"})()
    return hass


@pytest.mark.asyncio
async def test_slow_cache_fetches_on_first_refresh() -> None:
    client = FakeClient()
    coordinator = SonyAudioCoordinator(_make_hass(), client)
    # Skip discovery; set minimal state needed for _async_update_data
    coordinator.supported_api_info = {"services": []}
    coordinator.setting_descriptions = []
    state = await coordinator._async_update_data()

    assert client.get_system.called
    assert client.get_av_sources.called
    assert client.supported_api_info.called
    assert len(state.sources) == 2
    assert state.sources[0].title == "HDMI1"


@pytest.mark.asyncio
async def test_slow_cache_skipped_on_subsequent_refresh() -> None:
    client = FakeClient()
    coordinator = SonyAudioCoordinator(_make_hass(), client)
    coordinator.supported_api_info = {"services": []}
    coordinator.setting_descriptions = []
    # First refresh
    await coordinator._async_update_data()
    # Reset call counts
    client.get_system.reset_mock()
    client.get_av_sources.reset_mock()
    client.supported_api_info.reset_mock()

    # Second refresh (within slow interval)
    state = await coordinator._async_update_data()

    assert not client.get_system.called
    assert not client.get_av_sources.called
    assert not client.supported_api_info.called
    assert len(state.sources) == 2


@pytest.mark.asyncio
async def test_slow_cache_refreshes_after_interval(monkeypatch) -> None:
    import datetime as dt
    client = FakeClient()
    coordinator = SonyAudioCoordinator(_make_hass(), client)
    coordinator.supported_api_info = {"services": []}
    coordinator.setting_descriptions = []
    # First refresh
    await coordinator._async_update_data()

    # Simulate time passing
    future = dt.datetime.now() + dt.timedelta(seconds=400)
    monkeypatch.setattr(
        "custom_components.sony_audio_control.coordinator.datetime",
        type("MockDT", (), {"now": staticmethod(lambda: future)})(),
    )

    client.get_system.reset_mock()
    client.get_av_sources.reset_mock()
    client.supported_api_info.reset_mock()

    await coordinator._async_update_data()

    assert client.get_system.called
    assert client.get_av_sources.called
    assert client.supported_api_info.called


@pytest.mark.asyncio
async def test_fast_refresh_always_calls_core_methods() -> None:
    client = FakeClient()
    coordinator = SonyAudioCoordinator(_make_hass(), client)
    coordinator.supported_api_info = {"services": []}
    coordinator.setting_descriptions = []
    await coordinator._async_update_data()

    assert client.get_speaker_settings.called
    assert client.get_sound_settings.called
    assert client.get_volume.called
    assert client.power_status.called
    assert client.playing_content_info.called
