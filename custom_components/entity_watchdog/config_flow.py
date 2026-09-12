"""Config flow for Entity Watchdog Auto integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

DOMAIN = "entity_watchdog"

_LOGGER = logging.getLogger(__name__)


class EntityWatchdogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Watchdog."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step where user selects an integration to watch."""
        errors: dict[str, str] = {}

        if user_input is not None:
            title = user_input.get("title", user_input["target_config_entry_id"])
            return self.async_create_entry(title=title, data=user_input)

        # 1. Alle aktiven Config Entries (Integrationen) ermitteln
        entries = self.hass.config_entries.async_entries()
        
        # Liste für das Dropdown erstellen
        integration_options: list[SelectOptionDict] = []
        for entry in entries:
            # Wir schließen die eigene Integration aus
            if entry.domain == DOMAIN:
                continue
            
            label = f"{entry.title} ({entry.domain})"
            integration_options.append(
                SelectOptionDict(value=entry.entry_id, label=label)
            )

        # Sortieren nach Namen
        integration_options.sort(key=lambda x: x["label"])

        # 2. Formular-Schema definieren
        data_schema = vol.Schema(
            {
                vol.Required("title", default="Bluetooth Watchdog"): cv.string,
                vol.Required("target_config_entry_id"): SelectSelector(
                    SelectSelectorConfig(
                        options=integration_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("device_class_filter", default="battery"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value="battery", label="Batterie (device_class: battery)"),
                            SelectOptionDict(value="signal_strength", label="Signalstärke / RSSI"),
                            SelectOptionDict(value="all_sensors", label="Alle Sensoren der Integration"),
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return EntityWatchdogOptionsFlowHandler()


class EntityWatchdogOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow to update settings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_filter = self.config_entry.options.get(
            "device_class_filter", 
            self.config_entry.data.get("device_class_filter", "battery")
        )

        options_schema = vol.Schema(
            {
                vol.Optional("device_class_filter", default=current_filter): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value="battery", label="Batterie (device_class: battery)"),
                            SelectOptionDict(value="signal_strength", label="Signalstärke / RSSI"),
                            SelectOptionDict(value="all_sensors", label="Alle Sensoren der Integration"),
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
