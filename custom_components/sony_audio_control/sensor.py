from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .discovery import DynamicSettingDescription
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        SonyAudioPowerSensor(coordinator),
        SonyAudioSupportedMethodsSensor(coordinator),
        SonyAudioPlayingContentSensor(coordinator),
    ]
    entities.extend(
        SonyAudioSettingSensor(coordinator, desc)
        for desc in coordinator.dynamic_settings
        if desc.kind == "sensor"
    )
    async_add_entities(entities)

class SonyAudioPowerSensor(SonyAudioEntity, SensorEntity):
    _attr_name = "Power status"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "sensor_power_status")

    @property
    def native_value(self):
        return self.coordinator.data.power_status if self.coordinator.data else None

class SonyAudioSupportedMethodsSensor(SonyAudioEntity, SensorEntity):
    _attr_name = "Supported API methods"
    _attr_icon = "mdi:api"

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "sensor_supported_api_methods")

    @property
    def native_value(self):
        return len(self.coordinator.supported_methods)

    @property
    def extra_state_attributes(self):
        return {"methods": sorted(self.coordinator.supported_methods)}

class SonyAudioPlayingContentSensor(SonyAudioEntity, SensorEntity):
    _attr_name = "Playing content"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "sensor_playing_content")

    @property
    def native_value(self):
        data = self.coordinator.data.playing_content if self.coordinator.data else {}
        return data.get("title") or data.get("source") or data.get("uri")

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.playing_content if self.coordinator.data else {}

class SonyAudioSettingSensor(SonyAudioEntity, SensorEntity):
    def __init__(self, coordinator: SonyAudioCoordinator, description: DynamicSettingDescription) -> None:
        super().__init__(coordinator, f"sensor_{description.key}")
        self.description = description
        self._attr_name = description.name
        self._attr_icon = description.icon

    @property
    def native_value(self):
        value = self.coordinator.setting_value(self.description.key)
        return str(value) if value is not None else None
