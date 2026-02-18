"""Sensors for Ogniwo Furnace."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OgniwoCoordinator


@dataclass(frozen=True, kw_only=True)
class OgniwoSensorDescription(SensorEntityDescription):
    value_key: str
    requires_sensor: str | None = None


SENSOR_DESCRIPTIONS: tuple[OgniwoSensorDescription, ...] = (
    # --- Temperatures (conditional on sensor state) ---
    OgniwoSensorDescription(
        key="floor_temp",
        value_key="floor_temp",
        translation_key="floor_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:heating-coil",
        requires_sensor="floor_temp",
    ),
    OgniwoSensorDescription(
        key="indoor_temp",
        value_key="indoor_temp",
        translation_key="indoor_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-thermometer",
        requires_sensor="indoor_temp",
    ),
    OgniwoSensorDescription(
        key="outdoor_temp",
        value_key="outdoor_temp",
        translation_key="outdoor_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        requires_sensor="outdoor_temp",
    ),
    OgniwoSensorDescription(
        key="dhw_temp",
        value_key="dhw_temp",
        translation_key="dhw_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-thermometer",
        requires_sensor="dhw_temp",
    ),
    OgniwoSensorDescription(
        key="return_temp",
        value_key="return_temp",
        translation_key="return_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-chevron-down",
        requires_sensor="return_temp",
    ),
    OgniwoSensorDescription(
        key="feeder_temp",
        value_key="feeder_temp",
        translation_key="feeder_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-alert",
        requires_sensor="feeder_temp",
    ),
    OgniwoSensorDescription(
        key="boiler_temp",
        value_key="boiler_temp",
        translation_key="boiler_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fire",
        requires_sensor="boiler_temp",
    ),
    OgniwoSensorDescription(
        key="exhaust_temp",
        value_key="exhaust_temp",
        translation_key="exhaust_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:smoke",
        requires_sensor="exhaust_temp",
    ),
    # --- Power and runtime (always present) ---
    OgniwoSensorDescription(
        key="air_pump_power",
        value_key="air_pump_power",
        translation_key="air_pump_power",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
    ),
    OgniwoSensorDescription(
        key="feeder_runtime",
        value_key="feeder_runtime",
        translation_key="feeder_runtime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:timer-outline",
    ),
    # --- Setpoints (always present) ---
    OgniwoSensorDescription(
        key="target_boiler_temp",
        value_key="target_boiler_temp",
        translation_key="target_boiler_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-check",
    ),
    OgniwoSensorDescription(
        key="target_dhw_temp",
        value_key="target_dhw_temp",
        translation_key="target_dhw_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-water",
    ),
    OgniwoSensorDescription(
        key="co_lowered_amount",
        value_key="co_lowered_amount",
        translation_key="co_lowered_amount",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-minus",
    ),
    OgniwoSensorDescription(
        key="cwu_lowered_amount",
        value_key="cwu_lowered_amount",
        translation_key="cwu_lowered_amount",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-minus",
    ),
    # --- Room temperature setpoints (conditional on indoor sensor) ---
    OgniwoSensorDescription(
        key="room_day_temp",
        value_key="room_day_temp",
        translation_key="room_day_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:white-balance-sunny",
        requires_sensor="indoor_temp",
    ),
    OgniwoSensorDescription(
        key="room_night_temp",
        value_key="room_night_temp",
        translation_key="room_night_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:weather-night",
        requires_sensor="indoor_temp",
    ),
    # --- Floor heating setpoints (conditional on floor sensor) ---
    OgniwoSensorDescription(
        key="floor_day_temp",
        value_key="floor_day_temp",
        translation_key="floor_day_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:heating-coil",
        requires_sensor="floor_temp",
    ),
    OgniwoSensorDescription(
        key="floor_night_temp",
        value_key="floor_night_temp",
        translation_key="floor_night_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:heating-coil",
        requires_sensor="floor_temp",
    ),
    # --- Fuel data (always present) ---
    OgniwoSensorDescription(
        key="fuel_load_pct",
        value_key="fuel_load_pct",
        translation_key="fuel_load_pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:basket-fill",
    ),
    OgniwoSensorDescription(
        key="feeding_pct",
        value_key="feeding_pct",
        translation_key="feeding_pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transfer",
    ),
)

# Diagnostic sensors for modes and flags (always present)
DIAG_DESCRIPTIONS: tuple[OgniwoSensorDescription, ...] = (
    OgniwoSensorDescription(
        key="heating",
        value_key="heating",
        translation_key="heating_state",
        icon="mdi:fire",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="setpoint_mode",
        value_key="setpoint_mode",
        translation_key="setpoint_mode",
        icon="mdi:tune",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="cwu_mode",
        value_key="cwu_mode",
        translation_key="cwu_mode",
        icon="mdi:water-boiler",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="alarms_raw",
        value_key="alarms_raw",
        translation_key="alarms",
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="mixer_circuit",
        value_key="mixer_circuit",
        translation_key="mixer_circuit",
        icon="mdi:valve",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="day_night",
        value_key="day_night",
        translation_key="day_night",
        icon="mdi:theme-light-dark",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="controller_datetime",
        value_key="controller_datetime",
        translation_key="controller_datetime",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="fuel_load_date",
        value_key="fuel_load_date",
        translation_key="fuel_load_date",
        icon="mdi:calendar",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OgniwoSensorDescription(
        key="inputs_raw",
        value_key="inputs_raw",
        translation_key="inputs",
        icon="mdi:electric-switch",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OgniwoCoordinator = hass.data[DOMAIN][entry.entry_id]
    connected = coordinator.connected_sensors
    entities: list[SensorEntity] = []
    for description in SENSOR_DESCRIPTIONS:
        if description.requires_sensor and description.requires_sensor not in connected:
            continue
        entities.append(OgniwoSensor(coordinator, description, entry))
    for description in DIAG_DESCRIPTIONS:
        entities.append(OgniwoSensor(coordinator, description, entry))
    async_add_entities(entities)


class OgniwoSensor(CoordinatorEntity[OgniwoCoordinator], SensorEntity):
    entity_description: OgniwoSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OgniwoCoordinator,
        description: OgniwoSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ogniwo Furnace",
            manufacturer="Ogniwo Biecz",
            model="eCoal Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def native_value(self) -> float | int | str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.value_key)
