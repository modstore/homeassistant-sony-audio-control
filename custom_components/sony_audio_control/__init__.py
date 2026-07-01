from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENTRY_ID,
    ATTR_METHOD,
    ATTR_PARAMS,
    ATTR_SERVICE,
    ATTR_VERSION,
    DOMAIN,
    PLATFORMS,
    SERVICE_CALL_METHOD,
)
from .coordinator import SonyAudioCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required(ATTR_SERVICE): cv.string,
        vol.Required(ATTR_METHOD): cv.string,
        vol.Optional(ATTR_PARAMS, default=[]): list,
        vol.Optional(ATTR_VERSION, default="1.0"): cv.string,
    }
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SonyAudioCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_CALL_METHOD):
        async def async_call_method(call: ServiceCall) -> None:
            data: dict[str, Any] = dict(call.data)
            target_entry_id = data[ATTR_ENTRY_ID]
            target_coordinator: SonyAudioCoordinator | None = hass.data[DOMAIN].get(target_entry_id)
            if target_coordinator is None:
                _LOGGER.error("No Sony Audio Control config entry found for %s", target_entry_id)
                return
            result = await target_coordinator.api.call(
                data[ATTR_SERVICE],
                data[ATTR_METHOD],
                data.get(ATTR_PARAMS, []),
                data.get(ATTR_VERSION, "1.0"),
            )
            _LOGGER.info("Sony raw API result for %s.%s: %s", data[ATTR_SERVICE], data[ATTR_METHOD], result)
            await target_coordinator.async_request_refresh()

        hass.services.async_register(DOMAIN, SERVICE_CALL_METHOD, async_call_method, schema=SERVICE_SCHEMA)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
