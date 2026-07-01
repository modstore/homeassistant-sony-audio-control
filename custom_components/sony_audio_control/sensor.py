"""Sensor platform for Sony Audio Control."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity
from .sony.models import SettingDescription

CORE_SENSORS = [
    SettingDescription(key="power_status", name="Power Status", kind="sensor", service="system"),
    SettingDescription(key="current_input", name="Current Input", kind="sensor", service="avContent"),
    SettingDescription(key="model_name", name="Model", kind="sensor", service="system"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = entry.runtime_data
    entities = [SonyAudioSensor(coordinator, desc) for desc in CORE_SENSORS]
    entities.extend(SonyAudioSensor(coordinator, desc) for desc in coordinator.setting_descriptions if desc.kind == "sensor" and desc.key != "media_player_main")
    async_add_entities(entities)


class SonyAudioSensor(SonyAudioEntity, SensorEntity):
    """Sony diagnostic/current value sensor."""

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
        key = self.description.key
        if key == "power_status":
            return data.power
        if key == "current_input":
            return data.input_title or data.input_uri
        if key == "model_name":
            return data.model_name
        if self.description.target:
            return data.sound_settings.get(self.description.target, data.speaker_settings.get(self.description.target))
        return None
