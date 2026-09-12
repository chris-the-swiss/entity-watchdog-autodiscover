"""Entity Watchdog Auto Integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

DOMAIN = "entity_watchdog"
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Watchdog Auto from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    target_entry_id = entry.data.get("target_config_entry_id")
    device_class_filter = entry.options.get(
        "device_class_filter", entry.data.get("device_class_filter", "battery")
    )

    # 1. Automatische Ermittlung der Entitäten aus der Ziel-Integration
    watched_entities = async_get_entities_for_config_entry(
        hass, target_entry_id, device_class_filter
    )

    _LOGGER.info(
        "Entity Watchdog überwacht %d Entitäten für Integration Entry ID %s",
        len(watched_entities),
        target_entry_id,
    )

    # Speichern der überwachten Entitäten im Storage der Integration
    hass.data[DOMAIN][entry.entry_id] = {
        "target_entry_id": target_entry_id,
        "device_class_filter": device_class_filter,
        "watched_entities": watched_entities,
    }

    # 2. Registrieren eines Event-Listeners für Entity Registry Updates (Autodiscovery neuer Geräte)
    @callback
    def async_entity_registry_updated(event):
        """Reagiert, wenn neue Bluetooth-Geräte hinzugefügt oder entfernt werden."""
        action = event.data.get("action")
        if action in ("create", "remove", "update"):
            updated_entities = async_get_entities_for_config_entry(
                hass, target_entry_id, device_class_filter
            )
            hass.data[DOMAIN][entry.entry_id]["watched_entities"] = updated_entities
            _LOGGER.debug(
                "Watchdog Entitätsliste aktualisiert. Neue Anzahl: %d",
                len(updated_entities),
            )

    # Event-Listener an die Entity Registry von HA hängen
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
    hass: HomeAssistant, config_entry_id: str, device_class_filter: str
) -> list[str]:
    """Sucht alle relevanten Entitäten einer bestimmten Integration aus der Registry."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    # Alle Geräte holen, die zur gewählten Integration gehören
    devices = dr.async_entries_for_config_entry(dev_reg, config_entry_id)
    device_ids = {dev.id for dev in devices}

    matched_entities: list[str] = []

    # Alle Entitäten im System durchgehen und filtern
    for entity_entry in ent_reg.entities.values():
        if entity_entry.device_id in device_ids and not entity_entry.disabled_by:
            
            # Filter-Logik
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
