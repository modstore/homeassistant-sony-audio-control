"""Diagnostics helpers for Sony Audio Control."""
from __future__ import annotations

from typing import Any

REDACTED = "REDACTED"
TO_REDACT = {
    "host",
    "ip",
    "ipAddress",
    "macAddr",
    "mac",
    "wirelessMacAddr",
    "wiredMacAddr",
    "bdAddr",
    "bluetooth_mac",
    "ssid",
    "bssid",
    "serialNumber",
    "serial",
}


def redact(value: Any) -> Any:
    """Return a share-safe copy of a diagnostic payload."""
    if isinstance(value, dict):
        return {
            key: (REDACTED if key in TO_REDACT else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
