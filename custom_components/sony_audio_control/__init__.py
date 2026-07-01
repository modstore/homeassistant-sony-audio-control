"""Sony Audio Control integration."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENDPOINT,
    ATTR_METHOD,
    ATTR_PARAMS,
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
    PLATFORMS,
    SERVICE_CALL_API,
    SERVICE_DUMP_DEVICE_INFO,
)
from .coordinator import SonyAudioCoordinator
from .sony.client import SonyAudioClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sony Audio Control from a config entry."""
    session = async_get_clientsession(hass)
    client = SonyAudioClient(session, entry.data[CONF_HOST], entry.data[CONF_PORT])
    coordinator = SonyAudioCoordinator(hass, client)
    await coordinator.async_discover()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_DUMP_DEVICE_INFO):
        return

    async def async_dump_device_info(call: ServiceCall) -> None:
        host = call.data.get(CONF_HOST)
        coordinators = _coordinators(hass)
        coordinator = next((item for item in coordinators if not host or item.client.host == host), None)
        if coordinator is None:
            _LOGGER.warning("No Sony Audio Control config entry found for diagnostics dump")
            return
        targets = [desc.target for desc in coordinator.setting_descriptions if desc.target]
        dump = await coordinator.client.dump_device_info([target for target in targets if target])
        path = Path(hass.config.path(f"sony_audio_control_{coordinator.client.host.replace('.', '_')}_dump.json"))
        await hass.async_add_executor_job(path.write_text, json.dumps(dump, indent=2, sort_keys=True), "utf-8")
        _LOGGER.info("Sony Audio Control device dump written to %s", path)

    async def async_call_api(call: ServiceCall) -> None:
        host = call.data.get(CONF_HOST)
        endpoint = call.data[ATTR_ENDPOINT]
        method = call.data[ATTR_METHOD]
        params = call.data.get(ATTR_PARAMS) or []
        coordinator = next((item for item in _coordinators(hass) if not host or item.client.host == host), None)
        if coordinator is None:
            _LOGGER.warning("No Sony Audio Control config entry found for API call")
            return
        result = await coordinator.client.call(endpoint, method, params)
        _LOGGER.info("Sony Audio Control API result for %s/%s: %s", endpoint, method, result)

    hass.services.async_register(
        DOMAIN,
        SERVICE_DUMP_DEVICE_INFO,
        async_dump_device_info,
        schema=vol.Schema({vol.Optional(CONF_HOST): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CALL_API,
        async_call_api,
        schema=vol.Schema(
            {
                vol.Optional(CONF_HOST): cv.string,
                vol.Required(ATTR_ENDPOINT): cv.string,
                vol.Required(ATTR_METHOD): cv.string,
                vol.Optional(ATTR_PARAMS, default=[]): list,
            }
        ),
    )


def _coordinators(hass: HomeAssistant) -> list[SonyAudioCoordinator]:
    entries = hass.config_entries.async_entries(DOMAIN)
    return [entry.runtime_data for entry in entries if getattr(entry, "runtime_data", None) is not None]
