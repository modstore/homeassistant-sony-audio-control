"""Base entity classes for Sony Audio Control."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator
from .sony.models import SettingDescription


class SonyAudioEntity(CoordinatorEntity[SonyAudioCoordinator]):
    """Base Sony audio entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SonyAudioCoordinator, description: SettingDescription) -> None:
        super().__init__(coordinator)
        self.description = description
        self._attr_unique_id = f"{coordinator.client.host}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_name = description.name
        if description.icon:
            self._attr_icon = description.icon

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        name = data.device_name if data else None
        model = data.model_name if data else None
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.client.host)},
            name=name or "Sony Audio Device",
            manufacturer="Sony",
            model=model,
            configuration_url=f"http://{self.coordinator.client.host}:{self.coordinator.client.port}",
        )
