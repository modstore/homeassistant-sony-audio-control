"""Tests for Sony client typed parsing methods."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.sony_audio_control.sony.client import SonyAudioClient
from custom_components.sony_audio_control.sony.models import SettingType

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self._data = data

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self, content_type: str | None = None) -> Any:
        return self._data


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
        self.requests.append((url, json))
        return FakeResponse(self.responses.pop(0))


@pytest.mark.asyncio
async def test_supported_api_info_accepts_empty_object_params_first() -> None:
    service_list = load_fixture("get_supported_api_info.json")
    session = FakeSession([{"id": 1, "result": [service_list]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.supported_api_info()

    assert result["services"] == service_list
    assert session.requests[0][1]["params"] == [{}]
    assert session.requests[0][1]["method"] == "getSupportedApiInfo"


@pytest.mark.asyncio
async def test_system_information_returns_plain_dict() -> None:
    system_info = load_fixture("get_system_information.json")
    session = FakeSession([{"id": 1, "result": [system_info]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.system_information()

    assert result["macAddr"] == "38:18:4c:4e:e1:d5"
    assert result["version"] == "M41.R.0518"


@pytest.mark.asyncio
async def test_get_system_parses_system_information() -> None:
    system_info = load_fixture("system.json")
    session = FakeSession([{"id": 1, "result": [system_info]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_system()

    assert result is not None
    assert result.firmware == "M41.R.0518"
    assert result.mac == "38:18:4c:4e:e1:d5"
    assert result.bluetooth_mac == "e8:d0:fc:87:62:fc"
    assert result.raw["modelName"] == "STR-DN1080"


@pytest.mark.asyncio
async def test_get_volume_parses_volume_information() -> None:
    volume_data = load_fixture("volume.json")
    session = FakeSession([{"id": 1, "result": [volume_data]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_volume()

    assert result is not None
    assert result.volume == 35
    assert result.muted is False
    assert result.max_volume == 70
    assert result.min_volume == 0
    assert result.step == 1


@pytest.mark.asyncio
async def test_get_volume_mute_on_string() -> None:
    session = FakeSession([{"id": 1, "result": [[{"target": "", "volume": 20, "mute": "on", "minVolume": 0, "maxVolume": 70, "step": 1}]]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_volume()

    assert result is not None
    assert result.muted is True


@pytest.mark.asyncio
async def test_get_volume_mute_off_string() -> None:
    session = FakeSession([{"id": 1, "result": [[{"target": "", "volume": 20, "mute": "off", "minVolume": 0, "maxVolume": 70, "step": 1}]]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_volume()

    assert result is not None
    assert result.muted is False


@pytest.mark.asyncio
async def test_get_speaker_settings_parses_all_settings() -> None:
    payload = load_fixture("get_speaker_settings.json")
    session = FakeSession([{"id": 1, "result": payload}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_speaker_settings()

    assert len(result) == 4  # speakerSelection, frontLLevel, centerLevel, subwooferLevel (heightLLevel is unavailable)
    assert "subwooferLevel" in result
    sub = result["subwooferLevel"]
    assert sub.title == "Subwoofer"
    assert sub.type == SettingType.NUMBER
    assert sub.current_value == "0.0"
    assert sub.available is True
    assert sub.minimum == -10.0
    assert sub.maximum == 10.0
    assert sub.step == 0.5

    sel = result["speakerSelection"]
    assert sel.type == SettingType.ENUM
    assert sel.current_value == "speakerA"


@pytest.mark.asyncio
async def test_get_sound_settings_parses_all_settings() -> None:
    payload = load_fixture("get_sound_settings.json")
    session = FakeSession([{"id": 1, "result": payload}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    result = await client.get_sound_settings()

    assert len(result) == 3
    assert "soundField" in result
    sf = result["soundField"]
    assert sf.title == "Sound Field"
    assert sf.type == SettingType.ENUM
    assert sf.current_value == "multiChStereo"

    pd = result["pureDirect"]
    assert pd.type == SettingType.BOOLEAN
    assert pd.current_value == "off"

    opt = result["optimizer"]
    assert opt.type == SettingType.ENUM
    assert opt.current_value == "off"


@pytest.mark.asyncio
async def test_set_mute_writes_on_off() -> None:
    session = FakeSession([{"id": 1, "result": [0]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    await client.set_mute(True)

    req = session.requests[0][1]
    assert req["method"] == "setAudioMute"
    assert req["params"] == [{"mute": "on"}]


@pytest.mark.asyncio
async def test_set_mute_unmute_writes_off() -> None:
    session = FakeSession([{"id": 1, "result": [0]}])
    client = SonyAudioClient(session, "192.168.1.14")  # type: ignore[arg-type]

    await client.set_mute(False)

    req = session.requests[0][1]
    assert req["method"] == "setAudioMute"
    assert req["params"] == [{"mute": "off"}]
