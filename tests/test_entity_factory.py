"""Tests for entity factory type mapping."""
from __future__ import annotations

import sys
from types import ModuleType

# Minimal mocks for Home Assistant modules required by entity factory
_ha = ModuleType("homeassistant")
_ha_components = ModuleType("homeassistant.components")
_ha_helpers = ModuleType("homeassistant.helpers")

# number
_ha_number = ModuleType("homeassistant.components.number")
_ha_number.NumberEntity = type("NumberEntity", (), {})
_ha_number.NumberMode = ModuleType("homeassistant.components.number.NumberMode")
_ha_number.NumberMode.SLIDER = "slider"
_ha_components.number = _ha_number

# select
_ha_select = ModuleType("homeassistant.components.select")
_ha_select.SelectEntity = type("SelectEntity", (), {})
_ha_components.select = _ha_select

# switch
_ha_switch = ModuleType("homeassistant.components.switch")
_ha_switch.SwitchEntity = type("SwitchEntity", (), {})
_ha_components.switch = _ha_switch

# sensor
_ha_sensor = ModuleType("homeassistant.components.sensor")
_ha_sensor.SensorEntity = type("SensorEntity", (), {})
_ha_components.sensor = _ha_sensor

# button
_ha_button = ModuleType("homeassistant.components.button")
_ha_button.ButtonEntity = type("ButtonEntity", (), {})
_ha_components.button = _ha_button

# media_player
_ha_mp = ModuleType("homeassistant.components.media_player")
_ha_mp.MediaPlayerEntity = type("MediaPlayerEntity", (), {})
_ha_mp.MediaPlayerEntityFeature = type("MediaPlayerEntityFeature", (), {"TURN_ON": 1})
_ha_mp_const = ModuleType("homeassistant.components.media_player.const")
_ha_mp_const.MediaPlayerState = type("MediaPlayerState", (), {"ON": "on"})
_ha_mp.const = _ha_mp_const
_ha_components.media_player = _ha_mp
_ha_components.media_player.const = _ha_mp_const

# helpers
_ha_helpers_entity = ModuleType("homeassistant.helpers.entity")
_ha_helpers_entity.Entity = type("Entity", (), {})
_ha_helpers.entity = _ha_helpers_entity

_ha_helpers_device_registry = ModuleType("homeassistant.helpers.device_registry")
_ha_helpers_device_registry.DeviceInfo = dict
_ha_helpers.device_registry = _ha_helpers_device_registry

class _Subscriptable(type):
    def __getitem__(cls, item):
        return cls


class _MockCoordinatorEntity(metaclass=_Subscriptable):
    def __init__(self, coordinator=None):
        self.coordinator = coordinator


class _MockDataUpdateCoordinator(metaclass=_Subscriptable):
    def __init__(self, hass, logger, name=None, update_interval=None, update_method=None, request_refresh_debouncer=None):
        self.hass = hass
        self.name = name
        self.update_interval = update_interval


_ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
_ha_helpers_update_coordinator.CoordinatorEntity = _MockCoordinatorEntity
_ha_helpers_update_coordinator.DataUpdateCoordinator = _MockDataUpdateCoordinator
_ha_helpers_update_coordinator.UpdateFailed = Exception
_ha_helpers.update_coordinator = _ha_helpers_update_coordinator

_ha_helpers_entity_platform = ModuleType("homeassistant.helpers.entity_platform")
_ha_helpers_entity_platform.AddEntitiesCallback = type("AddEntitiesCallback", (), {})
_ha_helpers.entity_platform = _ha_helpers_entity_platform

# config_entries / core
_ha.config_entries = ModuleType("homeassistant.config_entries")
_ha.config_entries.ConfigEntry = type("ConfigEntry", (), {})
_ha.core = ModuleType("homeassistant.core")
_ha.core.HomeAssistant = type("HomeAssistant", (), {})

sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.components"] = _ha_components
sys.modules["homeassistant.components.number"] = _ha_number
sys.modules["homeassistant.components.select"] = _ha_select
sys.modules["homeassistant.components.switch"] = _ha_switch
sys.modules["homeassistant.components.sensor"] = _ha_sensor
sys.modules["homeassistant.components.button"] = _ha_button
sys.modules["homeassistant.components.media_player"] = _ha_mp
sys.modules["homeassistant.components.media_player.const"] = _ha_mp_const
sys.modules["homeassistant.config_entries"] = _ha.config_entries
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.helpers"] = _ha_helpers
sys.modules["homeassistant.helpers.device_registry"] = _ha_helpers_device_registry
sys.modules["homeassistant.helpers.entity"] = _ha_helpers_entity
sys.modules["homeassistant.helpers.entity_platform"] = _ha_helpers_entity_platform
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_helpers_update_coordinator

from custom_components.sony_audio_control.entity_factory import create  # noqa: E402
from custom_components.sony_audio_control.number import SonyAudioNumber  # noqa: E402
from custom_components.sony_audio_control.select import SonyAudioSelect  # noqa: E402
from custom_components.sony_audio_control.sensor import SonyAudioSensor  # noqa: E402
from custom_components.sony_audio_control.sony.models import (  # noqa: E402
    SettingDescription,
    SettingType,
)
from custom_components.sony_audio_control.switch import SonyAudioSwitch  # noqa: E402


class _FakeClient:
    host = "192.168.1.14"
    port = 10000


class FakeCoordinator:
    def __init__(self):
        self.client = _FakeClient()
        self.data = None


def test_factory_creates_number_for_double_number_target() -> None:
    desc = SettingDescription(
        key="audio_frontLLevel",
        name="Front L",
        kind="number",
        service="audio",
        sony_type=SettingType.NUMBER.value,
        target="frontLLevel",
    )
    entity = create(FakeCoordinator(), desc)
    assert isinstance(entity, SonyAudioNumber)


def test_factory_creates_select_for_enum_target() -> None:
    desc = SettingDescription(
        key="audio_soundField",
        name="Sound Field",
        kind="select",
        service="audio",
        sony_type=SettingType.ENUM.value,
        target="soundField",
    )
    entity = create(FakeCoordinator(), desc)
    assert isinstance(entity, SonyAudioSelect)


def test_factory_creates_switch_for_boolean_target() -> None:
    desc = SettingDescription(
        key="audio_pureDirect",
        name="Pure Direct",
        kind="switch",
        service="audio",
        sony_type=SettingType.BOOLEAN.value,
        target="pureDirect",
    )
    entity = create(FakeCoordinator(), desc)
    assert isinstance(entity, SonyAudioSwitch)


def test_factory_falls_back_to_kind_for_unknown_type() -> None:
    desc = SettingDescription(
        key="audio_someSensor",
        name="Some Sensor",
        kind="sensor",
        service="audio",
        sony_type=SettingType.UNKNOWN.value,
        target="someSensor",
    )
    entity = create(FakeCoordinator(), desc)
    assert isinstance(entity, SonyAudioSensor)
