"""Diagnostics support for Sony Audio Control."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_HOST, DOMAIN
from .coordinator import SonyAudioCoordinator

TO_REDACT = {CONF_HOST, "macAddr", "wirelessMacAddr", "wiredMacAddr", "ssid", "bssid"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SonyAudioCoordinator = entry.runtime_data
    targets = [desc.target for desc in coordinator.setting_descriptions if desc.target]
    dump = await coordinator.client.dump_device_info([target for target in targets if target])
    return {
        "entry": {"title": entry.title, "data": _redact(dict(entry.data))},
        "discovered_entities": [_redact(desc.raw | {"key": desc.key, "kind": desc.kind}) for desc in coordinator.setting_descriptions],
        "device_dump": _redact(dump),
    }


async def async_get_device_diagnostics(hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return await async_get_config_entry_diagnostics(hass, entry)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("REDACTED" if k in TO_REDACT else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
