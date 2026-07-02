"""Select platform for Sony Audio Control."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SUBWOOFER_MANUAL_PRESET, SUBWOOFER_PRESET_KEY, SUBWOOFER_PRESETS
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
            if desc.kind == "select" and desc.key != "input_source"
        ]
    )


class SonyAudioSelect(SonySettingEntity, SelectEntity):
    """Sony selectable setting."""

    @property
    def options(self) -> list[str]:
        return self.description.option_values

    @property
    def current_option(self) -> str | None:
        setting = self._setting
        if not setting:
            return None
        value = setting.current_value
        if value is None:
            return None
        if self.description.key == SUBWOOFER_PRESET_KEY:
            try:
                current = float(value)
            except (TypeError, ValueError):
                return SUBWOOFER_MANUAL_PRESET
            for label, preset_value in SUBWOOFER_PRESETS.items():
                if current == preset_value:
                    return label
            return SUBWOOFER_MANUAL_PRESET
        raw = str(value)
        for label, raw_value in self.description.option_map.items():
            if raw_value == raw:
                return label
        return raw if raw in self.description.option_values else None

    async def async_select_option(self, option: str) -> None:
        if not self.description.target or not self.description.set_method:
            return
        if self.description.key == SUBWOOFER_PRESET_KEY and option == SUBWOOFER_MANUAL_PRESET:
            # Manual is a read-only/current-state option used when the level does
            # not match a preset. Selecting it should not change the receiver.
            return
        value = self.description.option_map.get(option, option)
        if self.description.set_method == SET_SPEAKER_SETTINGS:
            await self.coordinator.async_set_speaker_setting(self.description.target, value)
        elif self.description.set_method == SET_SOUND_SETTINGS:
            await self.coordinator.async_set_sound_setting(self.description.target, value)
