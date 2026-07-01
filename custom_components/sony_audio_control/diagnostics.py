"""Home Assistant diagnostics support for Sony Audio Control."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .coordinator import SonyAudioCoordinator
from .sony.diagnostics import redact


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SonyAudioCoordinator = entry.runtime_data
    targets = [desc.target for desc in coordinator.setting_descriptions if desc.target]
    dump = await coordinator.client.dump_device_info([target for target in targets if target])
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
            "device_dump": dump,
        }
    )


async def async_get_device_diagnostics(hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return await async_get_config_entry_diagnostics(hass, entry)
