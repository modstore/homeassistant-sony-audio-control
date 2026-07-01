"""Tests for Sony Audio Control discovery helpers.

These tests use trimmed versions of real STR-DN1080 responses captured during
initial development so discovery can be refactored safely without needing a
receiver on the network.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from custom_components.sony_audio_control.sony.discovery import (
    _api_methods,
    _classify_setting,
    _extract_settings_payloads,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_api_methods_are_extracted_from_supported_api_info() -> None:
    supported = {"services": load_fixture("get_supported_api_info.json")}

    methods = _api_methods(supported)

    assert ("audio", "getSpeakerSettings") in methods
    assert ("audio", "getSoundSettings") in methods
    assert ("audio", "getVolumeInformation") in methods
    assert ("system", "getSystemInformation") in methods
    assert ("avContent", "setPlayContent") in methods


def test_speaker_settings_create_numbers_and_selects() -> None:
    payload = load_fixture("get_speaker_settings.json")
    settings = [s for s in _extract_settings_payloads(payload) if s.get("isAvailable", True)]

    descriptions = {
        setting["target"]: _classify_setting("audio", "getSpeakerSettings", setting["target"], setting)
        for setting in settings
    }

    assert descriptions["frontLLevel"].kind == "number"
    assert descriptions["frontLLevel"].min_value == -10
    assert descriptions["frontLLevel"].max_value == 10
    assert descriptions["frontLLevel"].step == 0.5
    assert descriptions["frontLLevel"].unit == "dB"

    assert descriptions["subwooferLevel"].kind == "number"
    assert descriptions["centerLevel"].kind == "number"

    assert descriptions["speakerSelection"].kind == "select"
    assert descriptions["speakerSelection"].option_map == {
        "Speaker A": "speakerA",
        "Off": "off",
    }
    assert "heightLLevel" not in descriptions


def test_sound_settings_create_selects_and_switches() -> None:
    payload = load_fixture("get_sound_settings.json")
    settings = [s for s in _extract_settings_payloads(payload) if s.get("isAvailable", True)]

    descriptions = {
        setting["target"]: _classify_setting("audio", "getSoundSettings", setting["target"], setting)
        for setting in settings
    }

    assert descriptions["soundField"].kind == "select"
    assert descriptions["soundField"].option_map["2ch Stereo"] == "2chStereo"
    assert descriptions["soundField"].option_map["Multi Ch Stereo"] == "multiChStereo"
    assert "" not in descriptions["soundField"].option_values

    assert descriptions["pureDirect"].kind == "switch"
    assert descriptions["optimizer"].kind == "select"
    assert descriptions["optimizer"].option_values == ["Off", "Normal", "Low"]
