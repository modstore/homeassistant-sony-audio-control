"""Async Sony ScalarWebAPI / SongPal style JSON-RPC client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from .exceptions import SonyAudioApiError, SonyAudioConnectionError

_LOGGER = logging.getLogger(__name__)


class SonyAudioClient:
    """Thin async client for Sony audio devices using local JSON-RPC endpoints."""

    def __init__(self, session: ClientSession, host: str, port: int = 10000, timeout: int = 10) -> None:
        self.session = session
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}/sony"
        self._request_id = 1

    async def call(
        self,
        service: str,
        method: str,
        params: list[Any] | None = None,
        version: str = "1.0",
    ) -> Any:
        """Call a Sony API method and return the first result object when available."""
        self._request_id += 1
        payload = {
            "method": method,
            "id": self._request_id,
            "params": params or [],
            "version": version,
        }
        url = f"{self.base_url}/{service}"
        try:
            async with asyncio.timeout(self.timeout):
                async with self.session.post(url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
        except (TimeoutError, ClientError, OSError) as err:
            raise SonyAudioConnectionError(f"Unable to call {service}/{method}: {err}") from err

        if isinstance(data, dict) and "error" in data:
            raise SonyAudioApiError(f"Sony API error from {service}/{method}: {data['error']}", error=data["error"])

        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, list):
            if len(result) == 1:
                return result[0]
            return result
        return result

    async def try_call(self, service: str, method: str, params: list[Any] | None = None, version: str = "1.0") -> Any | None:
        """Call an API method, returning None on unsupported/unavailable methods."""
        try:
            return await self.call(service, method, params, version)
        except SonyAudioApiError as err:
            _LOGGER.debug("Sony API method unavailable: %s/%s (%s)", service, method, err)
            return None

    async def supported_api_info(self) -> dict[str, Any]:
        """Return supported service/method information.

        Some Sony audio devices return ``Illegal Argument`` for the usual
        guide/getSupportedApiInfo call shape even though the device supports
        the audio APIs directly. Treat guide discovery as optional so setup can
        continue and the integration can probe known safe audio endpoints.
        """
        for params in ([{}], [], [{"services": []}]):
            data = await self.try_call("guide", "getSupportedApiInfo", params)
            if data is None:
                continue
            if isinstance(data, dict):
                return data
            return {"services": data or []}
        _LOGGER.debug("guide/getSupportedApiInfo unavailable; continuing with probe-based discovery")
        return {"services": []}

    async def system_information(self) -> dict[str, Any]:
        """Return system information where supported."""
        for version in ("1.4", "1.3", "1.0"):
            data = await self.try_call("system", "getSystemInformation", [], version=version)
            if isinstance(data, dict):
                return data
        return {}

    async def power_status(self) -> dict[str, Any]:
        for version in ("1.1", "1.0"):
            data = await self.try_call("system", "getPowerStatus", [], version=version)
            if isinstance(data, dict):
                return data
        return {}

    async def set_power(self, active: bool) -> None:
        await self.call("system", "setPowerStatus", [{"status": "active" if active else "standby"}], version="1.1")

    async def volume_information(self) -> list[dict[str, Any]]:
        # Receivers differ on the accepted params shape. Try the self-describing
        # empty-object call first; STR-DN1080 returns Illegal Argument for [] here.
        for params, version in (([{}], "1.1"), ([{"target": "speaker"}], "1.1"), ([], "1.1"), ([{}], "1.0")):
            data = await self.try_call("audio", "getVolumeInformation", params, version=version)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                return [data]
        return []

    async def set_volume(self, volume: int, *, target: str = "speaker") -> None:
        await self.call("audio", "setAudioVolume", [{"target": target, "volume": str(volume), "ui": "on"}], version="1.1")

    async def set_mute(self, mute: bool, *, target: str = "speaker") -> None:
        await self.call("audio", "setAudioMute", [{"target": target, "status": mute}], version="1.1")

    async def get_sound_setting(self, target: str) -> Any:
        return await self.call("audio", "getSoundSettings", [{"target": target}], version="1.1")

    async def set_sound_setting(self, target: str, value: str) -> None:
        await self.call("audio", "setSoundSettings", [{"settings": [{"target": target, "value": value}]}], version="1.1")

    async def get_speaker_setting(self, target: str) -> Any:
        return await self.call("audio", "getSpeakerSettings", [{"target": target}])

    async def set_speaker_setting(self, target: str, value: str) -> None:
        await self.call("audio", "setSpeakerSettings", [{"settings": [{"target": target, "value": value}]}])

    async def source_list(self) -> list[dict[str, Any]]:
        data = await self.try_call("avContent", "getCurrentExternalTerminalsStatus")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    async def playing_content_info(self) -> dict[str, Any]:
        data = await self.try_call("avContent", "getPlayingContentInfo")
        return data if isinstance(data, dict) else {}

    async def set_play_content(self, uri: str) -> None:
        await self.call("avContent", "setPlayContent", [{"uri": uri}])

    async def dump_device_info(self, discovered_targets: list[str] | None = None) -> dict[str, Any]:
        """Best-effort device dump for diagnostics and issue reports.

        This deliberately favours successful partial diagnostics over failing the
        whole dump when a model does not support a method or requires a slightly
        different params shape.
        """
        dump: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "supported_api_info": await self.supported_api_info(),
            "system_information": await self.system_information(),
            "power_status": await self.power_status(),
            "volume_information": await self.volume_information(),
            "speaker_settings_all": await self.try_call("audio", "getSpeakerSettings", [{}]),
            "sound_settings_all": await self.try_call("audio", "getSoundSettings", [{}], version="1.1"),
            "custom_equalizer_settings": await self.try_call("audio", "getCustomEqualizerSettings", [{}]),
            "source_list": await self.try_call("avContent", "getSourceList", [{"scheme": "extInput"}], version="1.2"),
            "current_external_terminals_status": await self.try_call("avContent", "getCurrentExternalTerminalsStatus"),
            "playing_content_info": await self.try_call("avContent", "getPlayingContentInfo", [], version="1.2"),
            "available_playback_function": await self.try_call("avContent", "getAvailablePlaybackFunction"),
            "power_settings": await self.try_call("system", "getPowerSettings", [{}]),
            "sleep_timer_settings": await self.try_call("system", "getSleepTimerSettings", [{}]),
            "device_misc_settings": await self.try_call("system", "getDeviceMiscSettings", [{}]),
            "interface_information": await self.try_call("system", "getInterfaceInformation"),
            "software_update_info": await self.try_call("system", "getSWUpdateInfo"),
        }
        settings: dict[str, Any] = {}
        for target in discovered_targets or []:
            settings[target] = {
                "sound": await self.try_call("audio", "getSoundSettings", [{"target": target}], version="1.1"),
                "speaker": await self.try_call("audio", "getSpeakerSettings", [{"target": target}]),
            }
        dump["target_probe_results"] = settings
        return dump
