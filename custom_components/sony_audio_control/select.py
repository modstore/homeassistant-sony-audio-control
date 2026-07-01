"""Select platform for Sony Audio Control."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = entry.runtime_data
    async_add_entities([SonyAudioSelect(coordinator, desc) for desc in coordinator.setting_descriptions if desc.kind == "select" and desc.key != "input_source"])


class SonyAudioSelect(SonyAudioEntity, SelectEntity):
    """Sony selectable setting."""

    @property
    def options(self) -> list[str]:
        return self.description.option_values

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        if not data or not self.description.target:
            return None
        value = data.sound_settings.get(self.description.target, data.speaker_settings.get(self.description.target))
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        if not self.description.target or not self.description.set_method:
            return
        if self.description.set_method == "setSpeakerSettings":
            await self.coordinator.client.set_speaker_setting(self.description.target, option)
        elif self.description.set_method == "setSoundSettings":
            await self.coordinator.client.set_sound_setting(self.description.target, option)
        await self.coordinator.async_request_refresh()
