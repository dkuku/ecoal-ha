"""Data update coordinator for eCoal controller."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import SENSOR_NAMES, EcoalClient

_LOGGER = logging.getLogger(__name__)


class EcoalCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls furnace status every 30 seconds."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcoalClient,
        entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="eCoal",
            update_interval=timedelta(seconds=30),
            config_entry=entry,
        )
        self.client = client
        self.firmware_version: str | None = None
        self.connected_sensors: set[str] = set()
        self.hopper_capacity_kg: int = 150
        self.feeder_mode: int | None = None
        self.feeder_max_runtime: int | None = None
        self.dhw_priority: bool | None = None
        self.blower_correction: int | None = None
        self.exhaust_temp_regulator: bool | None = None
        self._extended_refresh_counter: int = 0

    async def async_refresh_extended_params(self) -> None:
        """Read extended furnace configuration parameters."""
        mode = await self.client.get_feeder_mode()
        if mode is not None:
            self.feeder_mode = mode
        max_rt = await self.client.get_feeder_max_runtime()
        if max_rt is not None:
            self.feeder_max_runtime = max_rt
        p_cwu = await self.client.get_dhw_priority()
        if p_cwu is not None:
            self.dhw_priority = p_cwu
        b_corr = await self.client.get_blower_correction()
        if b_corr is not None:
            self.blower_correction = b_corr
        reg_spal = await self.client.get_exhaust_temp_regulator()
        if reg_spal is not None:
            self.exhaust_temp_regulator = reg_spal

    def set_hopper_capacity(self, kg: int) -> None:
        """Update hopper capacity and recalculate fuel remaining kg."""
        self.hopper_capacity_kg = max(1, int(kg))
        if self.data is not None:
            fuel_pct = self.data.get("fuel_load_pct")
            if isinstance(fuel_pct, (int, float)):
                self.data["fuel_remaining_kg"] = round(
                    self.hopper_capacity_kg * min(max(fuel_pct, 0), 100) / 100.0, 1
                )
            self.async_update_listeners()

    async def async_refill_hopper(self, kg: int | None = None) -> bool:
        """Reset feeder runtime counter and record new coal refill (100% hopper)."""
        if kg is None:
            kg = self.hopper_capacity_kg
        success = await self.client.refill_hopper(kg)
        if success:
            await self.async_request_refresh()
        return success

    async def async_set_feeder_mode(self, mode: int) -> bool:
        """Set feeder combustion algorithm and update local state."""
        success = await self.client.set_feeder_mode(mode)
        if success:
            self.feeder_mode = mode
            if self.data is not None:
                self.data["feeder_mode"] = mode
                self.async_update_listeners()
        return success

    async def async_set_feeder_max_runtime(self, minutes: int) -> bool:
        """Set hopper empty alert runtime in minutes and update local state."""
        success = await self.client.set_feeder_max_runtime(minutes)
        if success:
            self.feeder_max_runtime = minutes
            if self.data is not None:
                self.data["feeder_max_runtime"] = minutes
                self.async_update_listeners()
        return success

    async def async_set_dhw_priority(self, on: bool) -> bool:
        """Set DHW priority state and update local state."""
        success = await self.client.set_dhw_priority(on)
        if success:
            self.dhw_priority = on
            if self.data is not None:
                self.data["dhw_priority"] = on
                self.async_update_listeners()
        return success

    async def async_set_blower_correction(self, correction: int) -> bool:
        """Set blower power correction percentage and update local state."""
        success = await self.client.set_blower_correction(correction)
        if success:
            self.blower_correction = correction
            if self.data is not None:
                self.data["blower_correction"] = correction
                self.async_update_listeners()
        return success

    async def async_set_exhaust_temp_regulator(self, on: bool) -> bool:
        """Set exhaust temperature regulator state and update local state."""
        success = await self.client.set_exhaust_temp_regulator(on)
        if success:
            self.exhaust_temp_regulator = on
            if self.data is not None:
                self.data["exhaust_temp_regulator"] = on
                self.async_update_listeners()
        return success

    async def _async_update_data(self) -> dict[str, Any]:
        status = await self.client.get_status()
        if status is None:
            raise UpdateFailed("Failed to get status from furnace")
        if self.firmware_version is None:
            self.firmware_version = await self.client.get_firmware_version()

        self._extended_refresh_counter += 1
        if (
            self.feeder_mode is None
            or self.feeder_max_runtime is None
            or self.dhw_priority is None
            or self.blower_correction is None
            or self.exhaust_temp_regulator is None
            or self._extended_refresh_counter >= 10
        ):
            await self.async_refresh_extended_params()
            self._extended_refresh_counter = 0

        if not self.connected_sensors:
            self.connected_sensors = {
                name for name in SENSOR_NAMES
                if status.get(f"{name}_state", 1) == 0
            }
        fuel_pct = status.get("fuel_load_pct")
        if isinstance(fuel_pct, (int, float)):
            status["fuel_remaining_kg"] = round(
                self.hopper_capacity_kg * min(max(fuel_pct, 0), 100) / 100.0, 1
            )
        else:
            status["fuel_remaining_kg"] = None
        status["feeder_mode"] = self.feeder_mode
        status["feeder_max_runtime"] = self.feeder_max_runtime
        status["dhw_priority"] = self.dhw_priority
        status["blower_correction"] = self.blower_correction
        status["exhaust_temp_regulator"] = self.exhaust_temp_regulator
        return status
