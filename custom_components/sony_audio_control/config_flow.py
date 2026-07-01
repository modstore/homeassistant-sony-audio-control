"""Config flow for Sony Audio Control."""
from __future__ import annotations

from typing import Any
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN
from .sony.client import SonyAudioClient
from .sony.exceptions import SonyAudioConnectionError, SonyAudioError

_LOGGER = logging.getLogger(__name__)


class SonyAudioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sony Audio Control."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = SonyAudioClient(session, host, port)
            try:
                # Some Sony audio devices do not expose every discovery endpoint
                # consistently, so validate with a best-effort sequence.
                info = await client.system_information()
                if not info:
                    await client.supported_api_info()
            except SonyAudioConnectionError:
                errors["base"] = "cannot_connect"
            except SonyAudioError as err:
                _LOGGER.debug("Sony Audio validation returned API error, falling back to audio probe: %s", err)
                try:
                    await client.get_speaker_setting("subwooferLevel")
                except Exception as fallback_err:  # noqa: BLE001 - keep config flow user-friendly
                    _LOGGER.exception("Sony Audio fallback validation failed")
                    errors["base"] = "cannot_connect"
                else:
                    title = f"Sony Audio {host}"
                    return self.async_create_entry(title=title, data={CONF_HOST: host, CONF_PORT: port})
            except Exception:  # noqa: BLE001 - avoid generic UI "Unexpected error" during setup
                _LOGGER.exception("Unexpected error while validating Sony Audio device")
                errors["base"] = "cannot_connect"
            else:
                title = info.get("productName") or info.get("modelName") or f"Sony Audio {host}"
                return self.async_create_entry(title=title, data={CONF_HOST: host, CONF_PORT: port})

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
