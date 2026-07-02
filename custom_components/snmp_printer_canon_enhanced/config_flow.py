"""Config flow for Canon MF754cdw SNMP Printer."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_COMMUNITY,
    CONF_SNMP_VERSION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_COMMUNITY,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .snmp_client import SNMPClient

_LOGGER = logging.getLogger(__name__)


class SNMPPrinterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Canon MF754cdw."""

    VERSION = 1
    _discovered_hosts: set[str] = set()

    def __init__(self):
        self.discovery_info = {}

    #
    # USER STEP → always manual, Canon MF754cdw does not require auto-detection
    #
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_manual(user_input)

    #
    # MANUAL CONFIGURATION
    #
    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors = {}

        if user_input is not None:
            client = SNMPClient(
                host=user_input[CONF_HOST],
                port=user_input.get(CONF_PORT, DEFAULT_PORT),
                snmp_version="2c",
                community=user_input.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
            )

            try:
                system_info = await client.get_system_info()
                device_info = await client.get_device_info()

                # Canon MF754cdw always returns serial number
                unique_id = device_info.get("serial_number", user_input[CONF_HOST])

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Model name from sysDescr
                description = system_info.get("description") or ""
                model_name = "Canon MF754cdw"
                if "Canon" in description:
                    model_name = description.strip()

                return self.async_create_entry(
                    title=model_name,
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                        CONF_SNMP_VERSION: "2c",
                        CONF_COMMUNITY: user_input.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
                        CONF_UPDATE_INTERVAL: user_input.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    },
                )

            except Exception:
                _LOGGER.exception("Error connecting to Canon printer")
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=user_input.get(CONF_HOST, "") if user_input else "",
                ): str,
                vol.Optional(
                    CONF_PORT,
                    default=user_input.get(CONF_PORT, DEFAULT_PORT) if user_input else DEFAULT_PORT,
                ): int,
                vol.Optional(
                    CONF_COMMUNITY,
                    default=user_input.get(CONF_COMMUNITY, DEFAULT_COMMUNITY) if user_input else DEFAULT_COMMUNITY,
                ): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                    if user_input
                    else DEFAULT_UPDATE_INTERVAL,
                ): int,
            }
        )

        return self.async_show_form(
            step_id="manual",
            data_schema=data_schema,
            errors=errors,
        )

    #
    # ZEROCONF DISCOVERY
    #
    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> FlowResult:
        host = discovery_info.host
        if not host:
            return self.async_abort(reason="unknown")

        if host in SNMPPrinterConfigFlow._discovered_hosts:
            return self.async_abort(reason="already_in_progress")

        SNMPPrinterConfigFlow._discovered_hosts.add(host)

        # Try SNMP v2c only (Canon MF754cdw)
        try:
            client = SNMPClient(
                host=host,
                port=DEFAULT_PORT,
                snmp_version="2c",
                community=DEFAULT_COMMUNITY,
                timeout=2.5,
                retries=1,
            )

            system_info = await client.get_system_info()
            device_info = await client.get_device_info()

            if not system_info.get("description"):
                raise ValueError("No SNMP data")

            description = system_info.get("description", "")
            if "Canon" not in description:
                raise ValueError("Not a Canon printer")

            model = description.strip()
            manufacturer = "Canon"

            unique_id = device_info.get("serial_number", host)
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

            self.discovery_info = {
                CONF_HOST: host,
                "model": model,
                "manufacturer": manufacturer,
            }

            return await self.async_step_zeroconf_confirm()

        except Exception:
            SNMPPrinterConfigFlow._discovered_hosts.discard(host)
            return self.async_abort(reason="not_printer")

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return await self.async_step_manual(
                {
                    CONF_HOST: self.discovery_info[CONF_HOST],
                    CONF_PORT: DEFAULT_PORT,
                    CONF_COMMUNITY: DEFAULT_COMMUNITY,
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                }
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "model": self.discovery_info.get("model", "Canon Printer"),
                "manufacturer": self.discovery_info.get("manufacturer", "Canon"),
                "host": self.discovery_info[CONF_HOST],
            },
        )

    #
    # OPTIONS FLOW
    #
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Canon MF754cdw."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        super().__init__()
        self.config_entry = config_entry
        self._data = {}

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_complete()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self.config_entry.data.get(CONF_HOST)): str,
                vol.Optional(CONF_PORT, default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(
                    CONF_COMMUNITY,
                    default=self.config_entry.data.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
                ): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL,
                        self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ),
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)

    async def async_step_complete(self, user_input=None):
        errors = {}

        client = SNMPClient(
            host=self._data.get(CONF_HOST),
            port=self._data.get(CONF_PORT, DEFAULT_PORT),
            snmp_version="2c",
            community=self._data.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
        )

        try:
            await client.get_system_info()

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=self._data,
            )

            return self.async_create_entry(title="", data=self._data)

        except Exception:
            errors["base"] = "cannot_connect"
            self._data = {}
            return await self.async_step_init()
