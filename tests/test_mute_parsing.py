"""Tests for mute parsing and writing behavior."""
from __future__ import annotations

from custom_components.sony_audio_control.sony.client import (
    _parse_sony_volume,
)


def test_parse_mute_on_string() -> None:
    data = {"target": "", "volume": 20, "mute": "on", "minVolume": 0, "maxVolume": 70, "step": 1}
    vol = _parse_sony_volume(data)
    assert vol.muted is True


def test_parse_mute_off_string() -> None:
    data = {"target": "", "volume": 20, "mute": "off", "minVolume": 0, "maxVolume": 70, "step": 1}
    vol = _parse_sony_volume(data)
    assert vol.muted is False


def test_parse_mute_bool_true() -> None:
    data = {"target": "", "volume": 20, "mute": True, "minVolume": 0, "maxVolume": 70, "step": 1}
    vol = _parse_sony_volume(data)
    assert vol.muted is True


def test_parse_mute_bool_false() -> None:
    data = {"target": "", "volume": 20, "mute": False, "minVolume": 0, "maxVolume": 70, "step": 1}
    vol = _parse_sony_volume(data)
    assert vol.muted is False


def test_parse_mute_missing_defaults_false() -> None:
    data = {"target": "", "volume": 20, "minVolume": 0, "maxVolume": 70, "step": 1}
    vol = _parse_sony_volume(data)
    assert vol.muted is False


def test_parse_mute_case_insensitive_on() -> None:
    data = {"target": "", "volume": 20, "mute": "ON", "minVolume": 0, "maxVolume": 70, "step": 1}
    vol = _parse_sony_volume(data)
    assert vol.muted is True
