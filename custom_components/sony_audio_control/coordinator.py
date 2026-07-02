"""DataUpdateCoordinator for Sony Audio Control."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .sony.client import SonyAudioClient
from .sony.discovery import discover_settings
from .sony.exceptions import SonyAudioError
from .sony.models import SonyState

_LOGGER = logging.getLogger(__name__)


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

    @property
    def state(self) -> SonyState | None:
        """Return the current Sony state (alias for coordinator.data)."""
        return self.data

    async def async_discover(self) -> None:
        self.supported_api_info, self.setting_descriptions = await discover_settings(
            self.client
        )

    async def _async_update_data(self) -> SonyState:
        try:
            start = datetime.now()
            _LOGGER.debug("Refresh started")

            speaker_settings = await self.client.get_speaker_settings()
            _LOGGER.debug("Speaker settings: %d", len(speaker_settings))

            sound_settings = await self.client.get_sound_settings()
            _LOGGER.debug("Sound settings: %d", len(sound_settings))

            volume = await self.client.get_volume()
            _LOGGER.debug("Volume: %s", volume)

            system = await self.client.get_system()
            _LOGGER.debug("System: %s", system.firmware if system else None)

            # Extra calls for media player and core sensors (approved overhead)
            power_status = await self.client.power_status()
            sources = await self.client.source_list()
            playing_info = await self.client.playing_content_info()

            elapsed = (datetime.now() - start).total_seconds() * 1000
            _LOGGER.debug("Refresh complete (%.0fms)", elapsed)

            system_info = system.raw if system else {}
            model_name = (
                system_info.get("modelName")
                or system_info.get("model")
                or system_info.get("productName")
            )
            device_name = (
                system_info.get("productName")
                or system_info.get("deviceName")
                or system_info.get("modelName")
            )

            current_source = next(
                (
                    s
                    for s in sources
                    if s.get("active") or s.get("status") == "active"
                ),
                sources[0] if sources else {},
            )

            return SonyState(
                speaker_settings=speaker_settings,
                sound_settings=sound_settings,
                volume=volume,
                system=system,
                power=power_status.get("status"),
                input_uri=current_source.get("uri") or playing_info.get("uri"),
                input_title=current_source.get("title")
                or playing_info.get("source")
                or playing_info.get("title"),
                model_name=model_name,
                device_name=device_name,
                last_update=datetime.now(),
            )
        except SonyAudioError as err:
            raise UpdateFailed(str(err)) from err
