from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .api import SonyAudioApi

EntityKind = Literal["number", "select", "switch", "sensor"]


@dataclass(frozen=True)
class DynamicSettingDescription:
    key: str
    name: str
    getter: str
    setter: str | None
    target: str
    kind: EntityKind
    icon: str | None = None
    native_min_value: float | None = None
    native_max_value: float | None = None
    native_step: float | None = None
    options: tuple[str, ...] = ()


# These are discovery candidates, not fixed entities. Each one is probed and only
# created if the receiver reports a valid value or options for that target.
SPEAKER_LEVEL_TARGETS = (
    "subwooferLevel",
    "centerLevel",
    "frontLeftLevel",
    "frontRightLevel",
    "surroundLeftLevel",
    "surroundRightLevel",
    "surroundBackLeftLevel",
    "surroundBackRightLevel",
    "frontHighLeftLevel",
    "frontHighRightLevel",
    "heightLeftLevel",
    "heightRightLevel",
    "zone2Volume",
    "zone3Volume",
)

SPEAKER_DISTANCE_TARGETS = (
    "frontLeftDistance",
    "frontRightDistance",
    "centerDistance",
    "surroundLeftDistance",
    "surroundRightDistance",
    "surroundBackLeftDistance",
    "surroundBackRightDistance",
    "subwooferDistance",
    "frontHighLeftDistance",
    "frontHighRightDistance",
)

SOUND_SETTING_TARGETS = (
    "soundField",
    "soundFieldMode",
    "pureDirect",
    "nightMode",
    "voiceUp",
    "verticalSurround",
    "clearAudio",
    "dseeHx",
    "autoVolume",
    "dualMono",
    "dynamicRangeCompressor",
    "hdDcs",
    "aFDSurround",
    "neuralX",
    "dolbySpeakerVirtualizer",
)

PLAYBACK_SETTING_TARGETS = (
    "repeatType",
    "shuffleType",
)

EQ_TARGETS = (
    "bass",
    "treble",
    "frontBass",
    "frontTreble",
    "centerBass",
    "centerTreble",
    "surroundBass",
    "surroundTreble",
)

BOOLEAN_TRUE = {"on", "true", "yes", "enabled", "enable", "active", "1"}
BOOLEAN_FALSE = {"off", "false", "no", "disabled", "disable", "inactive", "0"}


async def discover_dynamic_settings(api: SonyAudioApi) -> list[DynamicSettingDescription]:
    """Probe common Sony audio targets and return supported HA entity descriptions."""
    descriptions: list[DynamicSettingDescription] = []

    for target in SPEAKER_LEVEL_TARGETS:
        setting = await api.get_setting("getSpeakerSettings", target)
        desc = _describe_setting("getSpeakerSettings", "setSpeakerSettings", target, setting, "mdi:speaker")
        if desc:
            descriptions.append(desc)

    for target in SPEAKER_DISTANCE_TARGETS:
        setting = await api.get_setting("getSpeakerSettings", target)
        desc = _describe_setting("getSpeakerSettings", "setSpeakerSettings", target, setting, "mdi:tape-measure")
        if desc:
            descriptions.append(desc)

    for target in EQ_TARGETS:
        setting = await api.get_setting("getSoundSettings", target)
        desc = _describe_setting("getSoundSettings", "setSoundSettings", target, setting, "mdi:tune-vertical")
        if desc:
            descriptions.append(desc)

    for target in SOUND_SETTING_TARGETS:
        setting = await api.get_setting("getSoundSettings", target)
        desc = _describe_setting("getSoundSettings", "setSoundSettings", target, setting, "mdi:surround-sound")
        if desc:
            descriptions.append(desc)

    for target in PLAYBACK_SETTING_TARGETS:
        setting = await api.get_setting("getPlaybackModeSettings", target)
        desc = _describe_setting("getPlaybackModeSettings", "setPlaybackModeSettings", target, setting, "mdi:play-circle")
        if desc:
            descriptions.append(desc)

    # Stable ordering and de-duplication.
    unique: dict[str, DynamicSettingDescription] = {desc.key: desc for desc in descriptions}
    return list(unique.values())


def _describe_setting(
    getter: str,
    setter: str,
    target: str,
    setting: dict[str, Any] | None,
    icon: str | None,
) -> DynamicSettingDescription | None:
    if not setting:
        return None

    value = setting.get("currentValue", setting.get("value"))
    candidate_options = _extract_options(setting)

    if candidate_options:
        lower_options = {str(opt).lower() for opt in candidate_options}
        if lower_options <= (BOOLEAN_TRUE | BOOLEAN_FALSE):
            kind: EntityKind = "switch"
        else:
            kind = "select"
        return DynamicSettingDescription(
            key=f"{getter}_{target}",
            name=_friendly_name(target),
            getter=getter,
            setter=setter,
            target=target,
            kind=kind,
            icon=icon,
            options=tuple(str(opt) for opt in candidate_options),
        )

    numeric_value = _to_float(value)
    if numeric_value is not None:
        min_v = _first_number(setting, ("min", "minimum", "minValue"), -10)
        max_v = _first_number(setting, ("max", "maximum", "maxValue"), 10)
        step = _first_number(setting, ("step", "stepValue", "interval"), 1)
        return DynamicSettingDescription(
            key=f"{getter}_{target}",
            name=_friendly_name(target),
            getter=getter,
            setter=setter,
            target=target,
            kind="number",
            icon=icon,
            native_min_value=min_v,
            native_max_value=max_v,
            native_step=step,
        )

    if value is not None:
        return DynamicSettingDescription(
            key=f"{getter}_{target}",
            name=_friendly_name(target),
            getter=getter,
            setter=None,
            target=target,
            kind="sensor",
            icon=icon,
        )
    return None


def _extract_options(setting: dict[str, Any]) -> list[str]:
    for key in ("candidate", "options", "available", "supportedValue"):
        raw = setting.get(key)
        if isinstance(raw, list):
            values: list[str] = []
            for item in raw:
                if isinstance(item, dict):
                    val = item.get("value") or item.get("name") or item.get("title")
                    if val is not None:
                        values.append(str(val))
                elif item is not None:
                    values.append(str(item))
            if values:
                return values
    return []


def _first_number(setting: dict[str, Any], keys: tuple[str, ...], default: float) -> float:
    for key in keys:
        number = _to_float(setting.get(key))
        if number is not None:
            return number
    return float(default)


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _friendly_name(target: str) -> str:
    chars: list[str] = []
    for char in target:
        if char.isupper() and chars:
            chars.append(" ")
        chars.append(char)
    text = "".join(chars).replace("_", " ").strip()
    return text[:1].upper() + text[1:]
