"""Home Assistant diagnostics support for Sony Audio Control."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .coordinator import SonyAudioCoordinator
from .sony.diagnostics import redact


def _state_to_dict(state) -> dict[str, Any]:
    """Convert SonyState into a plain dict for diagnostics."""
    if state is None:
        return {}
    return {
        "model_name": state.model_name,
        "device_name": state.device_name,
        "power": state.power,
        "input_title": state.input_title,
        "input_uri": state.input_uri,
        "last_update": state.last_update.isoformat() if state.last_update else None,
        "volume": {
            "volume": state.volume.volume,
            "muted": state.volume.muted,
            "max_volume": state.volume.max_volume,
            "min_volume": state.volume.min_volume,
            "step": state.volume.step,
        }
        if state.volume
        else None,
        "system": {
            "firmware": state.system.firmware,
            "mac": state.system.mac,
            "bluetooth_mac": state.system.bluetooth_mac,
        }
        if state.system
        else None,
        "speaker_settings": {
            target: {
                "title": s.title,
                "type": str(s.type),
                "current_value": s.current_value,
                "available": s.available,
                "minimum": s.minimum,
                "maximum": s.maximum,
                "step": s.step,
            }
            for target, s in state.speaker_settings.items()
        },
        "sound_settings": {
            target: {
                "title": s.title,
                "type": str(s.type),
                "current_value": s.current_value,
                "available": s.available,
                "minimum": s.minimum,
                "maximum": s.maximum,
                "step": s.step,
            }
            for target, s in state.sound_settings.items()
        },
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SonyAudioCoordinator = entry.runtime_data
    return redact(
        {
            "entry": {"title": entry.title, "data": dict(entry.data)},
            "discovered_entities": [
                {
                    "key": desc.key,
                    "name": desc.name,
                    "kind": desc.kind,
                    "service": desc.service,
                    "target": desc.target,
                    "sony_type": desc.sony_type,
                    "get_method": desc.get_method,
                    "set_method": desc.set_method,
                    "options": desc.option_values,
                    "min": desc.min_value,
                    "max": desc.max_value,
                    "step": desc.step,
                    "unit": desc.unit,
                    "raw": desc.raw,
                }
                for desc in coordinator.setting_descriptions
            ],
            "state": _state_to_dict(coordinator.data),
            "supported_api_info": coordinator.supported_api_info,
        }
    )


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return await async_get_config_entry_diagnostics(hass, entry)
