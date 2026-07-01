"""Small data models used by the integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EntityKind = Literal["number", "select", "sensor", "switch", "button"]


@dataclass(slots=True, frozen=True)
class SettingDescription:
    """A Home Assistant entity candidate discovered from Sony APIs."""

    key: str
    name: str
    kind: EntityKind
    service: str
    get_method: str | None = None
    set_method: str | None = None
    target: str | None = None
    option_values: list[str] = field(default_factory=list)
    option_map: dict[str, str] = field(default_factory=dict)
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    unit: str | None = None
    icon: str | None = None
    category: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DeviceSnapshot:
    """Latest device data."""

    available: bool = False
    model_name: str | None = None
    device_name: str | None = None
    power: str | None = None
    mute: bool | None = None
    volume: int | None = None
    min_volume: int | None = None
    max_volume: int | None = None
    input_uri: str | None = None
    input_title: str | None = None
    sound_settings: dict[str, Any] = field(default_factory=dict)
    speaker_settings: dict[str, Any] = field(default_factory=dict)
    system_info: dict[str, Any] = field(default_factory=dict)
    playing_info: dict[str, Any] = field(default_factory=dict)
