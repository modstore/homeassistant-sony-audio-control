"""Tests for diagnostics redaction helpers."""
from __future__ import annotations

from custom_components.sony_audio_control.sony.diagnostics import REDACTED, redact


def test_diagnostics_redacts_network_identifiers() -> None:
    payload = {
        "host": "192.168.1.14",
        "system_information": {
            "macAddr": "38:18:4c:4e:e1:d5",
            "wirelessMacAddr": "e8:d0:fc:87:62:fb",
            "bdAddr": "e8:d0:fc:87:62:fc",
            "version": "M41.R.0518",
        },
        "settings": [{"target": "soundField", "currentValue": "multiChStereo"}],
    }

    redacted = redact(payload)

    assert redacted["host"] == REDACTED
    assert redacted["system_information"]["macAddr"] == REDACTED
    assert redacted["system_information"]["wirelessMacAddr"] == REDACTED
    assert redacted["system_information"]["bdAddr"] == REDACTED
    assert redacted["system_information"]["version"] == "M41.R.0518"
    assert redacted["settings"][0]["currentValue"] == "multiChStereo"
