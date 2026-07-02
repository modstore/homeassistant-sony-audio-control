"""Generic setting entity base class for Sony Audio Control."""
from __future__ import annotations

from homeassistant.helpers.entity import Entity

from .coordinator import SonyAudioCoordinator
from .entity import SonyAudioEntity
from .sony.models import SettingDescription, SonySetting


class SonySettingEntity(SonyAudioEntity, Entity):
    """Base entity for Sony settings that appear in speaker or sound settings."""

    def __init__(
        self, coordinator: SonyAudioCoordinator, description: SettingDescription
    ) -> None:
        super().__init__(coordinator, description)
        self.target = description.target

    @property
    def _setting(self) -> SonySetting | None:
        """Return the current SonySetting for this entity's target, if any."""
        if not self.target:
            return None
        state = self.coordinator.data
        if not state:
            return None
        return (
            state.speaker_settings.get(self.target)
            or state.sound_settings.get(self.target)
        )

    @property
    def available(self) -> bool:
        """Return True if the setting exists and is available."""
        setting = self._setting
        if setting is not None:
            return setting.available
        return super().available
