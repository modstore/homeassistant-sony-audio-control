"""DataUpdateCoordinator for Sony Audio Control."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN, SLOW_SCAN_INTERVAL_SECONDS
from .sony.client import SonyAudioClient
from .sony.discovery import discover_settings
from .sony.exceptions import SonyAudioError
from .sony.models import SonySource, SonyState

_LOGGER = logging.getLogger(__name__)


def _source_icon(title: str) -> str | None:
    """Return a Home Assistant icon for common Sony source titles."""
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


class SonyAudioCoordinator(DataUpdateCoordinator[SonyState]):
    """Coordinator for Sony audio device data."""

    def __init__(self, hass: HomeAssistant, client: SonyAudioClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.supported_api_info: dict[str, Any] = {}
        self.setting_descriptions: list = []
        self._slow_cache: dict[str, Any] = {}
        self._last_slow_refresh: datetime | None = None

    @property
    def state(self) -> SonyState | None:
        """Return the current Sony state (alias for coordinator.data)."""
        return self.data

    async def async_discover(self) -> None:
        self.supported_api_info, self.setting_descriptions = await discover_settings(
            self.client
        )

    async def async_set_setting(self, domain: str, target: str, value: Any) -> None:
        """Set a speaker or sound setting and optimistically update cache."""
        if domain == "speaker":
            await self.async_set_speaker_setting(target, value)
        elif domain == "sound":
            await self.async_set_sound_setting(target, value)
        else:
            raise ValueError(f"Unknown domain: {domain}")

    async def async_set_speaker_setting(self, target: str, value: Any) -> None:
        """Set a speaker setting and optimistically update cache."""
        await self.client.set_speaker_setting(target, str(value))
        if self.state and target in self.state.speaker_settings:
            self.state.speaker_settings[target].current_value = value
            self.async_update_listeners()
            _LOGGER.debug("Optimistic update applied: speaker.%s=%s", target, value)
        else:
            _LOGGER.debug("Optimistic update skipped: target %s not in cache", target)

    async def async_set_sound_setting(self, target: str, value: Any) -> None:
        """Set a sound setting and optimistically update cache."""
        await self.client.set_sound_setting(target, str(value))
        if self.state and target in self.state.sound_settings:
            self.state.sound_settings[target].current_value = value
            self.async_update_listeners()
            _LOGGER.debug("Optimistic update applied: sound.%s=%s", target, value)
        else:
            _LOGGER.debug("Optimistic update skipped: target %s not in cache", target)

    async def async_set_volume(self, volume: int | float) -> None:
        """Set volume and optimistically update cache."""
        await self.client.set_volume(int(volume))
        if self.state and self.state.volume is not None:
            self.state.volume.volume = int(volume)
            self.async_update_listeners()
            _LOGGER.debug("Optimistic update applied: volume.volume=%s", volume)

    async def async_set_mute(self, muted: bool) -> None:
        """Set mute and optimistically update cache."""
        await self.client.set_mute(muted)
        if self.state and self.state.volume is not None:
            self.state.volume.muted = muted
            self.async_update_listeners()
            _LOGGER.debug("Optimistic update applied: volume.muted=%s", muted)

    async def async_select_source(self, source: str) -> None:
        """Select a source and optimistically update cache."""
        if not self.state or not self.state.sources:
            _LOGGER.debug("Optimistic update skipped: no cached sources")
            return
        matched = next((s for s in self.state.sources if s.title == source), None)
        if not matched:
            _LOGGER.debug("Optimistic update skipped: source %s not in cached sources", source)
            return
        await self.client.set_play_content(matched.uri)
        self.state.input_title = source
        self.state.input_uri = matched.uri
        self.async_update_listeners()
        _LOGGER.debug("Optimistic update applied: source=%s", source)

    async def _async_update_data(self) -> SonyState:
        try:
            start = datetime.now()
            _LOGGER.debug("Refresh started")

            speaker_settings = await self.client.get_speaker_settings()
            _LOGGER.debug(
                "Speaker settings:\n%d discovered", len(speaker_settings)
            )

            sound_settings = await self.client.get_sound_settings()
            _LOGGER.debug(
                "Sound settings:\n%d discovered", len(sound_settings)
            )

            volume = await self.client.get_volume()
            _LOGGER.debug("Volume updated")

            power_status = await self.client.power_status()
            _LOGGER.debug("Power status: %s", power_status.get("status"))

            playing_info = await self.client.playing_content_info()
            _LOGGER.debug(
                "Current source:\n%s",
                playing_info.get("source") or playing_info.get("title"),
            )

            now = datetime.now()
            slow_due = (
                self._last_slow_refresh is None
                or (now - self._last_slow_refresh).total_seconds()
                >= SLOW_SCAN_INTERVAL_SECONDS
            )

            if slow_due:
                _LOGGER.debug("Slow refresh started")
                self.supported_api_info = await self.client.supported_api_info()
                system = await self.client.get_system()
                raw_sources = await self.client.get_av_sources()
                sources = [
                    SonySource(
                        uri=str(s.get("source", "")),
                        title=str(s.get("title", "")),
                        icon=_source_icon(str(s.get("title", ""))),
                    )
                    for s in raw_sources
                    if s.get("source") and s.get("title")
                ]
                self._slow_cache = {
                    "system": system,
                    "sources": sources,
                }
                self._last_slow_refresh = now
                _LOGGER.debug("Slow refresh completed")
            else:
                _LOGGER.debug("Using cached slow data")

            cached_system = self._slow_cache.get("system")
            cached_sources: list[SonySource] = self._slow_cache.get("sources", [])

            system_info = cached_system.raw if cached_system else {}
            model_name = (
                system_info.get("modelName")
                or system_info.get("model")
                or system_info.get("productName")
            )
            device_name = (
                system_info.get("productName")
                or system_info.get("deviceName")
                or system_info.get("modelName")
                or model_name
            )

            input_title = playing_info.get("source") or playing_info.get("title")
            input_uri = playing_info.get("uri")

            # Preserve current source from cache if the device reports nothing
            if not input_title and self.data:
                input_title = self.data.input_title
                input_uri = input_uri or self.data.input_uri

            elapsed = (datetime.now() - start).total_seconds() * 1000
            _LOGGER.debug("Refresh completed\nDuration: %.0f ms", elapsed)

            return SonyState(
                speaker_settings=speaker_settings,
                sound_settings=sound_settings,
                volume=volume,
                system=cached_system,
                power=power_status.get("status"),
                input_uri=input_uri,
                input_title=input_title,
                model_name=model_name,
                device_name=device_name,
                sources=cached_sources,
                last_update=datetime.now(),
            )
        except SonyAudioError as err:
            raise UpdateFailed(str(err)) from err
