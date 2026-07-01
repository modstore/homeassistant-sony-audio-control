"""Sensor entities for Sony Audio Control."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SonySimpleSensor(coordinator, "power_status", "Power Status", "power", "status", "mdi:power"),
        SonyPlayingSensor(coordinator),
    ])

class SonySimpleSensor(SonyAudioEntity, SensorEntity):
    """Simple sensor based on a result key."""

    def __init__(self, coordinator: SonyAudioCoordinator, key: str, name: str, data_key: str, value_key: str, icon: str) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name
        self._data_key = data_key
        self._value_key = value_key
        self._attr_icon = icon

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data.get(self._data_key) if self.coordinator.data else None
        item = self._first_dict(data)
        value = item.get(self._value_key)
        return str(value) if value is not None else None

    @staticmethod
    def _first_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, list) and value:
            value = value[0]
        return value if isinstance(value, dict) else {}

class SonyPlayingSensor(SonyAudioEntity, SensorEntity):
    """Current playing content/input info."""

    _attr_name = "Playing Content"
    _attr_icon = "mdi:audio-video"

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "playing_content")

    @property
    def native_value(self) -> str | None:
        item = self._playing_dict()
        return item.get("title") or item.get("source") or item.get("uri")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._playing_dict()

    def _playing_dict(self) -> dict[str, Any]:
        value = self.coordinator.data.get("playing") if self.coordinator.data else None
        if isinstance(value, list) and value:
            value = value[0]
        return value if isinstance(value, dict) else {}
