from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
        SonyAudioSelect(coordinator, desc)
        for desc in coordinator.dynamic_settings
        if desc.kind == "select"
    )

class SonyAudioSelect(SonyAudioEntity, SelectEntity):
    def __init__(self, coordinator: SonyAudioCoordinator, description: DynamicSettingDescription) -> None:
        super().__init__(coordinator, f"select_{description.key}")
        self.description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_options = list(description.options)

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.setting_value(self.description.key)
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        if not self.description.setter:
            return
        await self.coordinator.api.set_setting(self.description.setter, self.description.target, option)
        await self.coordinator.async_request_refresh()
