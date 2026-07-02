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
        "sources": [
            {"uri": s.uri, "title": s.title, "icon": s.icon} for s in state.sources
        ],
    }


def _discovery_to_dict(coordinator: SonyAudioCoordinator) -> dict[str, Any]:
    """Build a discovery summary for diagnostics."""
    supported = coordinator.supported_api_info
    services = []
    if isinstance(supported, dict):
        svc_list = supported.get("services")
        if isinstance(svc_list, list):
            services = [
                str(s.get("service") or s.get("serviceName") or s.get("name"))
                for s in svc_list
                if isinstance(s, dict)
            ]
    return {
        "supported_services": [s for s in services if s],
        "successful_methods": sorted(coordinator.client.successful_methods),
        "failed_methods": sorted(coordinator.client.failed_methods),
        "sony_error_codes": coordinator.client.sony_error_codes,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SonyAudioCoordinator = entry.runtime_data
    return redact(
        {
            "entry": {"title": entry.title, "data": dict(entry.data)},
            "device": {
                "host": coordinator.client.host,
                "port": coordinator.client.port,
                "model_name": coordinator.data.model_name if coordinator.data else None,
                "device_name": coordinator.data.device_name if coordinator.data else None,
                "firmware": coordinator.data.system.firmware if coordinator.data and coordinator.data.system else None,
            },
            "discovery": _discovery_to_dict(coordinator),
            "api_timings": list(coordinator.client.api_timings.values()),
            "state": _state_to_dict(coordinator.data),
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
            "supported_api_info": coordinator.supported_api_info,
        }
    )


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return await async_get_config_entry_diagnostics(hass, entry)
