"""Data update coordinator for eCoal controller."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import PARAM_PROG_CO_TAB, SENSOR_NAMES, EcoalClient

_LOGGER = logging.getLogger(__name__)

MAINTENANCE_STORAGE_KEY = "ecoal_maintenance"
MAINTENANCE_STORAGE_VERSION = 1


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
        self.hopper_capacity_kg: int = 100
        self.feeder_mode: int | None = None
        self.feeder_max_runtime: int | None = None
        self.dhw_priority: bool | None = None
        self.blower_correction: int | None = None
        self.exhaust_temp_regulator: bool | None = None
        self._extended_refresh_counter: int = 0
        self._legionella_task: asyncio.Task | None = None
        self._legionella_state: dict[str, Any] = {
            "active": False,
            "phase": "idle",
            "target_temp": 60,
            "boiler_target": 65,
            "holding_duration": 1800,
            "holding_seconds_left": 1800,
            "total_elapsed": 0,
            "started_at": None,
            "last_run": None,
            "saved_co_target": None,
            "saved_dhw_target": None,
        }
        self._maintenance_store = Store[dict[str, Any]](
            hass, MAINTENANCE_STORAGE_VERSION, MAINTENANCE_STORAGE_KEY
        )
        self._maintenance_data: dict[str, Any] = {
            "last_cleaned_at": datetime.now().isoformat(),
            "feeder_runtime_at_cleaning": 0.0,
            "coal_burned_since_cleaning_kg": 0.0,
            "days_since_cleaning": 0,
            "heating_rate_c_per_min": None,
            "avg_exhaust_heating": None,
            "cleaning_required": False,
            "cleaning_warning_reason": None,
        }
        self._maintenance_loaded: bool = False
        self._last_heating_ts: float | None = None
        self._last_boiler_temp: float | None = None
        self._exhaust_heating_samples: list[float] = []

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
    async def async_set_mixer_mode(self, mode: int) -> bool:
        """Set mixer circuit mode (0=disabled, 1=mixer/CO, 2=floor)."""
        success = await self.client.set_mixer_mode(mode)
        if success:
            if self.data is not None:
                self.data["mixer_circuit"] = mode
                self.async_update_listeners()
            await self.async_request_refresh()
        return success

    async def async_force_co_mode(self, lowered: bool, hours: int = 2) -> bool:
        """Force lowered ('0') or comfort ('1') mode in CO weekly schedule for next hours."""
        schedule = await self.client.get_weekly_program(PARAM_PROG_CO_TAB)
        if not schedule or len(schedule) != 7:
            return False

        now = datetime.now()
        data = self.data or {}
        ctrl_dt = data.get("controller_datetime")
        if ctrl_dt:
            try:
                now = datetime.fromisoformat(ctrl_dt)
            except Exception:
                pass

        # eCoal weekly program day: 0=Sunday, 1=Monday, ..., 6=Saturday
        day_idx = (now.weekday() + 1) % 7
        slot_idx = now.hour * 2 + (1 if now.minute >= 30 else 0)
        target_bit = "0" if lowered else "1"

        days_copy = list(schedule)
        total_slots = max(1, hours * 2)
        for offset in range(total_slots):
            cur_slot = slot_idx + offset
            cur_day = (day_idx + (cur_slot // 48)) % 7
            cur_slot = cur_slot % 48

            day_str = days_copy[cur_day]
            chars = list(day_str)
            chars[cur_slot] = target_bit
            days_copy[cur_day] = "".join(chars)

        success = await self.client.set_weekly_program(PARAM_PROG_CO_TAB, days_copy)
        if success:
            await self.async_request_refresh()
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
        status["legionella"] = dict(self._legionella_state)

        # 1. Maintenance & Cleaning Tracker
        if not self._maintenance_loaded:
            try:
                stored = await self._maintenance_store.async_load()
                if stored and isinstance(stored, dict):
                    self._maintenance_data.update(stored)
            except Exception as err:
                _LOGGER.debug("Could not load maintenance data from store: %s", err)
            self._maintenance_loaded = True

        current_feeder_min = status.get("feeder_runtime_min")
        if current_feeder_min is None:
            fr_raw = status.get("feeder_runtime", 0)
            current_feeder_min = (fr_raw / 60.0) if fr_raw else 0.0

        base_feeder_min = float(self._maintenance_data.get("feeder_runtime_at_cleaning", 0.0) or 0.0)
        burned = max(0.0, round((current_feeder_min - base_feeder_min) * 0.3666, 1))
        self._maintenance_data["coal_burned_since_cleaning_kg"] = burned

        last_cleaned_str = self._maintenance_data.get("last_cleaned_at")
        days = 0
        if last_cleaned_str:
            try:
                dt_clean = datetime.fromisoformat(last_cleaned_str)
                days = max(0, (datetime.now() - dt_clean).days)
            except Exception:
                pass
        self._maintenance_data["days_since_cleaning"] = days

        # Heating rate calculation during active heating (heating == 1)
        is_heating = bool(status.get("heating") == 1 or status.get("heating") is True)
        b_temp = status.get("boiler_temp")
        now_ts = datetime.now().timestamp()

        if is_heating and isinstance(b_temp, (int, float)):
            ex_temp = status.get("exhaust_temp")
            if isinstance(ex_temp, (int, float)) and ex_temp > 40:
                self._exhaust_heating_samples.append(float(ex_temp))
                if len(self._exhaust_heating_samples) > 20:
                    self._exhaust_heating_samples.pop(0)
                self._maintenance_data["avg_exhaust_heating"] = round(
                    sum(self._exhaust_heating_samples) / len(self._exhaust_heating_samples), 1
                )

            if self._last_heating_ts is not None and self._last_boiler_temp is not None:
                delta_sec = now_ts - self._last_heating_ts
                if 20 <= delta_sec <= 180:
                    delta_t = b_temp - self._last_boiler_temp
                    if delta_t > 0:
                        rate = round((delta_t / delta_sec) * 60.0, 2)
                        self._maintenance_data["heating_rate_c_per_min"] = rate
            self._last_heating_ts = now_ts
            self._last_boiler_temp = b_temp
        else:
            self._last_heating_ts = None
            self._last_boiler_temp = None

        # Cleaning warning evaluation
        reasons = []
        avg_ex = self._maintenance_data.get("avg_exhaust_heating")
        if avg_ex and avg_ex > 135.0:
            reasons.append(f"Wysoka temp. spalin ({avg_ex}°C > 135°C)")
        if burned > 200.0:
            reasons.append(f"Spalono {burned} kg węgla (> 200 kg)")
        if days >= 25:
            reasons.append(f"{days} dni od czyszczenia kotła")
        hrate = self._maintenance_data.get("heating_rate_c_per_min")
        if hrate is not None and hrate < 0.20 and burned > 50.0:
            reasons.append(f"Niska prędkość grzania ({hrate}°C/min)")

        self._maintenance_data["cleaning_required"] = len(reasons) > 0
        self._maintenance_data["cleaning_warning_reason"] = " | ".join(reasons) if reasons else None

        status["maintenance"] = dict(self._maintenance_data)
        status["coal_burned_since_cleaning_kg"] = burned
        status["days_since_cleaning"] = days
        status["heating_rate_c_per_min"] = self._maintenance_data.get("heating_rate_c_per_min")
        status["cleaning_required"] = self._maintenance_data["cleaning_required"]
        status["cleaning_warning_reason"] = self._maintenance_data["cleaning_warning_reason"]

        # 2. Cool-down pump cutoff protection when in Manual mode / Extinguished:
        if status.get("auto_mode") is False:
            if isinstance(b_temp, (int, float)) and b_temp < 40.0:
                if status.get("ch_pump") is True:
                    _LOGGER.info(
                        "Boiler in manual mode cooled to %s°C (< 40°C). Automatically cutting off CH pump.",
                        b_temp,
                    )
                    await self.client.set_switch(0x0D, False)
                    status["ch_pump"] = False
                if status.get("dhw_pump") is True:
                    _LOGGER.info(
                        "Boiler in manual mode cooled to %s°C (< 40°C). Automatically cutting off DHW pump.",
                        b_temp,
                    )
                    await self.client.set_switch(0x0E, False)
                    status["dhw_pump"] = False

        return status

    @property
    def legionella_active(self) -> bool:
        """Return True if anti-legionella disinfection is in progress."""
        return bool(self._legionella_state.get("active", False))

    @property
    def legionella_state(self) -> dict[str, Any]:
        """Return anti-legionella cycle state."""
        return self._legionella_state

    async def async_start_legionella(
        self,
        target_dhw: int = 60,
        target_co: int = 65,
        duration_mins: int = 30,
    ) -> bool:
        """Start anti-legionella thermal disinfection routine."""
        if self._legionella_state.get("active"):
            return True

        saved_co = None
        saved_dhw = None
        if self.data:
            saved_co = self.data.get("target_boiler_temp")
            saved_dhw = self.data.get("target_dhw_temp")

        if saved_co is None:
            saved_co = 53
        if saved_dhw is None:
            saved_dhw = 50

        # Set higher temperatures: boiler 65°C, DHW 60°C
        ok_co = await self.client.set_target_boiler_temp(target_co)
        ok_dhw = await self.client.set_target_dhw_temp(target_dhw)

        if not (ok_co and ok_dhw):
            _LOGGER.error(
                "Failed to set anti-legionella target temperatures (CO: %s, CWU: %s)",
                target_co,
                target_dhw,
            )
            return False

        # If furnace in manual mode, turn on auto mode
        if self.data and self.data.get("auto_mode") is False:
            await self.client.set_auto_mode(True)

        holding_sec = max(60, int(duration_mins * 60))
        self._legionella_state = {
            "active": True,
            "phase": "heating",
            "target_temp": target_dhw,
            "boiler_target": target_co,
            "holding_duration": holding_sec,
            "holding_seconds_left": holding_sec,
            "total_elapsed": 0,
            "started_at": datetime.now().isoformat(),
            "last_run": self._legionella_state.get("last_run"),
            "saved_co_target": saved_co,
            "saved_dhw_target": saved_dhw,
        }
        if self.data is not None:
            self.data["legionella"] = dict(self._legionella_state)
            self.async_update_listeners()

        if self._legionella_task and not self._legionella_task.done():
            self._legionella_task.cancel()
        self._legionella_task = self.hass.async_create_background_task(
            self._async_legionella_loop(),
            name="ecoal_anti_legionella_loop",
        )
        return True

    async def async_stop_legionella(self, reason: str = "manual_cancel") -> bool:
        """Stop anti-legionella thermal disinfection and restore original setpoints."""
        if self._legionella_task and not self._legionella_task.done():
            self._legionella_task.cancel()
            self._legionella_task = None

        saved_co = self._legionella_state.get("saved_co_target")
        saved_dhw = self._legionella_state.get("saved_dhw_target")

        if saved_co is not None:
            await self.client.set_target_boiler_temp(saved_co)
        if saved_dhw is not None:
            await self.client.set_target_dhw_temp(saved_dhw)

        last_run = self._legionella_state.get("last_run")
        if reason == "completed":
            last_run = datetime.now().isoformat()

        self._legionella_state = {
            "active": False,
            "phase": "completed" if reason == "completed" else "idle",
            "target_temp": 60,
            "boiler_target": 65,
            "holding_duration": 1800,
            "holding_seconds_left": 0 if reason == "completed" else 1800,
            "total_elapsed": self._legionella_state.get("total_elapsed", 0),
            "started_at": None,
            "last_run": last_run,
            "saved_co_target": None,
            "saved_dhw_target": None,
        }
        if self.data is not None:
            self.data["legionella"] = dict(self._legionella_state)
            self.async_update_listeners()
            await self.async_request_refresh()
        return True

    async def _async_legionella_loop(self) -> None:
        """Background monitoring loop for thermal disinfection."""
        max_timeout_sec = 7200  # 2 hours max safety timeout
        poll_interval = 2
        try:
            while self._legionella_state.get("active"):
                await asyncio.sleep(poll_interval)
                self._legionella_state["total_elapsed"] += poll_interval

                cur_dhw = 0.0
                if self.data:
                    cur_dhw = float(self.data.get("dhw_temp", 0.0) or 0.0)

                phase = self._legionella_state.get("phase")

                # Phase 1: Heating up towards target (58.0°C threshold for holding)
                if phase == "heating":
                    if cur_dhw >= (self._legionella_state["target_temp"] - 2.0):
                        self._legionella_state["phase"] = "holding"
                        _LOGGER.info(
                            "eCoal anti-legionella: DHW reached %s°C, holding countdown started (%ss)",
                            cur_dhw,
                            self._legionella_state["holding_seconds_left"],
                        )
                    elif self._legionella_state["total_elapsed"] >= max_timeout_sec:
                        _LOGGER.warning(
                            "eCoal anti-legionella: Max timeout (2h) reached without attaining 58°C. Aborting."
                        )
                        await self.async_stop_legionella(reason="timeout")
                        break

                # Phase 2: Holding disinfection temperature
                elif phase == "holding":
                    self._legionella_state["holding_seconds_left"] -= poll_interval
                    if self._legionella_state["holding_seconds_left"] <= 0:
                        _LOGGER.info("eCoal anti-legionella: Disinfection cycle successfully finished!")
                        await self.async_stop_legionella(reason="completed")
                        break

                # Notify listeners
                if self.data is not None:
                    self.data["legionella"] = dict(self._legionella_state)
                    self.async_update_listeners()

        except asyncio.CancelledError:
            pass
        except Exception as err:
            _LOGGER.exception("Error in anti-legionella monitoring loop: %s", err)
            await self.async_stop_legionella(reason="error")

    async def async_record_cleaning(self) -> bool:
        """Record boiler cleaning event, reset coal counter and clear warnings."""
        current_feeder_min = 0.0
        if self.data:
            current_feeder_min = self.data.get("feeder_runtime_min") or (
                self.data.get("feeder_runtime", 0) / 60.0
            )
        self._maintenance_data = {
            "last_cleaned_at": datetime.now().isoformat(),
            "feeder_runtime_at_cleaning": current_feeder_min,
            "coal_burned_since_cleaning_kg": 0.0,
            "days_since_cleaning": 0,
            "heating_rate_c_per_min": None,
            "avg_exhaust_heating": None,
            "cleaning_required": False,
            "cleaning_warning_reason": None,
        }
        self._exhaust_heating_samples.clear()
        try:
            await self._maintenance_store.async_save(self._maintenance_data)
        except Exception as err:
            _LOGGER.warning("Could not persist maintenance data: %s", err)

        if self.data is not None:
            self.data["maintenance"] = dict(self._maintenance_data)
            self.data["coal_burned_since_cleaning_kg"] = 0.0
            self.data["days_since_cleaning"] = 0
            self.data["cleaning_required"] = False
            self.data["cleaning_warning_reason"] = None
            self.async_update_listeners()
            await self.async_request_refresh()
        return True

    async def async_extinguish_furnace(self) -> bool:
        """Safely extinguish the furnace: stop auto mode, blower, feeder, and protect pumps."""
        _LOGGER.info("Initiating safe furnace extinguishing sequence")
        # 1. Turn off auto mode
        ok = await self.client.set_auto_mode(False)
        # 2. Stop blower (OUT_DMUCHAWA 0x0B) and feeder (OUT_PODAJNIK 0x0C)
        await self.client.set_switch(0x0B, False)
        await self.client.set_switch(0x0C, False)

        # 3. Check boiler temperature:
        b_temp = self.data.get("boiler_temp") if self.data else None
        if isinstance(b_temp, (int, float)) and b_temp < 40.0:
            await self.client.set_switch(0x0D, False)  # OUT_POMPA_CO
            await self.client.set_switch(0x0E, False)  # OUT_POMPA_CWU
        # If boiler is >= 40.0°C, CH pump stays running to safely absorb heat,
        # and will automatically be cut off in _async_update_data once it drops below 40°C.
        await self.async_request_refresh()
        return ok
