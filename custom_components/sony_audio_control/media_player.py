"""Media player platform for Sony Audio Control."""
from __future__ import annotations

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity
from .sony.models import SettingDescription


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = entry.runtime_data
    if any(desc.key == "media_player_main" for desc in coordinator.setting_descriptions):
        async_add_entities([SonyAudioMediaPlayer(coordinator)])


class SonyAudioMediaPlayer(SonyAudioEntity, MediaPlayerEntity):
    """Main Sony receiver media player."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, SettingDescription(key="media_player_main", name="Receiver", kind="sensor", service="core"))

    @property
    def state(self) -> MediaPlayerState | None:
        power = (self.coordinator.data.power or "").lower() if self.coordinator.data else ""
        if power in {"active", "on"}:
            return MediaPlayerState.ON
        if power in {"standby", "off"}:
            return MediaPlayerState.OFF
        return None

    @property
    def volume_level(self) -> float | None:
        data = self.coordinator.data
        if not data or data.volume is None:
            return None
        min_v = data.min_volume if data.min_volume is not None else 0
        max_v = data.max_volume if data.max_volume is not None else 100
        if max_v <= min_v:
            return None
        return (data.volume - min_v) / (max_v - min_v)

    @property
    def is_volume_muted(self) -> bool | None:
        return self.coordinator.data.mute if self.coordinator.data else None

    @property
    def source(self) -> str | None:
        return self.coordinator.data.input_title if self.coordinator.data else None

    @property
    def source_list(self) -> list[str] | None:
        return getattr(self, "_source_titles", None)

    async def async_turn_on(self) -> None:
        await self.coordinator.client.set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.client.set_power(False)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        data = self.coordinator.data
        min_v = data.min_volume if data and data.min_volume is not None else 0
        max_v = data.max_volume if data and data.max_volume is not None else 100
        await self.coordinator.client.set_volume(round(min_v + volume * (max_v - min_v)))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.client.set_mute(mute)
        await self.coordinator.async_request_refresh()
