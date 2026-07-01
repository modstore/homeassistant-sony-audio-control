from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .discovery import BOOLEAN_FALSE, BOOLEAN_TRUE, DynamicSettingDescription
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [SonyAudioMuteSwitch(coordinator)]
    entities.extend(
        SonyAudioSettingSwitch(coordinator, desc)
        for desc in coordinator.dynamic_settings
        if desc.kind == "switch"
    )
    async_add_entities(entities)

class SonyAudioMuteSwitch(SonyAudioEntity, SwitchEntity):
    _attr_name = "Mute"
    _attr_icon = "mdi:volume-mute"

    def __init__(self, coordinator: SonyAudioCoordinator) -> None:
        super().__init__(coordinator, "switch_mute")

    @property
    def is_on(self) -> bool | None:
        volume = self.coordinator.primary_volume()
        if not volume:
            return None
        return bool(volume.get("mute"))

    async def async_turn_on(self, **kwargs) -> None:
        volume = self.coordinator.primary_volume() or {}
        await self.coordinator.api.set_mute(True, str(volume.get("target") or "master"))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        volume = self.coordinator.primary_volume() or {}
        await self.coordinator.api.set_mute(False, str(volume.get("target") or "master"))
        await self.coordinator.async_request_refresh()

class SonyAudioSettingSwitch(SonyAudioEntity, SwitchEntity):
    def __init__(self, coordinator: SonyAudioCoordinator, description: DynamicSettingDescription) -> None:
        super().__init__(coordinator, f"switch_{description.key}")
        self.description = description
        self._attr_name = description.name
        self._attr_icon = description.icon

    @property
    def is_on(self) -> bool | None:
        value = str(self.coordinator.setting_value(self.description.key)).lower()
        if value in BOOLEAN_TRUE:
            return True
        if value in BOOLEAN_FALSE:
            return False
        return None

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_bool(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_bool(False)

    async def _set_bool(self, enabled: bool) -> None:
        value = _best_bool_value(self.description.options, enabled)
        await self.coordinator.api.set_setting(self.description.setter or "setSoundSettings", self.description.target, value)
        await self.coordinator.async_request_refresh()


def _best_bool_value(options: tuple[str, ...], enabled: bool) -> str:
    desired = BOOLEAN_TRUE if enabled else BOOLEAN_FALSE
    for option in options:
        if option.lower() in desired:
            return option
    return "on" if enabled else "off"
