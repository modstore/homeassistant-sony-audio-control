"""Tests for Sony data model parsing and behavior."""
from __future__ import annotations

from custom_components.sony_audio_control.sony.models import (
    SettingType,
    SonySetting,
    SonyState,
    SonySystem,
    SonyVolume,
)


def test_setting_type_enum_values() -> None:
    assert SettingType.NUMBER == "doubleNumberTarget"
    assert SettingType.ENUM == "enumTarget"
    assert SettingType.BOOLEAN == "booleanTarget"
    assert SettingType.UNKNOWN == "unknown"


def test_sony_setting_defaults() -> None:
    s = SonySetting(
        target="subwooferLevel",
        title="Subwoofer",
        type=SettingType.NUMBER,
        current_value="0.0",
        available=True,
    )
    assert s.target == "subwooferLevel"
    assert s.title == "Subwoofer"
    assert s.type == SettingType.NUMBER
    assert s.current_value == "0.0"
    assert s.available is True
    assert s.candidates == []
    assert s.minimum is None
    assert s.maximum is None
    assert s.step is None


def test_sony_setting_with_candidates() -> None:
    s = SonySetting(
        target="soundField",
        title="Sound Field",
        type=SettingType.ENUM,
        current_value="multiChStereo",
        available=True,
        candidates=[
            {"title": "2ch Stereo", "value": "2chStereo"},
            {"title": "Multi Ch Stereo", "value": "multiChStereo"},
        ],
    )
    assert len(s.candidates) == 2
    assert s.raw == {}


def test_sony_volume_defaults() -> None:
    v = SonyVolume(volume=35, muted=False, max_volume=70, min_volume=0, step=1)
    assert v.volume == 35
    assert v.muted is False
    assert v.max_volume == 70
    assert v.min_volume == 0
    assert v.step == 1


def test_sony_system_parsing() -> None:
    sys = SonySystem(
        firmware="M41.R.0518",
        mac="38:18:4c:4e:e1:d5",
        bluetooth_mac="e8:d0:fc:87:62:fc",
        raw={"modelName": "STR-DN1080"},
    )
    assert sys.firmware == "M41.R.0518"
    assert sys.mac == "38:18:4c:4e:e1:d5"
    assert sys.bluetooth_mac == "e8:d0:fc:87:62:fc"
    assert sys.raw["modelName"] == "STR-DN1080"


def test_sony_state_assembly() -> None:
    speaker = SonySetting(
        target="subwooferLevel",
        title="Subwoofer",
        type=SettingType.NUMBER,
        current_value="0.0",
        available=True,
    )
    sound = SonySetting(
        target="soundField",
        title="Sound Field",
        type=SettingType.ENUM,
        current_value="multiChStereo",
        available=True,
    )
    vol = SonyVolume(volume=35, muted=False, max_volume=70, min_volume=0, step=1)
    sys = SonySystem(firmware="M41.R.0518", mac="38:18:4c:4e:e1:d5", raw={})

    state = SonyState(
        speaker_settings={"subwooferLevel": speaker},
        sound_settings={"soundField": sound},
        volume=vol,
        system=sys,
        power="active",
        input_title="HDMI1",
        model_name="STR-DN1080",
    )

    assert state.speaker_settings["subwooferLevel"].current_value == "0.0"
    assert state.sound_settings["soundField"].current_value == "multiChStereo"
    assert state.volume.volume == 35
    assert state.volume.muted is False
    assert state.system.mac == "38:18:4c:4e:e1:d5"
    assert state.power == "active"
    assert state.input_title == "HDMI1"
    assert state.model_name == "STR-DN1080"
