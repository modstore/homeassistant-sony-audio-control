"""Select entities for Sony Audio Control."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_SELECT_TARGETS, DOMAIN
from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    targets = set(data.get("sound_settings", {}).keys()) or set(DEFAULT_SELECT_TARGETS.keys())
    async_add_entities([SonySoundSettingSelect(coordinator, target, DEFAULT_SELECT_TARGETS.get(target, target)) for target in targets])

class SonySoundSettingSelect(SonyAudioEntity, SelectEntity):
    """Sound setting select."""

    _attr_icon = "mdi:tune"

    def __init__(self, coordinator: SonyAudioCoordinator, target: str, name: str) -> None:
        super().__init__(coordinator, f"sound_{target}")
        self.target = target
        self._attr_name = name

    @property
    def available(self) -> bool:
        return super().available and self.target in (self.coordinator.data or {}).get("sound_settings", {})

    @property
    def current_option(self) -> str | None:
        setting = self._setting_dict()
        return setting.get("currentValue") or setting.get("value") or setting.get("title")

    @property
    def options(self) -> list[str]:
        setting = self._setting_dict()
        candidates = setting.get("candidate") or setting.get("candidates") or setting.get("option") or []
        options: list[str] = []
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    value = item.get("value") or item.get("title") or item.get("name")
                    if value is not None:
                        options.append(str(value))
                elif item is not None:
                    options.append(str(item))
        current = self.current_option
        if current and current not in options:
            options.insert(0, current)
        return options

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.set_sound_setting(self.target, option)
        await self.coordinator.async_request_refresh()

    def _setting_dict(self) -> dict[str, Any]:
        raw = (self.coordinator.data or {}).get("sound_settings", {}).get(self.target)
        if isinstance(raw, list) and raw:
            raw = raw[0]
        if isinstance(raw, dict) and "settings" in raw:
            settings = raw.get("settings")
            if isinstance(settings, list) and settings:
                return settings[0] if isinstance(settings[0], dict) else {}
        return raw if isinstance(raw, dict) else {}
