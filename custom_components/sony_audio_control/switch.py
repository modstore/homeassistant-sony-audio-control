"""Switch platform for Sony Audio Control."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SonyAudioCoordinator
from .entity_factory import create as entity_factory_create
from .setting_entity import SonySettingEntity

TRUE_VALUES = {True, "true", "on", "enabled", "active"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SonyAudioCoordinator = entry.runtime_data
    async_add_entities(
        [
            entity_factory_create(coordinator, desc)
            for desc in coordinator.setting_descriptions
            if desc.kind == "switch"
        ]
    )


class SonyAudioSwitch(SonySettingEntity, SwitchEntity):
    """Sony boolean setting."""

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data
        if not state:
            return None
        if self.description.key == "audio_mute":
            return state.volume.muted if state.volume else None
        if not self.description.target:
            return None
        setting = self._setting
        if setting is None:
            return None
        value = setting.current_value
        return value in TRUE_VALUES or str(value).lower() in TRUE_VALUES

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)

    async def _set(self, value: bool) -> None:
        if self.description.key == "audio_mute":
            await self.coordinator.client.set_mute(value)
        elif self.description.target and self.description.set_method == "setSoundSettings":
            await self.coordinator.client.set_sound_setting(self.description.target, "on" if value else "off")
        elif self.description.target and self.description.set_method == "setSpeakerSettings":
            await self.coordinator.client.set_speaker_setting(self.description.target, "on" if value else "off")
        await self.coordinator.async_request_refresh()
