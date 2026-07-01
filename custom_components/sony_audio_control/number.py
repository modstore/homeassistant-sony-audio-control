from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .discovery import DynamicSettingDescription
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SonyAudioNumber(coordinator, desc)
        for desc in coordinator.dynamic_settings
        if desc.kind == "number"
    )

class SonyAudioNumber(SonyAudioEntity, NumberEntity):
    def __init__(self, coordinator: SonyAudioCoordinator, description: DynamicSettingDescription) -> None:
        super().__init__(coordinator, f"number_{description.key}")
        self.description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_native_min_value = description.native_min_value
        self._attr_native_max_value = description.native_max_value
        self._attr_native_step = description.native_step

    @property
    def native_value(self) -> float | None:
        return _to_float(self.coordinator.setting_value(self.description.key))

    async def async_set_native_value(self, value: float) -> None:
        if not self.description.setter:
            return
        await self.coordinator.api.set_setting(self.description.setter, self.description.target, value)
        await self.coordinator.async_request_refresh()


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
