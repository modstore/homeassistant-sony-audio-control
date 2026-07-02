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

    def __init__(
        self, coordinator: SonyAudioCoordinator, description: SettingDescription
    ) -> None:
        super().__init__(coordinator)
        self.description = description
        self._attr_unique_id = f"{coordinator.client.host}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_name = description.name
        if description.icon:
            self._attr_icon = description.icon

    @property
    def device_info(self) -> DeviceInfo:
        state = self.coordinator.data
        system = state.system if state else None
        system_info = system.raw if system else {}

        name = (
            state.device_name
            or system_info.get("productName")
            or system_info.get("deviceName")
            or system_info.get("modelName")
        )
        model = (
            state.model_name
            or system_info.get("modelName")
            or system_info.get("model")
        )
        firmware = system.firmware if system else None
        mac = system.mac if system else None

        identifiers = {(DOMAIN, str(mac or self.coordinator.client.host))}
        connections = {("mac", mac)} if mac else set()

        return DeviceInfo(
            identifiers=identifiers,
            connections=connections,
            name=name or model or "Sony Audio Device",
            manufacturer="Sony",
            model=model,
            sw_version=firmware,
            configuration_url=f"http://{self.coordinator.client.host}:{self.coordinator.client.port}",
        )
