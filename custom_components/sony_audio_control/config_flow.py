from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SonyAudioApi, SonyAudioApiError
from .const import CONF_PORT, DEFAULT_PORT, DOMAIN

class SonyAudioControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            api = SonyAudioApi(async_get_clientsession(self.hass), host, int(port))
            try:
                # Validate that something Sony-like responds. Some audio devices may not
                # support guide discovery, so fall back to a basic audio call.
                supported = await api.get_supported_api_info()
                if not supported:
                    await api.get_volume_information()
            except SonyAudioApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Sony Audio {host}",
                    data={CONF_HOST: host, CONF_PORT: int(port)},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )
