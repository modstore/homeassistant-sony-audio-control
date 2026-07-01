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
        """Return supported service/method information."""
        result = await self.call("guide", "getSupportedApiInfo", [])
        if isinstance(result, dict):
            return result
        return {"services": result or []}

    async def system_information(self) -> dict[str, Any]:
        """Return system information where supported."""
        data = await self.try_call("system", "getSystemInformation")
        return data if isinstance(data, dict) else {}

    async def power_status(self) -> dict[str, Any]:
        data = await self.try_call("system", "getPowerStatus")
        return data if isinstance(data, dict) else {}

    async def set_power(self, active: bool) -> None:
        await self.call("system", "setPowerStatus", [{"status": "active" if active else "standby"}])

    async def volume_information(self) -> list[dict[str, Any]]:
        data = await self.try_call("audio", "getVolumeInformation")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    async def set_volume(self, volume: int, *, target: str = "speaker") -> None:
        await self.call("audio", "setAudioVolume", [{"target": target, "volume": str(volume), "ui": "on"}])

    async def set_mute(self, mute: bool, *, target: str = "speaker") -> None:
        await self.call("audio", "setAudioMute", [{"target": target, "status": mute}])

    async def get_sound_setting(self, target: str) -> Any:
        return await self.call("audio", "getSoundSettings", [{"target": target}])

    async def set_sound_setting(self, target: str, value: str) -> None:
        await self.call("audio", "setSoundSettings", [{"settings": [{"target": target, "value": value}]}])

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
        """Best-effort device dump for diagnostics and issue reports."""
        dump: dict[str, Any] = {
            "supported_api_info": await self.try_call("guide", "getSupportedApiInfo"),
            "system_information": await self.try_call("system", "getSystemInformation"),
            "power_status": await self.try_call("system", "getPowerStatus"),
            "volume_information": await self.try_call("audio", "getVolumeInformation"),
            "external_terminals": await self.try_call("avContent", "getCurrentExternalTerminalsStatus"),
            "playing_content_info": await self.try_call("avContent", "getPlayingContentInfo"),
        }
        settings: dict[str, Any] = {}
        for target in discovered_targets or []:
            settings[target] = {
                "sound": await self.try_call("audio", "getSoundSettings", [{"target": target}]),
                "speaker": await self.try_call("audio", "getSpeakerSettings", [{"target": target}]),
            }
        dump["target_probe_results"] = settings
        return dump
