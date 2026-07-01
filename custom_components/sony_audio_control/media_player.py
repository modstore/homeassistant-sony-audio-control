from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SonyAudioMediaPlayer(coordinator)])

class SonyAudioMediaPlayer(SonyAudioEntity, MediaPlayerEntity):
    _attr_name = None
    _attr_icon = "mdi:audio-video"

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "media_player")
        self._attr_supported_features = (
            MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )

    @property
    def state(self) -> MediaPlayerState | None:
        status = (self.coordinator.data.power_status if self.coordinator.data else None) or ""
        if str(status).lower() in {"active", "on", "true"}:
            return MediaPlayerState.ON
        if str(status).lower() in {"standby", "off", "false"}:
            return MediaPlayerState.OFF
        return None

    @property
    def volume_level(self) -> float | None:
        volume = self.coordinator.primary_volume()
        if not volume:
            return None
        current = _to_float(volume.get("volume"))
        min_v = _to_float(volume.get("minVolume")) or 0
        max_v = _to_float(volume.get("maxVolume")) or 100
        if current is None or max_v == min_v:
            return None
        return max(0, min(1, (current - min_v) / (max_v - min_v)))

    @property
    def is_volume_muted(self) -> bool | None:
        volume = self.coordinator.primary_volume()
        if not volume:
            return None
        mute = volume.get("mute")
        return bool(mute) if mute is not None else None

    @property
    def source(self) -> str | None:
        if not self.coordinator.data:
            return None
        content = self.coordinator.data.playing_content
        return content.get("source") or content.get("title") or content.get("uri")

    @property
    def source_list(self) -> list[str] | None:
        if not self.coordinator.data:
            return None
        values: list[str] = []
        for item in self.coordinator.data.inputs:
            title = item.get("title") or item.get("connection") or item.get("uri")
            if title:
                values.append(str(title))
        return values or None

    async def async_turn_on(self) -> None:
        await self.coordinator.api.set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.api.set_power(False)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        current = self.coordinator.primary_volume() or {}
        min_v = _to_float(current.get("minVolume")) or 0
        max_v = _to_float(current.get("maxVolume")) or 100
        target = current.get("target") or "master"
        await self.coordinator.api.set_volume(round(min_v + volume * (max_v - min_v)), str(target))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        current = self.coordinator.primary_volume() or {}
        await self.coordinator.api.set_mute(mute, str(current.get("target") or "master"))
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        # Sony devices usually select inputs by URI, not title. We look up the URI
        # from getCurrentExternalInputsStatus and send setPlayContent.
        if not self.coordinator.data:
            return
        for item in self.coordinator.data.inputs:
            if source in {item.get("title"), item.get("connection"), item.get("uri")} and item.get("uri"):
                await self.coordinator.api.call("avContent", "setPlayContent", [{"uri": item["uri"]}], "1.0")
                await self.coordinator.async_request_refresh()
                return


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
