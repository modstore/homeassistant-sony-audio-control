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


def _source_icon(title: str | None) -> str | None:
    """Return a Home Assistant icon for common Sony source titles."""
    if not title:
        return None
    title_l = title.lower()
    if "tv" in title_l:
        return "mdi:television"
    if "bluetooth" in title_l:
        return "mdi:bluetooth"
    if "usb" in title_l:
        return "mdi:usb"
    if "hdmi" in title_l:
        return "mdi:video-input-hdmi"
    if "network" in title_l or "net" in title_l:
        return "mdi:lan"
    if "spotify" in title_l:
        return "mdi:spotify"
    return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
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
        super().__init__(
            coordinator,
            SettingDescription(
                key="media_player_main", name="Receiver", kind="sensor", service="core"
            ),
        )

    @property
    def icon(self) -> str | None:
        return _source_icon(self.source) or "mdi:audio-video"

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
        state = self.coordinator.data
        if not state or state.volume is None:
            return None
        vol = state.volume
        min_v = vol.min_volume
        max_v = vol.max_volume
        if max_v <= min_v:
            return None
        return (vol.volume - min_v) / (max_v - min_v)

    @property
    def is_volume_muted(self) -> bool | None:
        state = self.coordinator.data
        return state.volume.muted if state and state.volume else None

    @property
    def source(self) -> str | None:
        return self.coordinator.data.input_title if self.coordinator.data else None

    @property
    def source_list(self) -> list[str] | None:
        state = self.coordinator.data
        if not state or not state.sources:
            return None
        titles = [s.title for s in state.sources]
        # If the current source is not in the list, append it so the UI can display it
        current = self.source
        if current and current not in titles:
            titles.append(current)
        return titles

    async def async_turn_on(self) -> None:
        await self.coordinator.client.set_power(True)
        if self.coordinator.state:
            self.coordinator.state.power = "active"
            self.coordinator.async_update_listeners()

    async def async_turn_off(self) -> None:
        await self.coordinator.client.set_power(False)
        if self.coordinator.state:
            self.coordinator.state.power = "standby"
            self.coordinator.async_update_listeners()

    async def async_set_volume_level(self, volume: float) -> None:
        state = self.coordinator.data
        if not state or state.volume is None:
            return
        vol = state.volume
        await self.coordinator.async_set_volume(round(vol.min_volume + volume * (vol.max_volume - vol.min_volume)))

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.async_set_mute(mute)

    async def async_select_source(self, source: str) -> None:
        await self.coordinator.async_select_source(source)
