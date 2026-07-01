"""Base entity helpers for Sony Audio Control."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SonyAudioCoordinator

class SonyAudioEntity(CoordinatorEntity[SonyAudioCoordinator]):
    """Base Sony Audio entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SonyAudioCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_{key}"
        self._attr_device_info = coordinator.device_info
