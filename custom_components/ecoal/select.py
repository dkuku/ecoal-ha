"""Select entities for eCoal controller."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import (
    FEEDER_MODE_BATCH,
    FEEDER_MODE_ECOAL,
    FEEDER_MODE_GROUP,
    FEEDER_MODE_MANUAL,
)
from .const import DOMAIN
from .coordinator import EcoalCoordinator

_LOGGER = logging.getLogger(__name__)

FEEDER_MODE_TO_OPTION = {
    FEEDER_MODE_MANUAL: "retort_manual",
    FEEDER_MODE_GROUP: "retort_group",
    FEEDER_MODE_ECOAL: "retort_ecoal",
    FEEDER_MODE_BATCH: "batch",
}

OPTION_TO_FEEDER_MODE = {v: k for k, v in FEEDER_MODE_TO_OPTION.items()}

FEEDER_OPTIONS = [
    "retort_manual",
    "retort_group",
    "retort_ecoal",
    "batch",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal select entities."""
    coordinator: EcoalCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EcoalFeederModeSelect(coordinator, entry),
    ])


class EcoalFeederModeSelect(CoordinatorEntity[EcoalCoordinator], SelectEntity):
    """Select entity for choosing feeder combustion algorithm (PARAM 119)."""

    _attr_has_entity_name = True
    _attr_translation_key = "feeder_mode"
    _attr_icon = "mdi:cog-transfer"
    _attr_options = FEEDER_OPTIONS
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EcoalCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_feeder_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="eCoal",
            manufacturer="eCoal",
            model="Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selected feeder mode."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.get("feeder_mode")
        if mode is None:
            return None
        return FEEDER_MODE_TO_OPTION.get(mode)

    async def async_select_option(self, option: str) -> None:
        """Change the feeder mode on the furnace controller."""
        mode = OPTION_TO_FEEDER_MODE.get(option)
        if mode is None:
            _LOGGER.error("Invalid feeder mode selected: %s", option)
            return
        await self.coordinator.async_set_feeder_mode(mode)
