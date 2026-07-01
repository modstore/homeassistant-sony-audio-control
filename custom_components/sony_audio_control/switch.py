"""Switch entities for Sony Audio Control."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SonyMuteSwitch(coordinator)])

class SonyMuteSwitch(SonyAudioEntity, SwitchEntity):
    """Mute switch."""

    _attr_name = "Mute"
    _attr_icon = "mdi:volume-mute"

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "mute")

    @property
    def is_on(self) -> bool | None:
        volume = self._main_volume()
        if not volume:
            return None
        mute = volume.get("mute")
        if isinstance(mute, bool):
            return mute
        if isinstance(mute, str):
            return mute.lower() in {"on", "true", "1"}
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_audio_mute(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_audio_mute(False)
        await self.coordinator.async_request_refresh()

    def _main_volume(self) -> dict[str, Any] | None:
        result = self.coordinator.data.get("volume") if self.coordinator.data else None
        items = result[0] if isinstance(result, list) and result else result
        if isinstance(items, list):
            return next((item for item in items if item.get("target") in ("", "master", "speaker")), items[0] if items else None)
        if isinstance(items, dict):
            return items
        return None
