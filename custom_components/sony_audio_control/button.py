"""Button platform for Sony Audio Control."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity
from .sony.models import SettingDescription


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SonyAudioCoordinator = entry.runtime_data
    buttons = [
        SettingDescription(key="refresh", name="Refresh", kind="button", service="core", icon="mdi:refresh"),
    ]
    async_add_entities([SonyAudioButton(coordinator, desc) for desc in buttons])


class SonyAudioButton(SonyAudioEntity, ButtonEntity):
    """Sony action button."""

    async def async_press(self) -> None:
        if self.description.key == "refresh":
            await self.coordinator.async_request_refresh()
