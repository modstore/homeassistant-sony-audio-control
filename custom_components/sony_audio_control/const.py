from __future__ import annotations

from datetime import timedelta

DOMAIN = "sony_audio_control"
CONF_PORT = "port"
DEFAULT_PORT = 10000
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 10

PLATFORMS = ["media_player", "number", "select", "sensor", "switch"]

ATTR_SERVICE = "service"
ATTR_METHOD = "method"
ATTR_PARAMS = "params"
ATTR_VERSION = "version"
ATTR_ENTRY_ID = "entry_id"

SERVICE_CALL_METHOD = "call_method"
