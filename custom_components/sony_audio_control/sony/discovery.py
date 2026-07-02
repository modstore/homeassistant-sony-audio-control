"""Discovery helpers for Sony audio devices."""
from __future__ import annotations

import logging
from typing import Any

from ..const import (
    SUBWOOFER_LEVEL_TARGET,
    SUBWOOFER_MANUAL_PRESET,
    SUBWOOFER_PRESET_KEY,
    SUBWOOFER_PRESETS,
)
from .client import SonyAudioClient
from .constants import (
    GET_CURRENT_EXTERNAL_TERMINALS_STATUS,
    GET_POWER_STATUS,
    GET_SOUND_SETTINGS,
    GET_SPEAKER_SETTINGS,
    GET_VOLUME_INFORMATION,
    SERVICE_AUDIO,
    SERVICE_AV_CONTENT,
    SERVICE_SYSTEM,
    SET_AUDIO_MUTE,
    SET_PLAY_CONTENT,
    SET_SOUND_SETTINGS,
    SET_SPEAKER_SETTINGS,
)
from .models import SettingDescription, SettingType

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
    """Normalize many known Sony setting response shapes and return the first setting."""
    payloads = _extract_settings_payloads(payload)
    return payloads[0] if payloads else None


def _extract_settings_payloads(payload: Any) -> list[dict[str, Any]]:
    """Normalize many known Sony setting response shapes and return all settings.

    Sony devices commonly return settings as result -> [ [ {setting}, ... ] ].
    A target-specific call returns the same nested shape with a single item.
    """
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


def _extract_candidates(
    setting: dict[str, Any],
) -> tuple[list[str], dict[str, str], float | None, float | None, float | None]:
    candidates = setting.get("candidate") or setting.get("candidates") or []
    option_values: list[str] = []
    option_map: dict[str, str] = {}
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None

    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict):
                if candidate.get("isAvailable") is False:
                    continue
                value = candidate.get("value")
                title = candidate.get("title") or value
                if value not in (None, "") and title not in (None, ""):
                    label = str(title).strip()
                    raw_value = str(value)
                    if label not in option_map:
                        option_values.append(label)
                    option_map[label] = raw_value
                if candidate.get("min") is not None and float(candidate["min"]) != -1:
                    min_value = float(candidate["min"])
                if candidate.get("max") is not None and float(candidate["max"]) != -1:
                    max_value = float(candidate["max"])
                if candidate.get("step") is not None and float(candidate["step"]) != -1:
                    step = float(candidate["step"])
            elif candidate not in (None, ""):
                label = str(candidate)
                option_values.append(label)
                option_map[label] = label
    elif isinstance(candidates, dict):
        if candidates.get("min") is not None:
            min_value = float(candidates["min"])
        if candidates.get("max") is not None:
            max_value = float(candidates["max"])
        if candidates.get("step") is not None:
            step = float(candidates["step"])

    return option_values, option_map, min_value, max_value, step


def _classify_setting(
    service: str, method: str, target: str, setting: dict[str, Any]
) -> SettingDescription:
    option_values, option_map, min_value, max_value, step = _extract_candidates(
        setting
    )
    value = setting.get("value", setting.get("currentValue"))
    target_l = target.lower()
    sony_type_str = str(setting.get("type") or "").lower()

    # Map to SettingType enum where possible
    if sony_type_str == SettingType.NUMBER:
        mapped_type = SettingType.NUMBER
    elif sony_type_str == SettingType.ENUM:
        mapped_type = SettingType.ENUM
    elif sony_type_str == SettingType.BOOLEAN:
        mapped_type = SettingType.BOOLEAN
    else:
        mapped_type = SettingType.UNKNOWN

    if (
        "number" in sony_type_str
        or min_value is not None
        or max_value is not None
        or "level" in target_l
    ):
        kind = "number"
    elif "boolean" in sony_type_str:
        kind = "switch"
    elif "enum" in sony_type_str or option_values:
        lower_raw = (
            {v.lower() for v in option_map.values()} or {opt.lower() for opt in option_values}
        )
        kind = (
            "switch"
            if lower_raw <= {"on", "off", "true", "false", "enabled", "disabled"}
            else "select"
        )
    elif isinstance(value, bool) or target_l.endswith("mode") and str(value).lower() in {
        "on",
        "off",
    }:
        kind = "switch"
    else:
        kind = "sensor"

    get_method = method
    set_method = None
    if method == GET_SPEAKER_SETTINGS:
        set_method = SET_SPEAKER_SETTINGS
    elif method == GET_SOUND_SETTINGS:
        set_method = SET_SOUND_SETTINGS

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
        sony_type=mapped_type.value,
        option_values=option_values,
        option_map=option_map,
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
        service_name = (
            service.get("service") or service.get("serviceName") or service.get("name")
        )
        apis = service.get("apis") or service.get("api") or []
        if not service_name or not isinstance(apis, list):
            continue
        for api in apis:
            method = (
                api.get("name") or api.get("method")
                if isinstance(api, dict)
                else str(api)
            )
            if method:
                methods.add((str(service_name), str(method)))
    return methods


async def discover_settings(
    client: SonyAudioClient,
) -> tuple[dict[str, Any], list[SettingDescription]]:
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

    if not methods or (SERVICE_AUDIO, GET_SPEAKER_SETTINGS) in methods:
        payload = await client.try_call(SERVICE_AUDIO, GET_SPEAKER_SETTINGS, [{}])
        settings = _extract_settings_payloads(payload)
        if settings:
            for setting in settings:
                if not setting.get("isAvailable", True):
                    continue
                target = setting.get("target")
                if not target:
                    continue
                desc = _classify_setting(
                    SERVICE_AUDIO, GET_SPEAKER_SETTINGS, str(target), setting
                )
                descriptions[desc.key] = desc
        else:
            for target in SPEAKER_TARGET_PROBES:
                await probe(SERVICE_AUDIO, GET_SPEAKER_SETTINGS, target)

    if any(
        desc.target == SUBWOOFER_LEVEL_TARGET and desc.kind == "number"
        for desc in descriptions.values()
    ):
        descriptions[SUBWOOFER_PRESET_KEY] = SettingDescription(
            key=SUBWOOFER_PRESET_KEY,
            name="Subwoofer Preset",
            kind="select",
            service=SERVICE_AUDIO,
            get_method=GET_SPEAKER_SETTINGS,
            set_method=SET_SPEAKER_SETTINGS,
            target=SUBWOOFER_LEVEL_TARGET,
            option_values=list(SUBWOOFER_PRESETS) + [SUBWOOFER_MANUAL_PRESET],
            option_map={
                label: str(value) for label, value in SUBWOOFER_PRESETS.items()
            },
            icon="mdi:speaker",
            raw={"preset_for": SUBWOOFER_LEVEL_TARGET},
        )

    if not methods or (SERVICE_AUDIO, GET_SOUND_SETTINGS) in methods:
        payload = await client.try_call(
            SERVICE_AUDIO, GET_SOUND_SETTINGS, [{}], version="1.1"
        )
        settings = _extract_settings_payloads(payload)
        if settings:
            for setting in settings:
                if not setting.get("isAvailable", True):
                    continue
                target = setting.get("target")
                if not target:
                    continue
                desc = _classify_setting(
                    SERVICE_AUDIO, GET_SOUND_SETTINGS, str(target), setting
                )
                descriptions[desc.key] = desc
        else:
            for target in SOUND_TARGET_PROBES + SENSOR_TARGET_PROBES:
                await probe(SERVICE_AUDIO, GET_SOUND_SETTINGS, target)

    # Core entities that are handled explicitly by platforms.
    if (
        not methods
        or (SERVICE_SYSTEM, GET_POWER_STATUS) in methods
        or (SERVICE_AUDIO, GET_VOLUME_INFORMATION) in methods
    ):
        descriptions["media_player_main"] = SettingDescription(
            key="media_player_main",
            name="Receiver",
            kind="sensor",
            service="core",
            raw={},
        )
    if not methods or (SERVICE_AUDIO, GET_VOLUME_INFORMATION) in methods:
        descriptions["audio_mute"] = SettingDescription(
            key="audio_mute",
            name="Mute",
            kind="switch",
            service=SERVICE_AUDIO,
            target="speaker",
            get_method=GET_VOLUME_INFORMATION,
            set_method=SET_AUDIO_MUTE,
            icon="mdi:volume-mute",
        )
    if (
        not methods
        or (SERVICE_AV_CONTENT, GET_CURRENT_EXTERNAL_TERMINALS_STATUS) in methods
    ):
        descriptions["input_source"] = SettingDescription(
            key="input_source",
            name="Input Source",
            kind="select",
            service=SERVICE_AV_CONTENT,
            get_method=GET_CURRENT_EXTERNAL_TERMINALS_STATUS,
            set_method=SET_PLAY_CONTENT,
            target="inputSource",
        )

    _LOGGER.debug("Discovered Sony settings: %s", descriptions)
    return supported, list(descriptions.values())
