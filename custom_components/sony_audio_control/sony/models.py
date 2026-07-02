"""Pure Python data models for Sony audio device state."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from .constants import (
    TYPE_BOOLEAN_TARGET,
    TYPE_DOUBLE_NUMBER_TARGET,
    TYPE_ENUM_TARGET,
)

EntityKind = Literal["number", "select", "sensor", "switch", "button"]


class SettingType(StrEnum):
    """Sony setting type identifiers."""

    NUMBER = TYPE_DOUBLE_NUMBER_TARGET
    ENUM = TYPE_ENUM_TARGET
    BOOLEAN = TYPE_BOOLEAN_TARGET
    UNKNOWN = "unknown"


@dataclass
class SonySetting:
    """A single setting discovered from a Sony audio device."""

    target: str
    title: str
    type: SettingType | str
    current_value: Any
    available: bool
    candidates: list[Any] = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SonyVolume:
    """Volume state for a Sony audio output zone."""

    volume: int
    muted: bool
    max_volume: int
    min_volume: int
    step: int


@dataclass
class SonySystem:
    """System information for a Sony audio device."""

    firmware: str | None = None
    mac: str | None = None
    bluetooth_mac: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class SonyState:
    """Complete cached state of a Sony audio device."""

    speaker_settings: dict[str, SonySetting] = field(default_factory=dict)
    sound_settings: dict[str, SonySetting] = field(default_factory=dict)
    volume: SonyVolume | None = None
    system: SonySystem | None = None
    power: str | None = None
    input_uri: str | None = None
    input_title: str | None = None
    model_name: str | None = None
    device_name: str | None = None
    last_update: datetime | None = None


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
    sony_type: str = ""
    option_values: list[str] = field(default_factory=list)
    option_map: dict[str, str] = field(default_factory=dict)
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    unit: str | None = None
    icon: str | None = None
    category: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
