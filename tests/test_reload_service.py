"""Tests for the manual reload service."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock

import pytest

# Mock voluptuous
_vol = ModuleType("voluptuous")
_vol.Schema = lambda fields, **kwargs: fields
_vol.Required = lambda key: key
_vol.Optional = lambda key, default=None: key
sys.modules["voluptuous"] = _vol

# Mock config_validation
_cv = ModuleType("homeassistant.helpers.config_validation")
_cv.string = "string"
_cv.boolean = "boolean"
sys.modules["homeassistant.helpers.config_validation"] = _cv

# Minimal mocks for Home Assistant
_ha = ModuleType("homeassistant")
_ha.core = ModuleType("homeassistant.core")
_ha.core.HomeAssistant = type("HomeAssistant", (), {})
class _MockServiceCall:
    def __init__(self, domain=None, service=None, data=None):
        self.data = data or {}
_ha.core.ServiceCall = _MockServiceCall
_ha.config_entries = ModuleType("homeassistant.config_entries")
_ha.config_entries.ConfigEntry = type("ConfigEntry", (), {})
_ha.helpers = ModuleType("homeassistant.helpers")
_ha.helpers.aiohttp_client = ModuleType("homeassistant.helpers.aiohttp_client")
_ha.helpers.aiohttp_client.async_get_clientsession = AsyncMock()

_ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
_ha_helpers_update_coordinator.DataUpdateCoordinator = type("DataUpdateCoordinator", (), {
    "__init__": lambda self, hass, logger, name=None, update_interval=None, update_method=None, request_refresh_debouncer=None: None
})
_ha_helpers_update_coordinator.UpdateFailed = Exception
_ha.helpers.update_coordinator = _ha_helpers_update_coordinator

sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.config_entries"] = _ha.config_entries
sys.modules["homeassistant.helpers"] = _ha.helpers
sys.modules["homeassistant.helpers.aiohttp_client"] = _ha.helpers.aiohttp_client
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_helpers_update_coordinator

# Remove the dummy module placeholder from conftest so the real __init__.py loads
if "custom_components.sony_audio_control" in sys.modules:
    del sys.modules["custom_components.sony_audio_control"]

from custom_components.sony_audio_control import _async_register_services  # noqa: E402


class FakeCoordinator:
    def __init__(self, host, entry_id="test_entry"):
        self.client = type("Client", (), {"host": host})()
        self.entry_id = entry_id
        self.async_request_refresh = AsyncMock()


class FakeEntry:
    def __init__(self, entry_id, coordinator):
        self.entry_id = entry_id
        self.runtime_data = coordinator


def _make_hass(entries):
    hass = type("Hass", (), {})()
    hass._services = {}
    hass._entries = entries

    def has_service(self, domain, service):
        return (domain, service) in hass._services

    def async_register(self, domain, service, func, schema=None, supports_response=None):
        hass._services[(domain, service)] = func

    def async_entries(self, domain):
        return hass._entries

    hass.services = type("Services", (), {"has_service": has_service, "async_register": async_register})()
    hass.config_entries = type("ConfigEntries", (), {"async_entries": async_entries})()
    return hass


@pytest.mark.asyncio
async def test_reload_service_registered() -> None:
    hass = _make_hass([])
    _async_register_services(hass)
    assert ("sony_audio_control", "reload") in hass._services


@pytest.mark.asyncio
async def test_reload_all_devices_when_no_entry_id() -> None:
    coord1 = FakeCoordinator("192.168.1.10", "entry_1")
    coord2 = FakeCoordinator("192.168.1.11", "entry_2")
    entries = [FakeEntry("entry_1", coord1), FakeEntry("entry_2", coord2)]
    hass = _make_hass(entries)
    _async_register_services(hass)

    call = type("Call", (), {"data": {}})()
    await hass._services[("sony_audio_control", "reload")](call)

    assert coord1.async_request_refresh.called
    assert coord2.async_request_refresh.called


@pytest.mark.asyncio
async def test_reload_single_device_by_entry_id() -> None:
    coord1 = FakeCoordinator("192.168.1.10", "entry_1")
    coord2 = FakeCoordinator("192.168.1.11", "entry_2")
    entries = [FakeEntry("entry_1", coord1), FakeEntry("entry_2", coord2)]
    hass = _make_hass(entries)
    _async_register_services(hass)

    call = type("Call", (), {"data": {"entry_id": "entry_2"}})()
    await hass._services[("sony_audio_control", "reload")](call)

    assert not coord1.async_request_refresh.called
    assert coord2.async_request_refresh.called


@pytest.mark.asyncio
async def test_reload_warns_on_missing_entry_id() -> None:
    coord1 = FakeCoordinator("192.168.1.10", "entry_1")
    entries = [FakeEntry("entry_1", coord1)]
    hass = _make_hass(entries)
    _async_register_services(hass)

    call = type("Call", (), {"data": {"entry_id": "nonexistent"}})()
    # Should not raise; just return after logging warning
    await hass._services[("sony_audio_control", "reload")](call)

    assert not coord1.async_request_refresh.called
