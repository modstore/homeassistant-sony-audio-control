"""Number platform for Sony Audio Control."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SonyAudioCoordinator
from .entity_factory import create as entity_factory_create
from .setting_entity import SonySettingEntity
from .sony.constants import SET_SOUND_SETTINGS, SET_SPEAKER_SETTINGS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SonyAudioCoordinator = entry.runtime_data
    async_add_entities(
        [
            entity_factory_create(coordinator, desc)
            for desc in coordinator.setting_descriptions
            if desc.kind == "number"
        ]
    )


class SonyAudioNumber(SonySettingEntity, NumberEntity):
    """Sony numeric setting."""

    _attr_mode = NumberMode.SLIDER

    @property
    def native_min_value(self) -> float:
        return self.description.min_value if self.description.min_value is not None else -10

    @property
    def native_max_value(self) -> float:
        return self.description.max_value if self.description.max_value is not None else 10

    @property
    def native_step(self) -> float:
        return self.description.step if self.description.step is not None else 0.5

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.description.unit

    @property
    def native_value(self) -> float | None:
        setting = self._setting
        if not setting:
            return None
        try:
            return float(setting.current_value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        if not self.description.target or not self.description.set_method:
            return
        text = str(int(value)) if float(value).is_integer() else str(value)
        if self.description.set_method == SET_SPEAKER_SETTINGS:
            await self.coordinator.async_set_speaker_setting(self.description.target, text)
        elif self.description.set_method == SET_SOUND_SETTINGS:
            await self.coordinator.async_set_sound_setting(self.description.target, text)
