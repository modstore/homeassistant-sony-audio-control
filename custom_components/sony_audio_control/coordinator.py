"""Coordinator for Sony Audio Control."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SonyAudioApi, SonyAudioApiError
from .const import (
    CONF_PORT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_SELECT_TARGETS,
    DEFAULT_SPEAKER_LEVEL_TARGETS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class SonyAudioCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch shared state from a Sony audio device."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self.api = SonyAudioApi(self.host, self.port)
        self.system_info: dict[str, Any] = {}
        self.supported_api_info: Any = None
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the device."""
        data: dict[str, Any] = {
            "power": None,
            "volume": None,
            "inputs": [],
            "playing": None,
            "speaker_settings": {},
            "sound_settings": {},
        }

        try:
            if self.supported_api_info is None:
                try:
                    self.supported_api_info = await self.api.get_supported_api_info()
                except SonyAudioApiError as err:
                    _LOGGER.debug("Unable to read supported API info: %s", err)
                try:
                    system_result = await self.api.get_system_information()
                    if system_result:
                        self.system_info = system_result[0] if isinstance(system_result, list) else system_result
                except SonyAudioApiError as err:
                    _LOGGER.debug("Unable to read system information: %s", err)

            for key, coro in (
                ("power", self.api.get_power_status()),
                ("volume", self.api.get_volume_information()),
                ("inputs", self.api.get_ext_input()),
                ("playing", self.api.get_playing_content_info()),
            ):
                try:
                    data[key] = await coro
                except SonyAudioApiError as err:
                    _LOGGER.debug("Unable to update %s: %s", key, err)

            for target in DEFAULT_SPEAKER_LEVEL_TARGETS:
                try:
                    data["speaker_settings"][target] = await self.api.get_speaker_setting(target)
                except SonyAudioApiError as err:
                    _LOGGER.debug("Speaker setting %s unavailable: %s", target, err)

            for target in DEFAULT_SELECT_TARGETS:
                try:
                    data["sound_settings"][target] = await self.api.get_sound_setting(target)
                except SonyAudioApiError as err:
                    _LOGGER.debug("Sound setting %s unavailable: %s", target, err)

            return data
        except SonyAudioApiError as err:
            raise UpdateFailed(str(err)) from err

    @property
    def device_name(self) -> str:
        model = self.system_info.get("modelName") or self.system_info.get("model")
        return model or "Sony Audio Device"

    @property
    def device_info(self) -> dict[str, Any]:
        model = self.system_info.get("modelName") or self.system_info.get("model")
        serial = self.system_info.get("serial") or self.host
        return {
            "identifiers": {(DOMAIN, f"{self.host}:{self.port}")},
            "name": self.device_name,
            "manufacturer": "Sony",
            "model": model,
            "configuration_url": f"http://{self.host}:{self.port}/sony",
            "serial_number": serial,
        }
