"""Sony ScalarWebAPI constants."""
from __future__ import annotations

# -- Services ---------------------------------------------------------------

SERVICE_AUDIO = "audio"
SERVICE_SYSTEM = "system"
SERVICE_AV_CONTENT = "avContent"
SERVICE_GUIDE = "guide"

# -- Audio methods ----------------------------------------------------------

GET_SPEAKER_SETTINGS = "getSpeakerSettings"
SET_SPEAKER_SETTINGS = "setSpeakerSettings"
GET_SOUND_SETTINGS = "getSoundSettings"
SET_SOUND_SETTINGS = "setSoundSettings"
GET_VOLUME_INFORMATION = "getVolumeInformation"
SET_AUDIO_VOLUME = "setAudioVolume"
SET_AUDIO_MUTE = "setAudioMute"
GET_CUSTOM_EQUALIZER_SETTINGS = "getCustomEqualizerSettings"

# -- System methods ---------------------------------------------------------

GET_SYSTEM_INFORMATION = "getSystemInformation"
GET_POWER_STATUS = "getPowerStatus"
SET_POWER_STATUS = "setPowerStatus"
GET_POWER_SETTINGS = "getPowerSettings"
GET_SLEEP_TIMER_SETTINGS = "getSleepTimerSettings"
GET_DEVICE_MISC_SETTINGS = "getDeviceMiscSettings"
GET_INTERFACE_INFORMATION = "getInterfaceInformation"
GET_SW_UPDATE_INFO = "getSWUpdateInfo"

# -- AV Content methods -----------------------------------------------------

GET_CURRENT_EXTERNAL_TERMINALS_STATUS = "getCurrentExternalTerminalsStatus"
GET_PLAYING_CONTENT_INFO = "getPlayingContentInfo"
SET_PLAY_CONTENT = "setPlayContent"
GET_SOURCE_LIST = "getSourceList"
GET_AVAILABLE_PLAYBACK_FUNCTION = "getAvailablePlaybackFunction"

# -- Guide methods ----------------------------------------------------------

GET_SUPPORTED_API_INFO = "getSupportedApiInfo"

# -- Setting type identifiers -----------------------------------------------

TYPE_DOUBLE_NUMBER_TARGET = "doubleNumberTarget"
TYPE_ENUM_TARGET = "enumTarget"
TYPE_BOOLEAN_TARGET = "booleanTarget"
