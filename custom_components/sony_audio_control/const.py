"""Constants for Sony Audio Control."""

DOMAIN = "sony_audio_control"
DEFAULT_PORT = 10000
DEFAULT_SCAN_INTERVAL_SECONDS = 30

CONF_PORT = "port"

PLATFORMS = ["media_player", "number", "select", "sensor", "switch"]

SERVICE_AUDIO = "audio"
SERVICE_SYSTEM = "system"
SERVICE_AV_CONTENT = "avContent"
SERVICE_GUIDE = "guide"

DEFAULT_SPEAKER_LEVEL_TARGETS = {
    "subwooferLevel": "Subwoofer Level",
    "frontLeftLevel": "Front Left Level",
    "frontRightLevel": "Front Right Level",
    "centerLevel": "Centre Level",
    "surroundLeftLevel": "Surround Left Level",
    "surroundRightLevel": "Surround Right Level",
    "surroundBackLeftLevel": "Surround Back Left Level",
    "surroundBackRightLevel": "Surround Back Right Level",
    "heightLeftLevel": "Height Left Level",
    "heightRightLevel": "Height Right Level",
}

DEFAULT_SELECT_TARGETS = {
    "soundField": "Sound Field",
    "speakerPattern": "Speaker Pattern",
}
