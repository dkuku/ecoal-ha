"""Tests for all eCoal entities (climate, sensor, binary_sensor, switch, button, number, select)."""
from __future__ import annotations

import threading
import time
from typing import Generator

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoal.const import DOMAIN
from tools.mock_furnace import EcoalMockServer


@pytest.fixture
def furnace_server() -> Generator[EcoalMockServer, None, None]:
    """Start virtual furnace simulator on a free localhost port."""
    server = EcoalMockServer(("127.0.0.1", 0), simulate_quirk=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    yield server
    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_all_ecoal_entities(hass: HomeAssistant, furnace_server: EcoalMockServer) -> None:
    """Test full setup, entity state extraction, and service calls."""
    host, port = furnace_server.server_address

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"eCoal ({host}:{port})",
        data={
            CONF_HOST: f"{host}:{port}",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
        unique_id=f"{host}:{port}",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # 1. Test Sensor states
    state_boiler = hass.states.get("sensor.ecoal_boiler_temperature")
    assert state_boiler is not None
    assert float(state_boiler.state) == 58.7

    state_dhw = hass.states.get("sensor.ecoal_dhw_temperature")
    assert state_dhw is not None
    assert float(state_dhw.state) == 48.2

    state_fuel = hass.states.get("sensor.ecoal_fuel_load")
    assert state_fuel is not None
    assert float(state_fuel.state) == 99.0

    state_fuel_kg = hass.states.get("sensor.ecoal_fuel_remaining")
    assert state_fuel_kg is not None
    # 150 kg * 99% = 148.5 kg
    assert float(state_fuel_kg.state) == 148.5

    # 2. Test Binary Sensor states
    state_alarm = hass.states.get("binary_sensor.ecoal_alarm")
    assert state_alarm is not None
    assert state_alarm.state == STATE_OFF

    # 3. Test Climate entities
    state_co_climate = hass.states.get("climate.ecoal_heating")
    assert state_co_climate is not None
    assert state_co_climate.state == HVACMode.HEAT
    assert state_co_climate.attributes["current_temperature"] == 58.7
    assert state_co_climate.attributes["temperature"] == 55.0

    # Test setting target boiler temp via climate
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {ATTR_ENTITY_ID: "climate.ecoal_heating", ATTR_TEMPERATURE: 60},
        blocking=True,
    )
    await hass.async_block_till_done()
    state_co_climate = hass.states.get("climate.ecoal_heating")
    assert state_co_climate.attributes["temperature"] == 60.0

    # 4. Test Switches
    state_ch_pump = hass.states.get("switch.ecoal_ch_pump")
    assert state_ch_pump is not None
    assert state_ch_pump.state == STATE_ON

    # Turn off and on auto mode switch
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.ecoal_auto_mode"},
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.ecoal_auto_mode"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # 5. Test Select entity (feeder mode)
    state_mode = hass.states.get("select.ecoal_feeder_mode")
    assert state_mode is not None
    assert state_mode.state == "retort_group"

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: "select.ecoal_feeder_mode", "option": "retort_ecoal"},
        blocking=True,
    )
    await hass.async_block_till_done()
    state_mode = hass.states.get("select.ecoal_feeder_mode")
    assert state_mode.state == "retort_ecoal"

    state_mixer = hass.states.get("select.ecoal_mixer_circuit_function")
    assert state_mixer is not None
    assert state_mixer.state == "floor"

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: "select.ecoal_mixer_circuit_function", "option": "mixer"},
        blocking=True,
    )
    await hass.async_block_till_done()
    state_mixer = hass.states.get("select.ecoal_mixer_circuit_function")
    assert state_mixer.state == "mixer"

    # 6. Test Number entities
    state_hopper_cap = hass.states.get("number.ecoal_hopper_capacity")
    assert state_hopper_cap is not None
    assert float(state_hopper_cap.state) == 150.0

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: "number.ecoal_hopper_capacity", "value": 200.0},
        blocking=True,
    )
    await hass.async_block_till_done()
    state_hopper_cap = hass.states.get("number.ecoal_hopper_capacity")
    assert float(state_hopper_cap.state) == 200.0

    # 7. Test Button entities
    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: "button.ecoal_refill_hopper_100"},
        blocking=True,
    )
    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: "button.ecoal_acknowledge_alarms"},
        blocking=True,
    )
    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: "button.ecoal_synchronize_clock"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # 8. Test unload entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
