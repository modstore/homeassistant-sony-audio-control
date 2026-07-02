"""Tests for device registry information."""
from __future__ import annotations

import sys
from types import ModuleType

# Minimal mocks for Home Assistant modules required by entity
_ha = ModuleType("homeassistant")
_ha_helpers = ModuleType("homeassistant.helpers")

_ha_helpers_device_registry = ModuleType("homeassistant.helpers.device_registry")
_ha_helpers_device_registry.DeviceInfo = dict
_ha_helpers.device_registry = _ha_helpers_device_registry

_ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")

class _Subscriptable(type):
    def __getitem__(cls, item):
        return cls

class _MockCoordinatorEntity(metaclass=_Subscriptable):
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

class _MockDataUpdateCoordinator(metaclass=_Subscriptable):
    pass

_ha_helpers_update_coordinator.CoordinatorEntity = _MockCoordinatorEntity
_ha_helpers_update_coordinator.DataUpdateCoordinator = _MockDataUpdateCoordinator
_ha_helpers_update_coordinator.UpdateFailed = Exception
_ha_helpers.update_coordinator = _ha_helpers_update_coordinator

_ha.core = ModuleType("homeassistant.core")
_ha.core.HomeAssistant = type("HomeAssistant", (), {})
_ha.config_entries = ModuleType("homeassistant.config_entries")
_ha.config_entries.ConfigEntry = type("ConfigEntry", (), {})

sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.helpers"] = _ha_helpers
sys.modules["homeassistant.helpers.device_registry"] = _ha_helpers_device_registry
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_helpers_update_coordinator
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.config_entries"] = _ha.config_entries

from custom_components.sony_audio_control.entity import SonyAudioEntity  # noqa: E402
from custom_components.sony_audio_control.sony.models import (  # noqa: E402
    SettingDescription,
    SonyState,
    SonySystem,
)


class _FakeClient:
    host = "192.168.1.14"
    port = 10000


class FakeCoordinator:
    def __init__(self, state=None):
        self.client = _FakeClient()
        self.data = state


def test_device_info_uses_mac_when_available() -> None:
    system = SonySystem(mac="38:18:4c:4e:e1:d5", firmware="M41.R.0518", raw={"modelName": "STR-DN1080"})
    state = SonyState(system=system, model_name="STR-DN1080", device_name="Living Room Receiver")
    coordinator = FakeCoordinator(state)
    desc = SettingDescription(key="test", name="Test", kind="sensor", service="audio")
    entity = SonyAudioEntity(coordinator, desc)

    info = entity.device_info
    assert info["identifiers"] == {("sony_audio_control", "38:18:4c:4e:e1:d5")}
    assert info["connections"] == {("mac", "38:18:4c:4e:e1:d5")}


def test_device_info_falls_back_to_host_without_mac() -> None:
    system = SonySystem(mac=None, firmware="M41.R.0518", raw={})
    state = SonyState(system=system, model_name="STR-DN1080")
    coordinator = FakeCoordinator(state)
    desc = SettingDescription(key="test", name="Test", kind="sensor", service="audio")
    entity = SonyAudioEntity(coordinator, desc)

    info = entity.device_info
    assert info["identifiers"] == {("sony_audio_control", "192.168.1.14")}
    assert info["connections"] == set()


def test_device_info_populates_model_and_firmware() -> None:
    system = SonySystem(mac="38:18:4c:4e:e1:d5", firmware="M41.R.0518", raw={"modelName": "STR-DN1080"})
    state = SonyState(system=system, model_name="STR-DN1080", device_name="Living Room Receiver")
    coordinator = FakeCoordinator(state)
    desc = SettingDescription(key="test", name="Test", kind="sensor", service="audio")
    entity = SonyAudioEntity(coordinator, desc)

    info = entity.device_info
    assert info["manufacturer"] == "Sony"
    assert info["model"] == "STR-DN1080"
    assert info["sw_version"] == "M41.R.0518"
    assert info["name"] == "Living Room Receiver"


def test_device_info_prefers_friendly_name() -> None:
    system = SonySystem(mac="38:18:4c:4e:e1:d5", firmware="M41.R.0518", raw={"productName": "My Receiver", "modelName": "STR-DN1080"})
    state = SonyState(system=system, model_name="STR-DN1080", device_name="My Receiver")
    coordinator = FakeCoordinator(state)
    desc = SettingDescription(key="test", name="Test", kind="sensor", service="audio")
    entity = SonyAudioEntity(coordinator, desc)

    info = entity.device_info
    assert info["name"] == "My Receiver"


def test_device_info_fallback_name_order() -> None:
    system = SonySystem(mac=None, raw={})
    state = SonyState(system=system, model_name=None, device_name=None)
    coordinator = FakeCoordinator(state)
    desc = SettingDescription(key="test", name="Test", kind="sensor", service="audio")
    entity = SonyAudioEntity(coordinator, desc)

    info = entity.device_info
    assert info["name"] == "Sony Audio Device"
    assert info["model"] is None


def test_device_info_uses_raw_system_when_no_state() -> None:
    system = SonySystem(mac="38:18:4c:4e:e1:d5", raw={"productName": "Receiver", "modelName": "STR-DN1080"})
    state = SonyState(system=system)
    coordinator = FakeCoordinator(state)
    desc = SettingDescription(key="test", name="Test", kind="sensor", service="audio")
    entity = SonyAudioEntity(coordinator, desc)

    info = entity.device_info
    assert info["name"] == "Receiver"
    assert info["model"] == "STR-DN1080"
    assert info["sw_version"] is None
    assert info["manufacturer"] == "Sony"
