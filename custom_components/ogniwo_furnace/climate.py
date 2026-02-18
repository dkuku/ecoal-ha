"""Climate entities for Ogniwo Furnace - CO heating, CWU hot water, floor heating."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import CWU_MODE_OFF, CWU_MODE_WINTER
from .const import DOMAIN
from .coordinator import OgniwoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OgniwoCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ClimateEntity] = [
        OgniwoHeatingClimate(coordinator, entry),
        OgniwoCWUClimate(coordinator, entry),
    ]
    if "floor_temp" in coordinator.connected_sensors:
        entities.append(OgniwoFloorClimate(coordinator, entry))
    async_add_entities(entities)


class OgniwoHeatingClimate(CoordinatorEntity[OgniwoCoordinator], ClimateEntity):
    """Climate entity for the central heating (CO) circuit."""

    _attr_has_entity_name = True
    _attr_name = "Heating"
    _attr_translation_key = "heating"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = 30
    _attr_max_temp = 80
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: OgniwoCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate_co"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ogniwo Furnace",
            manufacturer="Ogniwo Biecz",
            model="eCoal Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def current_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("boiler_temp")

    @property
    def target_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("target_boiler_temp")

    @property
    def hvac_mode(self) -> HVACMode:
        if self.coordinator.data and self.coordinator.data.get("auto_mode"):
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.coordinator.data is None:
            return None
        if self.coordinator.data.get("air_pump") or self.coordinator.data.get("coal_feeder"):
            return HVACAction.HEATING
        if self.coordinator.data.get("auto_mode"):
            return HVACAction.IDLE
        return HVACAction.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.coordinator.client.set_target_boiler_temp(int(temp))
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.client.set_auto_mode(True)
        else:
            await self.coordinator.client.set_auto_mode(False)
        await self.coordinator.async_request_refresh()


class OgniwoCWUClimate(CoordinatorEntity[OgniwoCoordinator], ClimateEntity):
    """Climate entity for domestic hot water (CWU) circuit."""

    _attr_has_entity_name = True
    _attr_name = "Hot Water"
    _attr_translation_key = "hot_water"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = 30
    _attr_max_temp = 65
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: OgniwoCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate_cwu"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ogniwo Furnace",
            manufacturer="Ogniwo Biecz",
            model="eCoal Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def current_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("dhw_temp")

    @property
    def target_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("target_dhw_temp")

    @property
    def hvac_mode(self) -> HVACMode:
        if self.coordinator.data is None:
            return HVACMode.OFF
        cwu_mode = self.coordinator.data.get("cwu_mode", 4)
        if cwu_mode == CWU_MODE_OFF:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.coordinator.data is None:
            return None
        if self.coordinator.data.get("dhw_pump"):
            return HVACAction.HEATING
        cwu_mode = self.coordinator.data.get("cwu_mode", 4)
        if cwu_mode == CWU_MODE_OFF:
            return HVACAction.OFF
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.coordinator.client.set_target_dhw_temp(int(temp))
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.client.set_cwu_mode(CWU_MODE_WINTER)
        else:
            await self.coordinator.client.set_cwu_mode(CWU_MODE_OFF)
        await self.coordinator.async_request_refresh()


class OgniwoFloorClimate(CoordinatorEntity[OgniwoCoordinator], ClimateEntity):
    """Climate entity for the floor heating circuit (mixer/underfloor)."""

    _attr_has_entity_name = True
    _attr_name = "Floor Heating"
    _attr_translation_key = "floor_heating"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = 20
    _attr_max_temp = 55
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: OgniwoCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate_floor"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ogniwo Furnace",
            manufacturer="Ogniwo Biecz",
            model="eCoal Furnace Controller",
            sw_version=coordinator.firmware_version,
        )

    @property
    def current_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("floor_temp")

    @property
    def target_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        if self.coordinator.data.get("floor_day_night", 0) == 1:
            return self.coordinator.data.get("floor_night_temp")
        return self.coordinator.data.get("floor_day_temp")

    @property
    def hvac_mode(self) -> HVACMode:
        if self.coordinator.data and self.coordinator.data.get("mixer_circuit", 0) > 0:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.coordinator.data is None:
            return None
        if self.coordinator.data.get("mixer_pump"):
            return HVACAction.HEATING
        if self.coordinator.data.get("mixer_circuit", 0) > 0:
            return HVACAction.IDLE
        return HVACAction.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            if self.coordinator.data and self.coordinator.data.get("floor_day_night", 0) == 1:
                await self.coordinator.client.set_floor_night_temp(int(temp))
            else:
                await self.coordinator.client.set_floor_day_temp(int(temp))
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.client.set_mixer_activation(True)
        else:
            await self.coordinator.client.set_mixer_activation(False)
        await self.coordinator.async_request_refresh()
