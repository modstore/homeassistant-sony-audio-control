"""Dynamic entity factory for Sony Audio Control."""
from __future__ import annotations

from .coordinator import SonyAudioCoordinator
from .sony.models import SettingDescription, SettingType

_TRUE_BOOLEAN_OPTIONS = {"on", "off", "true", "false", "enabled", "disabled"}


def create(
    coordinator: SonyAudioCoordinator, description: SettingDescription
) -> object:
    """Create a Home Assistant entity from a SettingDescription.

    Returns the appropriate platform entity based on the Sony setting type.
    Falls back to sensor for unknown types.
    """
    sony_type = description.sony_type

    # Lazy imports to avoid circular dependencies between factory and platforms
    if sony_type == SettingType.NUMBER.value:
        from .number import SonyAudioNumber
        return SonyAudioNumber(coordinator, description)

    if sony_type == SettingType.ENUM.value:
        from .select import SonyAudioSelect
        return SonyAudioSelect(coordinator, description)

    if sony_type == SettingType.BOOLEAN.value:
        from .switch import SonyAudioSwitch
        return SonyAudioSwitch(coordinator, description)

    # Fallback: use the pre-computed HA kind from discovery
    if description.kind == "number":
        from .number import SonyAudioNumber
        return SonyAudioNumber(coordinator, description)
    if description.kind == "select":
        from .select import SonyAudioSelect
        return SonyAudioSelect(coordinator, description)
    if description.kind == "switch":
        from .switch import SonyAudioSwitch
        return SonyAudioSwitch(coordinator, description)

    from .sensor import SonyAudioSensor
    return SonyAudioSensor(coordinator, description)
