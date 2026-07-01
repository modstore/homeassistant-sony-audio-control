from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class SonyAudioApiError(Exception):
    """Base API error."""


class SonyAudioApiConnectionError(SonyAudioApiError):
    """Connection error."""


class SonyAudioApiResponseError(SonyAudioApiError):
    """Unexpected or error response."""


@dataclass(frozen=True)
class SonyApiMethod:
    service: str
    name: str
    versions: tuple[str, ...]


class SonyAudioApi:
    """Small async client for Sony ScalarWebAPI/SongPal-style devices."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self.session = session
        self.host = host
        self.port = port
        self._request_id = 1

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/sony"

    async def call(
        self,
        service: str,
        method: str,
        params: list[Any] | None = None,
        version: str = "1.0",
    ) -> Any:
        """Call a Sony API method and return the raw result payload."""
        self._request_id += 1
        payload: dict[str, Any] = {
            "method": method,
            "id": self._request_id,
            "params": params or [],
            "version": version,
        }
        url = f"{self.base_url}/{service}"
        try:
            async with self.session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                text = await response.text()
                if response.status >= 400:
                    raise SonyAudioApiResponseError(
                        f"HTTP {response.status} calling {service}.{method}: {text}"
                    )
                data = await response.json(content_type=None)
        except asyncio.TimeoutError as err:
            raise SonyAudioApiConnectionError(f"Timeout calling {url}") from err
        except aiohttp.ClientError as err:
            raise SonyAudioApiConnectionError(f"Error calling {url}: {err}") from err

        if "error" in data:
            raise SonyAudioApiResponseError(f"Sony API error for {service}.{method}: {data['error']}")
        return data.get("result")

    async def try_call(
        self,
        service: str,
        method: str,
        params: list[Any] | None = None,
        version: str = "1.0",
    ) -> Any | None:
        """Call a method, returning None on unsupported/errors."""
        try:
            return await self.call(service, method, params, version)
        except SonyAudioApiError as err:
            _LOGGER.debug("Sony API probe failed for %s.%s: %s", service, method, err)
            return None

    async def get_supported_api_info(self) -> dict[str, SonyApiMethod]:
        """Return supported API methods keyed by method name.

        Different devices return slightly different structures, so this parser is permissive.
        """
        result = await self.try_call("guide", "getSupportedApiInfo", [], "1.0")
        methods: dict[str, SonyApiMethod] = {}
        if not result:
            return methods

        payload = result[0] if isinstance(result, list) and result else result
        service_infos = payload if isinstance(payload, list) else payload.get("service", []) if isinstance(payload, dict) else []

        for service_info in service_infos:
            service_name = service_info.get("service") or service_info.get("name") or service_info.get("serviceName")
            if not service_name:
                continue
            for api in service_info.get("protocols", []) + service_info.get("apis", []) + service_info.get("methods", []):
                name = api.get("name") or api.get("method")
                if not name:
                    continue
                versions_raw = api.get("versions") or api.get("version") or ["1.0"]
                if isinstance(versions_raw, str):
                    versions = (versions_raw,)
                else:
                    versions = tuple(str(v) for v in versions_raw) or ("1.0",)
                methods[name] = SonyApiMethod(str(service_name), str(name), versions)
        return methods

    async def power_status(self) -> str | None:
        result = await self.try_call("system", "getPowerStatus", [], "1.1") or await self.try_call("system", "getPowerStatus", [], "1.0")
        item = _first_item(result)
        return item.get("status") if isinstance(item, dict) else None

    async def set_power(self, active: bool) -> None:
        await self.call("system", "setPowerStatus", [{"status": active}], "1.1")

    async def get_volume_information(self) -> list[dict[str, Any]]:
        result = await self.try_call("audio", "getVolumeInformation", [], "1.0")
        if isinstance(result, list) and result and isinstance(result[0], list):
            return [x for x in result[0] if isinstance(x, dict)]
        if isinstance(result, list):
            return [x for x in result if isinstance(x, dict)]
        return []

    async def set_volume(self, volume: int, target: str = "master") -> None:
        await self.call("audio", "setAudioVolume", [{"target": target, "volume": str(volume)}], "1.0")

    async def set_mute(self, mute: bool, target: str = "master") -> None:
        await self.call("audio", "setAudioMute", [{"target": target, "mute": mute}], "1.0")

    async def get_current_external_inputs_status(self) -> list[dict[str, Any]]:
        result = await self.try_call("avContent", "getCurrentExternalInputsStatus", [], "1.0")
        if isinstance(result, list) and result and isinstance(result[0], list):
            return [x for x in result[0] if isinstance(x, dict)]
        if isinstance(result, list):
            return [x for x in result if isinstance(x, dict)]
        return []

    async def get_playing_content_info(self) -> dict[str, Any]:
        result = await self.try_call("avContent", "getPlayingContentInfo", [], "1.0")
        item = _first_item(result)
        return item if isinstance(item, dict) else {}

    async def get_setting(self, getter: str, target: str) -> dict[str, Any] | None:
        service = "audio"
        result = await self.try_call(service, getter, [{"target": target}], "1.0")
        item = _first_item(result)
        if isinstance(item, dict):
            return item
        return None

    async def set_setting(self, setter: str, target: str, value: Any) -> None:
        await self.call("audio", setter, [{"settings": [{"target": target, "value": str(value)}]}], "1.0")


def _first_item(result: Any) -> Any:
    if isinstance(result, list) and result:
        if isinstance(result[0], list) and result[0]:
            return result[0][0]
        return result[0]
    return result
