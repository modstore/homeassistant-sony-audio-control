"""Async client for Sony ScalarWebAPI / SongPal-compatible audio devices."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

class SonyAudioApiError(Exception):
    """Raised when the Sony device returns or causes an API error."""

class SonyAudioApi:
    """Small JSON-RPC style client for Sony audio devices."""

    def __init__(self, host: str, port: int, session: aiohttp.ClientSession | None = None) -> None:
        self.host = host
        self.port = port
        self._session = session or aiohttp.ClientSession()
        self._own_session = session is None
        self._id = 1

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/sony"

    async def close(self) -> None:
        if self._own_session:
            await self._session.close()

    async def call(
        self,
        service: str,
        method: str,
        params: list[Any] | None = None,
        version: str = "1.0",
    ) -> Any:
        """Call a Sony service method."""
        self._id += 1
        payload = {
            "method": method,
            "id": self._id,
            "params": params or [],
            "version": version,
        }
        url = f"{self.base_url}/{service}"
        try:
            async with self._session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise SonyAudioApiError(f"HTTP {resp.status}: {text}")
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SonyAudioApiError(f"Unable to connect to Sony device: {err}") from err

        if "error" in data:
            raise SonyAudioApiError(f"Sony API error from {method}: {data['error']}")
        return data.get("result")

    async def test_connection(self) -> None:
        """Validate that the host responds to the Sony API."""
        try:
            await self.call("guide", "getSupportedApiInfo", [], "1.0")
        except SonyAudioApiError:
            # Some receivers respond on /system even if guide is limited.
            await self.call("system", "getSystemInformation", [], "1.0")

    async def get_supported_api_info(self) -> Any:
        return await self.call("guide", "getSupportedApiInfo", [], "1.0")

    async def get_system_information(self) -> Any:
        return await self.call("system", "getSystemInformation", [], "1.0")

    async def get_power_status(self) -> Any:
        return await self.call("system", "getPowerStatus", [], "1.0")

    async def set_power_status(self, status: str) -> None:
        await self.call("system", "setPowerStatus", [{"status": status}], "1.0")

    async def get_volume_information(self) -> Any:
        return await self.call("audio", "getVolumeInformation", [], "1.0")

    async def set_audio_volume(self, volume: str, target: str = "") -> None:
        params = [{"volume": volume}]
        if target:
            params[0]["target"] = target
        await self.call("audio", "setAudioVolume", params, "1.0")

    async def set_audio_mute(self, status: bool) -> None:
        await self.call("audio", "setAudioMute", [{"status": status}], "1.0")

    async def get_current_external_inputs_status(self) -> Any:
        return await self.call("avContent", "getCurrentExternalInputsStatus", [], "1.0")

    async def get_playing_content_info(self) -> Any:
        return await self.call("avContent", "getPlayingContentInfo", [], "1.0")

    async def get_ext_input(self) -> Any:
        return await self.call("avContent", "getExtInput", [], "1.0")

    async def set_play_content(self, uri: str) -> None:
        await self.call("avContent", "setPlayContent", [{"uri": uri}], "1.0")

    async def get_speaker_setting(self, target: str) -> Any:
        return await self.call("audio", "getSpeakerSettings", [{"target": target}], "1.0")

    async def set_speaker_setting(self, target: str, value: str) -> None:
        await self.call(
            "audio",
            "setSpeakerSettings",
            [{"settings": [{"target": target, "value": value}]}],
            "1.0",
        )

    async def get_sound_setting(self, target: str) -> Any:
        return await self.call("audio", "getSoundSettings", [{"target": target}], "1.0")

    async def set_sound_setting(self, target: str, value: str) -> None:
        await self.call(
            "audio",
            "setSoundSettings",
            [{"settings": [{"target": target, "value": value}]}],
            "1.0",
        )
