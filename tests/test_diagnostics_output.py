"""Tests for improved diagnostics output."""
from __future__ import annotations

import sys
from types import ModuleType

import pytest

# Minimal mocks for Home Assistant
_ha = ModuleType("homeassistant")
_ha.core = ModuleType("homeassistant.core")
_ha.core.HomeAssistant = type("HomeAssistant", (), {})
_ha.config_entries = ModuleType("homeassistant.config_entries")
class _MockConfigEntry:
    def __init__(self):
        self.data = {"host": "192.168.1.14", "port": 10000}
        self.title = "Sony Audio"
        self.entry_id = "test_entry"
        self.runtime_data = None

_ha.config_entries.ConfigEntry = _MockConfigEntry
_ha.helpers = ModuleType("homeassistant.helpers")
_ha_helpers_device_registry = ModuleType("homeassistant.helpers.device_registry")
_ha_helpers_device_registry.DeviceEntry = type("DeviceEntry", (), {})
_ha.helpers.device_registry = _ha_helpers_device_registry

_ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
_ha_helpers_update_coordinator.DataUpdateCoordinator = type("DataUpdateCoordinator", (), {})
_ha_helpers_update_coordinator.UpdateFailed = Exception
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_helpers_update_coordinator

sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.config_entries"] = _ha.config_entries
sys.modules["homeassistant.helpers"] = _ha.helpers
sys.modules["homeassistant.helpers.device_registry"] = _ha_helpers_device_registry

from custom_components.sony_audio_control.diagnostics import (  # noqa: E402
    _discovery_to_dict,
    _state_to_dict,
    async_get_config_entry_diagnostics,
)
from custom_components.sony_audio_control.sony.models import (  # noqa: E402
    SettingDescription,
    SettingType,
    SonySetting,
    SonySource,
    SonyState,
    SonySystem,
    SonyVolume,
)


class FakeClient:
    host = "192.168.1.14"
    port = 10000
    api_timings = {
        "getSpeakerSettings": {"method": "getSpeakerSettings", "duration_ms": 18},
        "getSoundSettings": {"method": "getSoundSettings", "duration_ms": 12},
    }
    successful_methods = {"getSpeakerSettings", "getSoundSettings"}
    failed_methods = {"getStorageList"}
    sony_error_codes = [{"method": "getStorageList", "error": [12, "Unsupported"]}]


class FakeCoordinator:
    def __init__(self):
        self.client = FakeClient()
        self.supported_api_info = {
            "services": [
                {"service": "audio", "apis": [{"name": "getSpeakerSettings"}]},
                {"service": "system", "apis": [{"name": "getPowerStatus"}]},
                {"service": "avContent", "apis": [{"name": "getSourceList"}]},
            ]
        }
        self.setting_descriptions = [
            SettingDescription(
                key="audio_subwooferLevel",
                name="Subwoofer",
                kind="number",
                service="audio",
                target="subwooferLevel",
            )
        ]
        self.data = SonyState(
            system=SonySystem(firmware="M41.R.0518", mac="38:18:4c:4e:e1:d5", raw={"modelName": "STR-DN1080"}),
            volume=SonyVolume(volume=35, muted=False, max_volume=70, min_volume=0, step=1),
            power="active",
            input_title="HDMI1",
            input_uri="extInput:hdmi?port=1",
            model_name="STR-DN1080",
            device_name="Living Room",
            sources=[SonySource(uri="extInput:hdmi?port=1", title="HDMI1"), SonySource(uri="extInput:tv", title="TV")],
            speaker_settings={
                "subwooferLevel": SonySetting(
                    target="subwooferLevel",
                    title="Subwoofer",
                    type=SettingType.NUMBER,
                    current_value="0.0",
                    available=True,
                    minimum=-10.0,
                    maximum=10.0,
                    step=0.5,
                )
            },
        )


def test_state_to_dict_includes_sources() -> None:
    state = SonyState(
        sources=[SonySource(uri="extInput:tv", title="TV", icon="mdi:television")],
        power="active",
    )
    d = _state_to_dict(state)
    assert d["sources"] == [{"uri": "extInput:tv", "title": "TV", "icon": "mdi:television"}]
    assert d["power"] == "active"


def test_discovery_to_dict_extracts_services() -> None:
    coordinator = FakeCoordinator()
    d = _discovery_to_dict(coordinator)
    assert sorted(d["supported_services"]) == ["audio", "avContent", "system"]
    assert d["successful_methods"] == ["getSoundSettings", "getSpeakerSettings"]
    assert d["failed_methods"] == ["getStorageList"]
    assert d["sony_error_codes"] == [{"method": "getStorageList", "error": [12, "Unsupported"]}]


@pytest.mark.asyncio
async def test_config_entry_diagnostics_structure() -> None:
    entry = _ha.config_entries.ConfigEntry()
    entry.runtime_data = FakeCoordinator()

    result = await async_get_config_entry_diagnostics(type("Hass", (), {})(), entry)

    # Device section
    assert result["device"]["host"] == "REDACTED"
    assert result["device"]["model_name"] == "STR-DN1080"
    assert result["device"]["firmware"] == "M41.R.0518"

    # Discovery section
    assert "audio" in result["discovery"]["supported_services"]
    assert "getSpeakerSettings" in result["discovery"]["successful_methods"]
    assert "getStorageList" in result["discovery"]["failed_methods"]

    # API timings
    assert any(t["method"] == "getSpeakerSettings" for t in result["api_timings"])
    assert any(t["method"] == "getSoundSettings" for t in result["api_timings"])

    # Cached state
    assert result["state"]["power"] == "active"
    assert result["state"]["input_title"] == "HDMI1"
    assert result["state"]["volume"]["volume"] == 35
    assert result["state"]["system"]["firmware"] == "M41.R.0518"
    assert result["state"]["speaker_settings"]["subwooferLevel"]["title"] == "Subwoofer"
    assert len(result["state"]["sources"]) == 2

    # Discovered entities
    assert len(result["discovered_entities"]) == 1
    assert result["discovered_entities"][0]["key"] == "audio_subwooferLevel"

    # Redaction
    assert result["device"]["host"] == "REDACTED"
    assert result["state"]["system"]["mac"] == "REDACTED"
