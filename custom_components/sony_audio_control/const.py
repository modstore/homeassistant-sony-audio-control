"""Constants for Sony Audio Control."""
from __future__ import annotations

DOMAIN = "sony_audio_control"
PLATFORMS = ["media_player", "number", "select", "sensor", "switch", "button"]

CONF_HOST = "host"
CONF_PORT = "port"
DEFAULT_PORT = 10000
DEFAULT_SCAN_INTERVAL_SECONDS = 30

ATTR_ENDPOINT = "endpoint"
ATTR_METHOD = "method"
ATTR_PARAMS = "params"

SERVICE_DUMP_DEVICE_INFO = "dump_device_info"
SERVICE_CALL_API = "call_api"
