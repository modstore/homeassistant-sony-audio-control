"""Discovery helpers for Sony audio devices."""
from __future__ import annotations

import logging
from typing import Any

from .client import SonyAudioClient
from .models import SettingDescription

_LOGGER = logging.getLogger(__name__)

# These are probes, not a compatibility whitelist. The integration only exposes
# targets that respond successfully or appear in device-provided candidate data.
SPEAKER_TARGET_PROBES = [
    "subwooferLevel",
    "centerLevel",
    "frontLeftLevel",
    "frontRightLevel",
    "surroundLeftLevel",
    "surroundRightLevel",
    "surroundBackLeftLevel",
    "surroundBackRightLevel",
    "heightLeftLevel",
    "heightRightLevel",
    "frontHighLeftLevel",
    "frontHighRightLevel",
]

SOUND_TARGET_PROBES = [
    "soundField",
    "clearAudio",
    "nightMode",
    "pureDirect",
    "autoVolume",
    "dseeHx",
    "subwooferPower",
]

SENSOR_TARGET_PROBES = [
    "currentCodec",
    "currentSoundField",
    "inputSignal",
    "outputSignal",
]


def _humanize(value: str) -> str:
    out = ""
    for idx, char in enumerate(value):
        if idx and char.isupper() and value[idx - 1].islower():
            out += " "
        out += char
    return out.replace("_", " ").replace("-", " ").title()


def _extract_settings_payload(payload: Any) -> dict[str, Any] | None:
    """Normalize many known Sony setting response shapes."""
    if isinstance(payload, dict):
        if "settings" in payload and isinstance(payload["settings"], list) and payload["settings"]:
            first = payload["settings"][0]
            return first if isinstance(first, dict) else None
        if "target" in payload or "value" in payload or "candidate" in payload:
            return payload
    if isinstance(payload, list) and payload:
        for item in payload:
            normal = _extract_settings_payload(item)
            if normal:
                return normal
    return None


def _extract_candidates(setting: dict[str, Any]) -> tuple[list[str], float | None, float | None, float | None]:
    candidates = setting.get("candidate") or setting.get("candidates") or []
    option_values: list[str] = []
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None

    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict):
                value = candidate.get("value") or candidate.get("title")
                if value is not None:
                    option_values.append(str(value))
                if candidate.get("min") is not None:
                    min_value = float(candidate["min"])
                if candidate.get("max") is not None:
                    max_value = float(candidate["max"])
                if candidate.get("step") is not None:
                    step = float(candidate["step"])
            elif candidate is not None:
                option_values.append(str(candidate))
    elif isinstance(candidates, dict):
        if candidates.get("min") is not None:
            min_value = float(candidates["min"])
        if candidates.get("max") is not None:
            max_value = float(candidates["max"])
        if candidates.get("step") is not None:
            step = float(candidates["step"])

    return option_values, min_value, max_value, step


def _classify_setting(service: str, method: str, target: str, setting: dict[str, Any]) -> SettingDescription:
    option_values, min_value, max_value, step = _extract_candidates(setting)
    value = setting.get("value")
    target_l = target.lower()

    if option_values:
        lower_options = {opt.lower() for opt in option_values}
        if lower_options <= {"on", "off", "true", "false", "enabled", "disabled"}:
            kind = "switch"
        else:
            kind = "select"
    elif min_value is not None or max_value is not None or "level" in target_l or "volume" in target_l:
        kind = "number"
    elif isinstance(value, bool) or target_l.endswith("mode") and str(value).lower() in {"on", "off"}:
        kind = "switch"
    else:
        kind = "sensor"

    get_method = method
    set_method = None
    if method == "getSpeakerSettings":
        set_method = "setSpeakerSettings"
    elif method == "getSoundSettings":
        set_method = "setSoundSettings"

    if kind == "number":
        min_value = min_value if min_value is not None else -10
        max_value = max_value if max_value is not None else 10
        step = step if step is not None else 0.5

    return SettingDescription(
        key=f"{service}_{target}",
        name=_humanize(target),
        kind=kind,
        service=service,
        get_method=get_method,
        set_method=set_method,
        target=target,
        option_values=option_values,
        min_value=min_value,
        max_value=max_value,
        step=step,
        unit="dB" if "level" in target_l else None,
        raw=setting,
    )


def _api_methods(supported: dict[str, Any]) -> set[tuple[str, str]]:
    methods: set[tuple[str, str]] = set()
    services = supported.get("services") if isinstance(supported, dict) else None
    if not isinstance(services, list):
        return methods
    for service in services:
        if not isinstance(service, dict):
            continue
        service_name = service.get("service") or service.get("serviceName") or service.get("name")
        apis = service.get("apis") or service.get("api") or []
        if not service_name or not isinstance(apis, list):
            continue
        for api in apis:
            if isinstance(api, dict):
                method = api.get("name") or api.get("method")
            else:
                method = str(api)
            if method:
                methods.add((str(service_name), str(method)))
    return methods


async def discover_settings(client: SonyAudioClient) -> tuple[dict[str, Any], list[SettingDescription]]:
    """Discover the Sony API surface and expose supported settings as entities."""
    supported = await client.supported_api_info()
    methods = _api_methods(supported)
    descriptions: dict[str, SettingDescription] = {}

    async def probe(service: str, method: str, target: str) -> None:
        if methods and (service, method) not in methods:
            # Some devices report guide info incompletely, so only skip when we are quite sure.
            pass
        payload = await client.try_call(service, method, [{"target": target}])
        setting = _extract_settings_payload(payload)
        if not setting:
            return
        discovered_target = str(setting.get("target") or target)
        desc = _classify_setting(service, method, discovered_target, setting)
        descriptions[desc.key] = desc

    if not methods or ("audio", "getSpeakerSettings") in methods:
        for target in SPEAKER_TARGET_PROBES:
            await probe("audio", "getSpeakerSettings", target)

    if not methods or ("audio", "getSoundSettings") in methods:
        for target in SOUND_TARGET_PROBES + SENSOR_TARGET_PROBES:
            await probe("audio", "getSoundSettings", target)

    # Core entities that are handled explicitly by platforms.
    if not methods or ("system", "getPowerStatus") in methods or ("audio", "getVolumeInformation") in methods:
        descriptions["media_player_main"] = SettingDescription(
            key="media_player_main",
            name="Receiver",
            kind="sensor",
            service="core",
            raw={},
        )
    if not methods or ("audio", "getVolumeInformation") in methods:
        descriptions["audio_mute"] = SettingDescription(
            key="audio_mute",
            name="Mute",
            kind="switch",
            service="audio",
            target="speaker",
            get_method="getVolumeInformation",
            set_method="setAudioMute",
            icon="mdi:volume-mute",
        )
    if not methods or ("avContent", "getCurrentExternalTerminalsStatus") in methods:
        descriptions["input_source"] = SettingDescription(
            key="input_source",
            name="Input Source",
            kind="select",
            service="avContent",
            get_method="getCurrentExternalTerminalsStatus",
            set_method="setPlayContent",
            target="inputSource",
        )

    _LOGGER.debug("Discovered Sony settings: %s", descriptions)
    return supported, list(descriptions.values())
