"""Media player platform for Sony Audio Control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SonyAudioMediaPlayer(coordinator)])

class SonyAudioMediaPlayer(SonyAudioEntity, MediaPlayerEntity):
    """Media player for the Sony receiver."""

    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "media_player")

    @property
    def state(self) -> MediaPlayerState | str | None:
        result = self.coordinator.data.get("power") if self.coordinator.data else None
        status = self._first_dict(result).get("status")
        if status == "active":
            return MediaPlayerState.ON
        if status in {"standby", "off"}:
            return MediaPlayerState.OFF
        return None

    @property
    def volume_level(self) -> float | None:
        volume = self._main_volume()
        if not volume:
            return None
        try:
            current = float(volume.get("volume"))
            minimum = float(volume.get("minVolume", 0))
            maximum = float(volume.get("maxVolume", 100))
            if maximum == minimum:
                return None
            return max(0.0, min(1.0, (current - minimum) / (maximum - minimum)))
        except (TypeError, ValueError):
            return None

    @property
    def is_volume_muted(self) -> bool | None:
        volume = self._main_volume()
        if not volume:
            return None
        mute = volume.get("mute")
        if isinstance(mute, bool):
            return mute
        if isinstance(mute, str):
            return mute.lower() == "on"
        return None

    @property
    def source(self) -> str | None:
        playing = self._first_dict(self.coordinator.data.get("playing"))
        return playing.get("title") or playing.get("source") or playing.get("uri")

    @property
    def source_list(self) -> list[str] | None:
        inputs = self._input_items()
        names = [item.get("title") or item.get("name") for item in inputs]
        return [name for name in names if name]

    async def async_turn_on(self) -> None:
        await self.coordinator.api.set_power_status("active")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.api.set_power_status("off")
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        current = self._main_volume()
        if current:
            minimum = float(current.get("minVolume", 0))
            maximum = float(current.get("maxVolume", 100))
            value = round(minimum + (volume * (maximum - minimum)))
        else:
            value = round(volume * 100)
        await self.coordinator.api.set_audio_volume(str(value))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.api.set_audio_mute(mute)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        for item in self._input_items():
            name = item.get("title") or item.get("name")
            uri = item.get("uri")
            if name == source and uri:
                await self.coordinator.api.set_play_content(uri)
                await self.coordinator.async_request_refresh()
                return
        _LOGGER.warning("Source %s not found in Sony input list", source)

    def _main_volume(self) -> dict[str, Any] | None:
        result = self.coordinator.data.get("volume") if self.coordinator.data else None
        items = result[0] if isinstance(result, list) and result else result
        if isinstance(items, list):
            return next((item for item in items if item.get("target") in ("", "master", "speaker")), items[0] if items else None)
        if isinstance(items, dict):
            return items
        return None

    def _input_items(self) -> list[dict[str, Any]]:
        result = self.coordinator.data.get("inputs") if self.coordinator.data else None
        if isinstance(result, list) and result and isinstance(result[0], list):
            return [item for item in result[0] if isinstance(item, dict)]
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        return []

    @staticmethod
    def _first_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, list) and value:
            value = value[0]
        return value if isinstance(value, dict) else {}
