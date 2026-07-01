from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator

class SonyAudioEntity(CoordinatorEntity[SonyAudioCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SonyAudioCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Sony",
            configuration_url=f"http://{coordinator.api.host}:{coordinator.api.port}/sony/guide",
        )
