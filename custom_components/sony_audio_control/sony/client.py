"""Async Sony ScalarWebAPI / SongPal style JSON-RPC client."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from aiohttp import ClientError, ClientSession

from .constants import (
    GET_AVAILABLE_PLAYBACK_FUNCTION,
    GET_CURRENT_EXTERNAL_TERMINALS_STATUS,
    GET_CUSTOM_EQUALIZER_SETTINGS,
    GET_DEVICE_MISC_SETTINGS,
    GET_INTERFACE_INFORMATION,
    GET_PLAYING_CONTENT_INFO,
    GET_POWER_SETTINGS,
    GET_POWER_STATUS,
    GET_SLEEP_TIMER_SETTINGS,
    GET_SOUND_SETTINGS,
    GET_SOURCE_LIST,
    GET_SPEAKER_SETTINGS,
    GET_SUPPORTED_API_INFO,
    GET_SW_UPDATE_INFO,
    GET_SYSTEM_INFORMATION,
    GET_VOLUME_INFORMATION,
    SERVICE_AUDIO,
    SERVICE_AV_CONTENT,
    SERVICE_GUIDE,
    SERVICE_SYSTEM,
    SET_AUDIO_MUTE,
    SET_AUDIO_VOLUME,
    SET_PLAY_CONTENT,
    SET_POWER_STATUS,
    SET_SOUND_SETTINGS,
    SET_SPEAKER_SETTINGS,
)
from .exceptions import SonyAudioApiError, SonyAudioConnectionError
from .models import (
    SettingType,
    SonySetting,
    SonySystem,
    SonyVolume,
)

_LOGGER = logging.getLogger(__name__)


def _extract_settings_payloads(payload: Any) -> list[dict[str, Any]]:
    """Normalize many known Sony setting response shapes and return all settings."""
    if isinstance(payload, dict):
        if "settings" in payload and isinstance(payload["settings"], list):
            return [item for item in payload["settings"] if isinstance(item, dict)]
        if (
            "target" in payload
            or "value" in payload
            or "currentValue" in payload
            or "candidate" in payload
        ):
            return [payload]
        return []
    if isinstance(payload, list):
        out: list[dict[str, Any]] = []
        for item in payload:
            out.extend(_extract_settings_payloads(item))
        return out
    return []


def _parse_sony_setting(setting: dict[str, Any]) -> SonySetting:
    """Parse a raw Sony setting dict into a SonySetting dataclass."""
    target = str(setting.get("target", ""))
    title = str(setting.get("title", target))
    sony_type_str = str(setting.get("type") or "")

    try:
        setting_type: SettingType | str = SettingType(sony_type_str)
    except ValueError:
        setting_type = sony_type_str

    current_value = setting.get("currentValue") or setting.get("value")
    available = setting.get("isAvailable", True)

    candidates: list[Any] = []
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None

    raw_candidates = setting.get("candidate") or setting.get("candidates") or []
    if isinstance(raw_candidates, list):
        for candidate in raw_candidates:
            if isinstance(candidate, dict):
                if candidate.get("isAvailable") is False:
                    continue
                candidates.append(candidate)
                if candidate.get("min") is not None and float(candidate["min"]) != -1:
                    minimum = float(candidate["min"])
                if candidate.get("max") is not None and float(candidate["max"]) != -1:
                    maximum = float(candidate["max"])
                if candidate.get("step") is not None and float(candidate["step"]) != -1:
                    step = float(candidate["step"])
            elif candidate not in (None, ""):
                candidates.append(candidate)
    elif isinstance(raw_candidates, dict):
        if raw_candidates.get("min") is not None:
            minimum = float(raw_candidates["min"])
        if raw_candidates.get("max") is not None:
            maximum = float(raw_candidates["max"])
        if raw_candidates.get("step") is not None:
            step = float(raw_candidates["step"])

    return SonySetting(
        target=target,
        title=title,
        type=setting_type,
        current_value=current_value,
        available=available,
        candidates=candidates,
        minimum=minimum,
        maximum=maximum,
        step=step,
        raw=setting,
    )


def _parse_sony_volume(data: dict[str, Any]) -> SonyVolume:
    """Parse a raw Sony volume dict into a SonyVolume dataclass."""
    volume_raw = data.get("volume")
    mute_raw = data.get("mute")
    max_v = data.get("maxVolume")
    min_v = data.get("minVolume")
    step_raw = data.get("step")

    muted = False
    if isinstance(mute_raw, str):
        muted = mute_raw.lower() == "on"
    elif mute_raw is not None:
        muted = bool(mute_raw)

    return SonyVolume(
        volume=int(float(volume_raw)) if volume_raw is not None else 0,
        muted=muted,
        max_volume=int(float(max_v)) if max_v is not None else 100,
        min_volume=int(float(min_v)) if min_v is not None else 0,
        step=int(float(step_raw)) if step_raw is not None else 1,
    )


class SonyAudioClient:
    """Thin async client for Sony audio devices using local JSON-RPC endpoints."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        port: int = 10000,
        timeout: int = 10,
    ) -> None:
        self.session = session
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}/sony"
        self._request_id = 1
        self.api_timings: dict[str, dict[str, Any]] = {}
        self.successful_methods: set[str] = set()
        self.failed_methods: set[str] = set()
        self.sony_error_codes: list[dict[str, Any]] = []

    async def _execute_call(
        self,
        service: str,
        method: str,
        params: list[Any] | None = None,
        version: str = "1.0",
    ) -> Any:
        """Execute the HTTP request without timing or tracking."""
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
            raise SonyAudioConnectionError(
                f"Unable to call {service}/{method}: {err}"
            ) from err

        if isinstance(data, dict) and "error" in data:
            raise SonyAudioApiError(
                f"Sony API error from {service}/{method}: {data['error']}",
                error=data["error"],
            )

        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, list):
            if len(result) == 1:
                return result[0]
            return result
        return result

    async def call(
        self,
        service: str,
        method: str,
        params: list[Any] | None = None,
        version: str = "1.0",
    ) -> Any:
        """Call a Sony API method and return the first result object when available."""
        start = time.perf_counter()
        try:
            result = await self._execute_call(service, method, params, version)
            self.successful_methods.add(method)
            return result
        except SonyAudioApiError as err:
            self.failed_methods.add(method)
            if isinstance(getattr(err, "error", None), list):
                self.sony_error_codes.append({"method": method, "error": err.error})
            raise
        except SonyAudioConnectionError:
            self.failed_methods.add(method)
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.api_timings[method] = {"method": method, "duration_ms": round(duration_ms)}

    async def try_call(
        self,
        service: str,
        method: str,
        params: list[Any] | None = None,
        version: str = "1.0",
    ) -> Any | None:
        """Call an API method, returning None on unsupported/unavailable methods."""
        try:
            return await self.call(service, method, params, version)
        except (SonyAudioApiError, SonyAudioConnectionError):
            _LOGGER.debug(
                "Sony API method unavailable: %s/%s", service, method
            )
            return None

    # -- Typed getters (new) -------------------------------------------------

    async def get_speaker_settings(self) -> dict[str, SonySetting]:
        """Fetch and parse all speaker settings."""
        payload = await self.try_call(SERVICE_AUDIO, GET_SPEAKER_SETTINGS, [{}])
        settings = _extract_settings_payloads(payload)
        return {
            str(s.get("target")): _parse_sony_setting(s)
            for s in settings
            if isinstance(s, dict) and s.get("target") and s.get("isAvailable", True)
        }

    async def get_sound_settings(self) -> dict[str, SonySetting]:
        """Fetch and parse all sound settings."""
        payload = await self.try_call(
            SERVICE_AUDIO, GET_SOUND_SETTINGS, [{}], version="1.1"
        )
        settings = _extract_settings_payloads(payload)
        return {
            str(s.get("target")): _parse_sony_setting(s)
            for s in settings
            if isinstance(s, dict) and s.get("target") and s.get("isAvailable", True)
        }

    async def get_volume(self) -> SonyVolume | None:
        """Fetch and parse the primary output volume."""
        for params, version in (
            ([{}], "1.1"),
            ([{"target": "speaker"}], "1.1"),
            ([], "1.1"),
            ([{}], "1.0"),
        ):
            data = await self.try_call(
                SERVICE_AUDIO, GET_VOLUME_INFORMATION, params, version=version
            )
            volumes: list[dict[str, Any]] = []
            if isinstance(data, list):
                volumes = [item for item in data if isinstance(item, dict)]
            elif isinstance(data, dict):
                volumes = [data]

            for vol in volumes:
                target = vol.get("target", "")
                if target in ("", "speaker", "output", "extOutput:zone?zone=1"):
                    return _parse_sony_volume(vol)

            if volumes:
                return _parse_sony_volume(volumes[0])

        return None

    async def get_system(self) -> SonySystem | None:
        """Fetch and parse system information."""
        data = await self.system_information()
        if not data:
            return None
        return SonySystem(
            firmware=data.get("version"),
            mac=data.get("macAddr"),
            bluetooth_mac=data.get("bdAddr"),
            raw=data,
        )

    async def get_av_sources(self) -> list[dict[str, Any]]:
        """Fetch the full discovered source list from avContent."""
        data = await self.try_call(
            SERVICE_AV_CONTENT,
            GET_SOURCE_LIST,
            [{"scheme": "extInput"}],
            version="1.2",
        )
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    # -- Existing helpers (kept for backward compat) --------------------------

    async def supported_api_info(self) -> dict[str, Any]:
        """Return supported service/method information."""
        for params in ([{}], [], [{"services": []}]):
            data = await self.try_call(SERVICE_GUIDE, GET_SUPPORTED_API_INFO, params)
            if data is None:
                continue
            if isinstance(data, dict):
                return data
            return {"services": data or []}
        _LOGGER.debug(
            "guide/getSupportedApiInfo unavailable; continuing with probe-based discovery"
        )
        return {"services": []}

    async def system_information(self) -> dict[str, Any]:
        """Return system information where supported."""
        for version in ("1.4", "1.3", "1.0"):
            data = await self.try_call(
                SERVICE_SYSTEM, GET_SYSTEM_INFORMATION, [], version=version
            )
            if isinstance(data, dict):
                return data
        return {}

    async def power_status(self) -> dict[str, Any]:
        for version in ("1.1", "1.0"):
            data = await self.try_call(
                SERVICE_SYSTEM, GET_POWER_STATUS, [], version=version
            )
            if isinstance(data, dict):
                return data
        return {}

    async def set_power(self, active: bool) -> None:
        await self.call(
            SERVICE_SYSTEM,
            SET_POWER_STATUS,
            [{"status": "active" if active else "standby"}],
            version="1.1",
        )

    async def volume_information(self) -> list[dict[str, Any]]:
        """Return raw volume information list (kept for compat / diagnostics)."""
        for params, version in (
            ([{}], "1.1"),
            ([{"target": "speaker"}], "1.1"),
            ([], "1.1"),
            ([{}], "1.0"),
        ):
            data = await self.try_call(
                SERVICE_AUDIO, GET_VOLUME_INFORMATION, params, version=version
            )
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                return [data]
        return []

    async def set_volume(self, volume: int, *, target: str = "speaker") -> None:
        await self.call(
            SERVICE_AUDIO,
            SET_AUDIO_VOLUME,
            [{"target": target, "volume": str(volume), "ui": "on"}],
            version="1.1",
        )

    async def set_mute(self, mute: bool) -> None:
        await self.call(
            SERVICE_AUDIO,
            SET_AUDIO_MUTE,
            [{"mute": "on" if mute else "off"}],
            version="1.1",
        )

    async def get_sound_setting(self, target: str) -> Any:
        return await self.call(
            SERVICE_AUDIO, GET_SOUND_SETTINGS, [{"target": target}], version="1.1"
        )

    async def set_sound_setting(self, target: str, value: str) -> None:
        await self.call(
            SERVICE_AUDIO,
            SET_SOUND_SETTINGS,
            [{"settings": [{"target": target, "value": value}]}],
            version="1.1",
        )

    async def get_speaker_setting(self, target: str) -> Any:
        return await self.call(SERVICE_AUDIO, GET_SPEAKER_SETTINGS, [{"target": target}])

    async def set_speaker_setting(self, target: str, value: str) -> None:
        await self.call(
            SERVICE_AUDIO,
            SET_SPEAKER_SETTINGS,
            [{"settings": [{"target": target, "value": value}]}],
        )

    async def source_list(self) -> list[dict[str, Any]]:
        data = await self.try_call(
            SERVICE_AV_CONTENT, GET_CURRENT_EXTERNAL_TERMINALS_STATUS
        )
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    async def playing_content_info(self) -> dict[str, Any]:
        data = await self.try_call(SERVICE_AV_CONTENT, GET_PLAYING_CONTENT_INFO)
        return data if isinstance(data, dict) else {}

    async def set_play_content(self, uri: str) -> None:
        await self.call(
            SERVICE_AV_CONTENT,
            SET_PLAY_CONTENT,
            [{"uri": uri}],
            version="1.2",
        )

    async def dump_device_info(
        self, discovered_targets: list[str] | None = None
    ) -> dict[str, Any]:
        """Best-effort device dump for diagnostics and issue reports."""
        dump: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "supported_api_info": await self.supported_api_info(),
            "system_information": await self.system_information(),
            "power_status": await self.power_status(),
            "volume_information": await self.volume_information(),
            "speaker_settings_all": await self.try_call(
                SERVICE_AUDIO, GET_SPEAKER_SETTINGS, [{}]
            ),
            "sound_settings_all": await self.try_call(
                SERVICE_AUDIO, GET_SOUND_SETTINGS, [{}], version="1.1"
            ),
            "custom_equalizer_settings": await self.try_call(
                SERVICE_AUDIO, GET_CUSTOM_EQUALIZER_SETTINGS, [{}]
            ),
            "source_list": await self.try_call(
                SERVICE_AV_CONTENT,
                GET_SOURCE_LIST,
                [{"scheme": "extInput"}],
                version="1.2",
            ),
            "current_external_terminals_status": await self.try_call(
                SERVICE_AV_CONTENT, GET_CURRENT_EXTERNAL_TERMINALS_STATUS
            ),
            "playing_content_info": await self.try_call(
                SERVICE_AV_CONTENT, GET_PLAYING_CONTENT_INFO, [], version="1.2"
            ),
            "available_playback_function": await self.try_call(
                SERVICE_AV_CONTENT, GET_AVAILABLE_PLAYBACK_FUNCTION
            ),
            "power_settings": await self.try_call(
                SERVICE_SYSTEM, GET_POWER_SETTINGS, [{}]
            ),
            "sleep_timer_settings": await self.try_call(
                SERVICE_SYSTEM, GET_SLEEP_TIMER_SETTINGS, [{}]
            ),
            "device_misc_settings": await self.try_call(
                SERVICE_SYSTEM, GET_DEVICE_MISC_SETTINGS, [{}]
            ),
            "interface_information": await self.try_call(
                SERVICE_SYSTEM, GET_INTERFACE_INFORMATION
            ),
            "software_update_info": await self.try_call(
                SERVICE_SYSTEM, GET_SW_UPDATE_INFO
            ),
        }
        settings: dict[str, Any] = {}
        for target in discovered_targets or []:
            settings[target] = {
                "sound": await self.try_call(
                    SERVICE_AUDIO, GET_SOUND_SETTINGS, [{"target": target}], version="1.1"
                ),
                "speaker": await self.try_call(
                    SERVICE_AUDIO, GET_SPEAKER_SETTINGS, [{"target": target}]
                ),
            }
        dump["target_probe_results"] = settings
        return dump
