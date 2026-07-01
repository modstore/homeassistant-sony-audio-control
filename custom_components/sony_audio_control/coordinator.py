from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SonyAudioApi, SonyAudioApiError, SonyApiMethod
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .discovery import DynamicSettingDescription, discover_dynamic_settings


@dataclass
class SonyAudioData:
    power_status: str | None = None
    volumes: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    playing_content: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, dict[str, Any] | None] = field(default_factory=dict)


class SonyAudioCoordinator(DataUpdateCoordinator[SonyAudioData]):
    """Coordinator holding discovered capabilities and current state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api = SonyAudioApi(
            async_get_clientsession(hass),
            entry.data["host"],
            int(entry.data["port"]),
        )
        self.supported_methods: dict[str, SonyApiMethod] = {}
        self.dynamic_settings: list[DynamicSettingDescription] = []
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def async_config_entry_first_refresh(self) -> None:
        await self.async_discover()
        await super().async_config_entry_first_refresh()

    async def async_discover(self) -> None:
        self.supported_methods = await self.api.get_supported_api_info()
        self.dynamic_settings = await discover_dynamic_settings(self.api)

    async def _async_update_data(self) -> SonyAudioData:
        try:
            data = SonyAudioData()
            data.power_status = await self.api.power_status()
            data.volumes = await self.api.get_volume_information()
            data.inputs = await self.api.get_current_external_inputs_status()
            data.playing_content = await self.api.get_playing_content_info()
            for desc in self.dynamic_settings:
                data.settings[desc.key] = await self.api.get_setting(desc.getter, desc.target)
            return data
        except SonyAudioApiError as err:
            raise UpdateFailed(str(err)) from err

    def setting_value(self, key: str) -> Any:
        setting = self.data.settings.get(key) if self.data else None
        if isinstance(setting, dict):
            return setting.get("currentValue", setting.get("value"))
        return None

    def primary_volume(self) -> dict[str, Any] | None:
        if not self.data:
            return None
        for volume in self.data.volumes:
            if volume.get("target") in ("master", "speaker", "main"):
                return volume
        return self.data.volumes[0] if self.data.volumes else None
