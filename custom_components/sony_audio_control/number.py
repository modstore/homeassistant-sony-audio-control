"""Number entities for Sony Audio Control."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_SPEAKER_LEVEL_TARGETS, DOMAIN
from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    data = coordinator.data or {}
    available_targets = set(data.get("speaker_settings", {}).keys()) or set(DEFAULT_SPEAKER_LEVEL_TARGETS.keys())
    for target in available_targets:
        name = DEFAULT_SPEAKER_LEVEL_TARGETS.get(target, target)
        entities.append(SonySpeakerLevelNumber(coordinator, target, name))
    async_add_entities(entities)

class SonySpeakerLevelNumber(SonyAudioEntity, NumberEntity):
    """Speaker level setting exposed as a number."""

    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = -10
    _attr_native_max_value = 10
    _attr_native_step = 0.5
    _attr_icon = "mdi:speaker"

    def __init__(self, coordinator: SonyAudioCoordinator, target: str, name: str) -> None:
        super().__init__(coordinator, f"speaker_{target}")
        self.target = target
        self._attr_translation_key = target
        self._attr_name = name

    @property
    def available(self) -> bool:
        return super().available and self.target in (self.coordinator.data or {}).get("speaker_settings", {})

    @property
    def native_value(self) -> float | None:
        setting = self._setting_dict()
        value = setting.get("currentValue") or setting.get("value")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @property
    def native_min_value(self) -> float:
        setting = self._setting_dict()
        return self._float_from(setting, ("min", "minValue"), self._attr_native_min_value)

    @property
    def native_max_value(self) -> float:
        setting = self._setting_dict()
        return self._float_from(setting, ("max", "maxValue"), self._attr_native_max_value)

    @property
    def native_step(self) -> float:
        setting = self._setting_dict()
        return self._float_from(setting, ("step", "stepValue"), self._attr_native_step)

    async def async_set_native_value(self, value: float) -> None:
        # Sony accepts speaker level values as strings.
        rounded = int(value) if value == int(value) else value
        await self.coordinator.api.set_speaker_setting(self.target, str(rounded))
        await self.coordinator.async_request_refresh()

    def _setting_dict(self) -> dict[str, Any]:
        raw = (self.coordinator.data or {}).get("speaker_settings", {}).get(self.target)
        if isinstance(raw, list) and raw:
            raw = raw[0]
        if isinstance(raw, dict) and "settings" in raw:
            settings = raw.get("settings")
            if isinstance(settings, list) and settings:
                return settings[0] if isinstance(settings[0], dict) else {}
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _float_from(data: dict[str, Any], keys: tuple[str, ...], default: float) -> float:
        for key in keys:
            if key in data:
                try:
                    return float(data[key])
                except (TypeError, ValueError):
                    pass
        return float(default)
