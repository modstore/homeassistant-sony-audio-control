"""Tests for Sony client response normalization."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.sony_audio_control.sony.client import SonyAudioClient

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self._data = data

    async def __aenter__(self) -> "FakeResponse":
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
