"""Tests for optimistic UI updates in the coordinator."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, Mock

import pytest

# --- Mock Home Assistant core modules before importing integration code ---

_ha = ModuleType("homeassistant")
_ha.core = ModuleType("homeassistant.core")
_ha.core.HomeAssistant = type("HomeAssistant", (), {})
_ha_helpers = ModuleType("homeassistant.helpers")

# update_coordinator
_ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
_ha_helpers_update_coordinator.UpdateFailed = Exception


class _Subscriptable(type):
    def __getitem__(cls, item):
        return cls


class _MockDataUpdateCoordinator(metaclass=_Subscriptable):
    def __init__(
        self,
        hass,
        logger,
        name=None,
        update_interval=None,
        update_method=None,
        request_refresh_debouncer=None,
    ):
        self.hass = hass
        self.name = name
        self.update_interval = update_interval
        self.data = None

    def async_update_listeners(self):
        pass


class _MockCoordinatorEntity(metaclass=_Subscriptable):
    def __init__(self, coordinator=None):
        self.coordinator = coordinator


_ha_helpers_update_coordinator.DataUpdateCoordinator = _MockDataUpdateCoordinator
_ha_helpers_update_coordinator.CoordinatorEntity = _MockCoordinatorEntity
_ha_helpers.update_coordinator = _ha_helpers_update_coordinator

# entity
_ha_helpers_entity = ModuleType("homeassistant.helpers.entity")
_ha_helpers_entity.Entity = type("Entity", (), {})
_ha_helpers.entity = _ha_helpers_entity

# device_registry
_ha_helpers_device_registry = ModuleType("homeassistant.helpers.device_registry")
_ha_helpers_device_registry.DeviceInfo = dict
_ha_helpers.device_registry = _ha_helpers_device_registry

# entity_platform
_ha_helpers_entity_platform = ModuleType("homeassistant.helpers.entity_platform")
_ha_helpers_entity_platform.AddEntitiesCallback = type("AddEntitiesCallback", (), {})
_ha_helpers.entity_platform = _ha_helpers_entity_platform

# config_entries
_ha.config_entries = ModuleType("homeassistant.config_entries")
_ha.config_entries.ConfigEntry = type("ConfigEntry", (), {})

sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.helpers"] = _ha_helpers
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_helpers_update_coordinator
sys.modules["homeassistant.helpers.entity"] = _ha_helpers_entity
sys.modules["homeassistant.helpers.device_registry"] = _ha_helpers_device_registry
sys.modules["homeassistant.helpers.entity_platform"] = _ha_helpers_entity_platform
sys.modules["homeassistant.config_entries"] = _ha.config_entries

# Remove cached coordinator module so it re-imports with our mock
if "custom_components.sony_audio_control.coordinator" in sys.modules:
    del sys.modules["custom_components.sony_audio_control.coordinator"]

# Pre-mock HA component platforms so entity modules can be imported on demand
_ha_components = ModuleType("homeassistant.components")
for _comp_name, _entity_name in (
    ("number", "NumberEntity"),
    ("select", "SelectEntity"),
    ("switch", "SwitchEntity"),
):
    _mod = ModuleType(f"homeassistant.components.{_comp_name}")
    _mod.__dict__[_entity_name] = type(_entity_name, (), {})
    sys.modules[f"homeassistant.components.{_comp_name}"] = _mod
    setattr(_ha_components, _comp_name, _mod)

# NumberMode mock for number platform
_ha_number_mod = sys.modules["homeassistant.components.number"]
_ha_number_mod.NumberMode = ModuleType("homeassistant.components.number.NumberMode")
_ha_number_mod.NumberMode.SLIDER = "slider"

sys.modules["homeassistant.components"] = _ha_components

from custom_components.sony_audio_control.coordinator import SonyAudioCoordinator
from custom_components.sony_audio_control.sony.models import (
    SonySetting,
    SonySource,
    SonyState,
    SonyVolume,
)

# --- Helpers ---


class FakeClient:
    def __init__(self):
        self.host = "192.168.1.14"
        self.port = 10000
        self.set_speaker_setting = AsyncMock()
        self.set_sound_setting = AsyncMock()
        self.set_volume = AsyncMock()
        self.set_mute = AsyncMock()
        self.set_play_content = AsyncMock()
        self.set_power = AsyncMock()


def _make_hass():
    hass = type("Hass", (), {})()
    hass.config = type("Config", (), {"path": lambda *p: "/tmp/ha"})()
    return hass


def _make_coordinator():
    client = FakeClient()
    coordinator = SonyAudioCoordinator(_make_hass(), client)
    return coordinator


# --- Coordinator tests ---


@pytest.mark.asyncio
async def test_set_speaker_setting_updates_cache() -> None:
    coordinator = _make_coordinator()
    setting = SonySetting(
        target="subwooferLevel",
        title="Subwoofer",
        type="doubleNumberTarget",
        current_value="0",
        available=True,
    )
    state = SonyState(speaker_settings={"subwooferLevel": setting})
    coordinator.data = state
    coordinator.async_update_listeners = Mock()

    await coordinator.async_set_speaker_setting("subwooferLevel", "5")

    coordinator.client.set_speaker_setting.assert_awaited_once_with(
        "subwooferLevel", "5"
    )
    assert state.speaker_settings["subwooferLevel"].current_value == "5"
    coordinator.async_update_listeners.assert_called_once()


@pytest.mark.asyncio
async def test_set_sound_setting_updates_cache() -> None:
    coordinator = _make_coordinator()
    setting = SonySetting(
        target="soundField",
        title="Sound Field",
        type="enumTarget",
        current_value="auto",
        available=True,
    )
    state = SonyState(sound_settings={"soundField": setting})
    coordinator.data = state

    await coordinator.async_set_sound_setting("soundField", "movie")

    coordinator.client.set_sound_setting.assert_awaited_once_with("soundField", "movie")
    assert state.sound_settings["soundField"].current_value == "movie"


@pytest.mark.asyncio
async def test_set_speaker_setting_missing_target_does_not_crash() -> None:
    coordinator = _make_coordinator()
    state = SonyState(speaker_settings={})
    coordinator.data = state

    await coordinator.async_set_speaker_setting("missingTarget", "5")

    coordinator.client.set_speaker_setting.assert_awaited_once_with(
        "missingTarget", "5"
    )
    # state unchanged, no crash


@pytest.mark.asyncio
async def test_set_sound_setting_missing_target_does_not_crash() -> None:
    coordinator = _make_coordinator()
    state = SonyState(sound_settings={})
    coordinator.data = state

    await coordinator.async_set_sound_setting("missingTarget", "on")

    coordinator.client.set_sound_setting.assert_awaited_once_with("missingTarget", "on")


@pytest.mark.asyncio
async def test_set_volume_updates_cache() -> None:
    coordinator = _make_coordinator()
    vol = SonyVolume(volume=20, muted=False, max_volume=70, min_volume=0, step=1)
    state = SonyState(volume=vol)
    coordinator.data = state

    await coordinator.async_set_volume(35)

    coordinator.client.set_volume.assert_awaited_once_with(35)
    assert state.volume.volume == 35


@pytest.mark.asyncio
async def test_set_mute_updates_cache() -> None:
    coordinator = _make_coordinator()
    vol = SonyVolume(volume=20, muted=False, max_volume=70, min_volume=0, step=1)
    state = SonyState(volume=vol)
    coordinator.data = state

    await coordinator.async_set_mute(True)

    coordinator.client.set_mute.assert_awaited_once_with(True)
    assert state.volume.muted is True


@pytest.mark.asyncio
async def test_select_source_updates_cache() -> None:
    coordinator = _make_coordinator()
    sources = [SonySource(uri="extInput:hdmi?port=1", title="HDMI1")]
    state = SonyState(sources=sources, input_title="TV", input_uri="extInput:tv")
    coordinator.data = state

    await coordinator.async_select_source("HDMI1")

    coordinator.client.set_play_content.assert_awaited_once_with(
        "extInput:hdmi?port=1"
    )
    assert state.input_title == "HDMI1"
    assert state.input_uri == "extInput:hdmi?port=1"


@pytest.mark.asyncio
async def test_select_source_not_found_does_not_call_api() -> None:
    coordinator = _make_coordinator()
    sources = [SonySource(uri="extInput:hdmi?port=1", title="HDMI1")]
    state = SonyState(sources=sources, input_title="TV", input_uri="extInput:tv")
    coordinator.data = state

    await coordinator.async_select_source("MissingSource")

    coordinator.client.set_play_content.assert_not_awaited()
    assert state.input_title == "TV"


@pytest.mark.asyncio
async def test_failed_api_call_does_not_update_cache() -> None:
    coordinator = _make_coordinator()
    from custom_components.sony_audio_control.sony.exceptions import SonyAudioApiError

    coordinator.client.set_speaker_setting.side_effect = SonyAudioApiError("fail")
    setting = SonySetting(
        target="subwooferLevel",
        title="Subwoofer",
        type="doubleNumberTarget",
        current_value="0",
        available=True,
    )
    state = SonyState(speaker_settings={"subwooferLevel": setting})
    coordinator.data = state

    with pytest.raises(SonyAudioApiError):
        await coordinator.async_set_speaker_setting("subwooferLevel", "5")

    assert state.speaker_settings["subwooferLevel"].current_value == "0"


# --- Entity delegation tests ---


@pytest.mark.asyncio
async def test_number_entity_set_updates_cache() -> None:
    from custom_components.sony_audio_control.number import SonyAudioNumber
    from custom_components.sony_audio_control.sony.models import SettingDescription

    coordinator = _make_coordinator()
    setting = SonySetting(
        target="subwooferLevel",
        title="Subwoofer",
        type="doubleNumberTarget",
        current_value="0",
        available=True,
    )
    state = SonyState(speaker_settings={"subwooferLevel": setting})
    coordinator.data = state

    desc = SettingDescription(
        key="audio_subwooferLevel",
        name="Subwoofer",
        kind="number",
        service="audio",
        set_method="setSpeakerSettings",
        target="subwooferLevel",
        min_value=-10,
        max_value=10,
        step=0.5,
    )
    entity = SonyAudioNumber(coordinator, desc)
    await entity.async_set_native_value(5.0)

    assert state.speaker_settings["subwooferLevel"].current_value == "5"


@pytest.mark.asyncio
async def test_switch_entity_set_updates_cache() -> None:
    from custom_components.sony_audio_control.switch import SonyAudioSwitch
    from custom_components.sony_audio_control.sony.models import SettingDescription

    coordinator = _make_coordinator()
    setting = SonySetting(
        target="pureDirect",
        title="Pure Direct",
        type="booleanTarget",
        current_value="off",
        available=True,
    )
    state = SonyState(sound_settings={"pureDirect": setting})
    coordinator.data = state

    desc = SettingDescription(
        key="audio_pureDirect",
        name="Pure Direct",
        kind="switch",
        service="audio",
        set_method="setSoundSettings",
        target="pureDirect",
    )
    entity = SonyAudioSwitch(coordinator, desc)
    await entity.async_turn_on()

    assert state.sound_settings["pureDirect"].current_value == "on"


@pytest.mark.asyncio
async def test_select_entity_set_updates_cache() -> None:
    from custom_components.sony_audio_control.select import SonyAudioSelect
    from custom_components.sony_audio_control.sony.models import SettingDescription

    coordinator = _make_coordinator()
    setting = SonySetting(
        target="soundField",
        title="Sound Field",
        type="enumTarget",
        current_value="auto",
        available=True,
    )
    state = SonyState(sound_settings={"soundField": setting})
    coordinator.data = state

    desc = SettingDescription(
        key="audio_soundField",
        name="Sound Field",
        kind="select",
        service="audio",
        set_method="setSoundSettings",
        target="soundField",
        option_values=["Auto", "Movie"],
        option_map={"Auto": "auto", "Movie": "movie"},
    )
    entity = SonyAudioSelect(coordinator, desc)
    await entity.async_select_option("Movie")

    assert state.sound_settings["soundField"].current_value == "movie"


# --- Subwoofer preset tests ---


@pytest.mark.asyncio
async def test_subwoofer_preset_updates_instantly() -> None:
    from custom_components.sony_audio_control.const import (
        SUBWOOFER_MANUAL_PRESET,
        SUBWOOFER_PRESETS,
    )
    from custom_components.sony_audio_control.select import SonyAudioSelect
    from custom_components.sony_audio_control.sony.models import SettingDescription

    coordinator = _make_coordinator()
    setting = SonySetting(
        target="subwooferLevel",
        title="Subwoofer",
        type="doubleNumberTarget",
        current_value="0",
        available=True,
    )
    state = SonyState(speaker_settings={"subwooferLevel": setting})
    coordinator.data = state

    desc = SettingDescription(
        key="subwoofer_preset",
        name="Subwoofer Preset",
        kind="select",
        service="audio",
        target="subwooferLevel",
        option_values=list(SUBWOOFER_PRESETS.keys()) + [SUBWOOFER_MANUAL_PRESET],
        option_map={k: str(int(v)) for k, v in SUBWOOFER_PRESETS.items()},
    )
    entity = SonyAudioSelect(coordinator, desc)
    assert entity.current_option == "Normal"

    # Simulate optimistic update via coordinator
    await coordinator.async_set_speaker_setting("subwooferLevel", "5")
    assert entity.current_option == "High"


@pytest.mark.asyncio
async def test_custom_subwoofer_value_maps_preset_to_manual() -> None:
    from custom_components.sony_audio_control.const import SUBWOOFER_MANUAL_PRESET
    from custom_components.sony_audio_control.select import SonyAudioSelect
    from custom_components.sony_audio_control.sony.models import SettingDescription

    coordinator = _make_coordinator()
    setting = SonySetting(
        target="subwooferLevel",
        title="Subwoofer",
        type="doubleNumberTarget",
        current_value="0",
        available=True,
    )
    state = SonyState(speaker_settings={"subwooferLevel": setting})
    coordinator.data = state

    from custom_components.sony_audio_control.const import SUBWOOFER_PRESETS

    desc = SettingDescription(
        key="subwoofer_preset",
        name="Subwoofer Preset",
        kind="select",
        service="audio",
        target="subwooferLevel",
        option_values=list(SUBWOOFER_PRESETS.keys()) + [SUBWOOFER_MANUAL_PRESET],
        option_map={k: str(int(v)) for k, v in SUBWOOFER_PRESETS.items()},
    )
    entity = SonyAudioSelect(coordinator, desc)

    await coordinator.async_set_speaker_setting("subwooferLevel", "3")
    assert entity.current_option == SUBWOOFER_MANUAL_PRESET
