"""Entity Watchdog Autodiscover Integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

DOMAIN = "entity_watchdog_autodiscover"
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Watchdog Autodiscover from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    target_entry_id = entry.data.get("target_config_entry_id")
    device_class_filter = entry.options.get(
        "device_class_filter", entry.data.get("device_class_filter", "battery")
    )

    watched_entities = async_get_entities_for_config_entry(
        hass, target_entry_id, device_class_filter
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "target_entry_id": target_entry_id,
        "device_class_filter": device_class_filter,
        "watched_entities": watched_entities,
    }

    @callback
    def async_entity_registry_updated(event):
        """Reagiert auf Änderungen in der Entity Registry."""
        action = event.data.get("action")
        if action in ("create", "remove", "update"):
            updated_entities = async_get_entities_for_config_entry(
                hass, target_entry_id, device_class_filter
            )
            hass.data[DOMAIN][entry.entry_id]["watched_entities"] = updated_entities

    entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED, async_entity_registry_updated
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)
    return True


def async_get_entities_for_config_entry(
    hass: HomeAssistant, target_selection: str, device_class_filter: str
) -> list[str]:
    """Holt die Entitäten aus der Registry basierend auf Entry ID oder Domain."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    device_ids: set[str] = set()

    # Prüfung: Ist es eine gesamte Domain (z.B. domain:xiaomi_ble) oder eine einzelne Entry ID?
    if target_selection and target_selection.startswith("domain:"):
        target_domain = target_selection.split("domain:", 1)[1]
        for entry in hass.config_entries.async_entries(target_domain):
            devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
            device_ids.update({dev.id for dev in devices})
    elif target_selection:
        devices = dr.async_entries_for_config_entry(dev_reg, target_selection)
        device_ids = {dev.id for dev in devices}

    matched_entities: list[str] = []

    for entity_entry in ent_reg.entities.values():
        if entity_entry.device_id in device_ids and not entity_entry.disabled_by:
            if device_class_filter == "battery" and entity_entry.device_class == "battery":
                matched_entities.append(entity_entry.entity_id)
            elif device_class_filter == "signal_strength" and (
                entity_entry.device_class == "signal_strength" 
                or "rssi" in entity_entry.entity_id
            ):
                matched_entities.append(entity_entry.entity_id)
            elif device_class_filter == "all_sensors" and entity_entry.domain == "sensor":
                matched_entities.append(entity_entry.entity_id)

    return matched_entities