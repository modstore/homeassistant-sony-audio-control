"""DataUpdateCoordinator for Sony Audio Control."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .sony.client import SonyAudioClient
from .sony.discovery import discover_settings
from .sony.models import DeviceSnapshot, SettingDescription
from .sony.exceptions import SonyAudioError

_LOGGER = logging.getLogger(__name__)


class SonyAudioCoordinator(DataUpdateCoordinator[DeviceSnapshot]):
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
        self.setting_descriptions: list[SettingDescription] = []

    async def async_discover(self) -> None:
        self.supported_api_info, self.setting_descriptions = await discover_settings(self.client)

    async def _async_update_data(self) -> DeviceSnapshot:
        try:
            system_info = await self.client.system_information()
            power_status = await self.client.power_status()
            volumes = await self.client.volume_information()
            sources = await self.client.source_list()
            playing_info = await self.client.playing_content_info()

            snap = DeviceSnapshot(
                available=True,
                model_name=system_info.get("modelName") or system_info.get("model") or system_info.get("productName"),
                device_name=system_info.get("productName") or system_info.get("deviceName") or system_info.get("modelName"),
                power=power_status.get("status"),
                system_info=system_info,
                playing_info=playing_info,
            )

            speaker_volume = next((v for v in volumes if v.get("target") in ("speaker", "")), volumes[0] if volumes else {})
            if speaker_volume:
                if speaker_volume.get("volume") is not None:
                    snap.volume = int(float(speaker_volume["volume"]))
                if speaker_volume.get("minVolume") is not None:
                    snap.min_volume = int(float(speaker_volume["minVolume"]))
                if speaker_volume.get("maxVolume") is not None:
                    snap.max_volume = int(float(speaker_volume["maxVolume"]))
                if speaker_volume.get("mute") is not None:
                    mute = speaker_volume["mute"]

                    if isinstance(mute, str):
                        snap.mute = mute.lower() == "on"
                    else:
                        snap.mute = bool(mute)

            current_source = next((s for s in sources if s.get("active") or s.get("status") == "active"), sources[0] if sources else {})
            snap.input_uri = current_source.get("uri") or playing_info.get("uri")
            snap.input_title = current_source.get("title") or playing_info.get("source") or playing_info.get("title")

            for desc in self.setting_descriptions:
                if not desc.target or desc.key in {"media_player_main", "audio_mute", "input_source"}:
                    continue
                if desc.get_method == "getSpeakerSettings":
                    data = await self.client.try_call(desc.service, desc.get_method, [{"target": desc.target}])
                    value = _extract_value(data)
                    if value is not None:
                        snap.speaker_settings[desc.target] = value
                elif desc.get_method == "getSoundSettings":
                    data = await self.client.try_call(desc.service, desc.get_method, [{"target": desc.target}])
                    value = _extract_value(data)
                    if value is not None:
                        snap.sound_settings[desc.target] = value

            return snap
        except SonyAudioError as err:
            raise UpdateFailed(str(err)) from err


def _extract_value(payload: Any) -> Any:
    if isinstance(payload, dict):
        if "settings" in payload and isinstance(payload["settings"], list) and payload["settings"]:
            return _extract_value(payload["settings"][0])
        return payload.get("currentValue", payload.get("value"))
    if isinstance(payload, list):
        for item in payload:
            value = _extract_value(item)
            if value is not None:
                return value
    return None
