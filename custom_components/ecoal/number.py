"""Number entities for eCoal controller."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoalCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal number entities."""
    coordinator: EcoalCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EcoalHopperCapacityNumber(coordinator, entry),
        EcoalFeederMaxRuntimeNumber(coordinator, entry),
        EcoalBlowerCorrectionNumber(coordinator, entry),
    ])


class EcoalHopperCapacityNumber(CoordinatorEntity[EcoalCoordinator], RestoreEntity, NumberEntity):
    """Number entity for configuring hopper capacity in kg."""

    _attr_has_entity_name = True
    _attr_translation_key = "hopper_capacity"
    _attr_icon = "mdi:weight-kilogram"
    _attr_device_class = NumberDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_native_min_value = 10.0
    _attr_native_max_value = 1000.0
    _attr_native_step = 5.0
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EcoalCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_hopper_capacity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="eCoal",
            manufacturer="eCoal",
            model="Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    async def async_added_to_hass(self) -> None:
        """Restore previous capacity setting on restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                kg = int(float(last_state.state))
                self.coordinator.set_hopper_capacity(kg)
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float | None:
        """Return current hopper capacity in kg."""
        return float(self.coordinator.hopper_capacity_kg)

    async def async_set_native_value(self, value: float) -> None:
        """Set hopper capacity in kg."""
        self.coordinator.set_hopper_capacity(int(value))


class EcoalFeederMaxRuntimeNumber(CoordinatorEntity[EcoalCoordinator], NumberEntity):
    """Number entity for configuring max feeder runtime until empty (PARAM 79)."""

    _attr_has_entity_name = True
    _attr_translation_key = "feeder_max_runtime"
    _attr_icon = "mdi:timer-sand"
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 0.0
    _attr_native_max_value = 10000.0
    _attr_native_step = 10.0
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EcoalCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_feeder_max_runtime"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="eCoal",
            manufacturer="eCoal",
            model="Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def native_value(self) -> float | None:
        """Return feeder max runtime in minutes."""
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get("feeder_max_runtime")
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Write feeder max runtime in minutes to furnace controller."""
        await self.coordinator.async_set_feeder_max_runtime(int(value))


class EcoalBlowerCorrectionNumber(CoordinatorEntity[EcoalCoordinator], NumberEntity):
    """Number entity for configuring blower power correction percentage (PARAM 94)."""

    _attr_has_entity_name = True
    _attr_translation_key = "blower_correction"
    _attr_icon = "mdi:fan-plus"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = -6.0
    _attr_native_max_value = 6.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EcoalCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_blower_correction"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="eCoal",
            manufacturer="eCoal",
            model="Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def native_value(self) -> float | None:
        """Return blower power correction percentage."""
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get("blower_correction")
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set blower power correction percentage on furnace controller."""
        await self.coordinator.async_set_blower_correction(int(value))
