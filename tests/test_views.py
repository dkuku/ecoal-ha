"""Tests for eCoal Home Assistant API Views (/api/ecoal/*)."""
from __future__ import annotations

import threading
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ecoal.const import DOMAIN
from custom_components.ecoal.views import (
    async_setup_views,
)
from tools.mock_furnace import EcoalMockServer


@pytest.fixture
def mock_furnace_server():
    server = EcoalMockServer(("127.0.0.1", 0), simulate_quirk=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    yield server
    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_api_ecoal_views(hass: HomeAssistant, hass_client_no_auth, mock_furnace_server) -> None:
    """Test eCoal com proxy, status, and control endpoints."""
    # Setup HTTP component
    await async_setup_component(hass, "http", {})

    host, port = mock_furnace_server.server_address

    # Create mock coordinator and client
    mock_coordinator = MagicMock()
    mock_client = MagicMock()
    mock_coordinator.client = mock_client
    mock_coordinator.hopper_capacity_kg = 150
    mock_coordinator.data = {
        "boiler_temp": 58.7,
        "dhw_temp": 48.2,
        "ch_pump": True,
        "fuel_load_pct": 85,
    }

    mock_client.send_raw_command = AsyncMock(return_value="[2, 1, 6, 0, 1, 4, 0, 50, 0, 35, 0, 65, 0, 50, 0, 123, 3]")
    mock_client.set_target_boiler_temp = AsyncMock(return_value=True)
    mock_client.set_target_dhw_temp = AsyncMock(return_value=True)
    mock_coordinator.async_refill_hopper = AsyncMock(return_value=True)
    mock_coordinator.async_set_mixer_mode = AsyncMock(return_value=True)
    mock_coordinator.async_request_refresh = AsyncMock()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = mock_coordinator

    await async_setup_views(hass)
    client = await hass_client_no_auth()

    # 1. Test GET /api/ecoal/com?com=<HEX>
    resp = await client.get("/api/ecoal/com?com=02010006000000006103")
    assert resp.status == 200
    text = await resp.text()
    assert text.startswith("[") and text.endswith("]")
    mock_client.send_raw_command.assert_awaited_with("02010006000000006103")

    # 2. Test GET /api/ecoal/status
    resp = await client.get("/api/ecoal/status")
    assert resp.status == 200
    data = await resp.json()
    assert data["boiler_temp"] == 58.7
    assert data["ch_pump"] is True

    # 3. Test POST /api/ecoal/control -> set_boiler_temp
    resp = await client.post("/api/ecoal/control", json={"action": "set_boiler_temp", "value": 62})
    assert resp.status == 200
    result = await resp.json()
    assert result == {"success": True}
    mock_client.set_target_boiler_temp.assert_awaited_with(62)

    # 4. Test POST /api/ecoal/control -> refill_hopper
    resp = await client.post("/api/ecoal/control", json={"action": "refill_hopper", "kg": 150})
    assert resp.status == 200
    result = await resp.json()
    assert result == {"success": True}
    mock_coordinator.async_refill_hopper.assert_awaited_with(150)

    # 5. Test POST /api/ecoal/control -> set_mixer_mode
    resp = await client.post("/api/ecoal/control", json={"action": "set_mixer_mode", "value": 1})
    assert resp.status == 200
    result = await resp.json()
    assert result == {"success": True}
    mock_coordinator.async_set_mixer_mode.assert_awaited_with(1)

    # Test POST /api/ecoal/control -> set_room_day_temp & set_room_night_temp
    mock_coordinator.async_set_room_day_temp = AsyncMock(return_value=True)
    mock_coordinator.async_set_room_night_temp = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "set_room_day_temp", "value": 21.5})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_set_room_day_temp.assert_awaited_with(21.5)

    resp = await client.post("/api/ecoal/control", json={"action": "set_room_night_temp", "value": 19.5})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_set_room_night_temp.assert_awaited_with(19.5)

    # 5b. Test POST /api/ecoal/control -> force_co_mode & force_schedule_mode
    mock_coordinator.async_force_co_mode = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "force_co_mode", "lowered": True, "hours": 2})
    assert resp.status == 200
    result = await resp.json()
    assert result == {"success": True}
    mock_coordinator.async_force_co_mode.assert_awaited_with(lowered=True, hours=2)

    mock_coordinator.async_force_schedule_mode = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "force_schedule_mode", "schedule_id": 27, "lowered": False, "hours": 3})
    assert resp.status == 200
    result = await resp.json()
    assert result == {"success": True}
    mock_coordinator.async_force_schedule_mode.assert_awaited_with(schedule_id=27, lowered=False, hours=3)

    # 5c. Test POST /api/ecoal/control -> start_legionella & stop_legionella
    mock_coordinator.async_start_legionella = AsyncMock(return_value=True)
    mock_coordinator.async_stop_legionella = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "start_legionella", "duration": 30, "target_dhw": 60, "target_co": 65})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_start_legionella.assert_awaited_with(target_dhw=60, target_co=65, duration_mins=30)

    resp = await client.post("/api/ecoal/control", json={"action": "stop_legionella"})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_stop_legionella.assert_awaited_with(reason="manual_cancel")

    # 5d. Test POST /api/ecoal/control -> record_cleaning & extinguish
    mock_coordinator.async_record_cleaning = AsyncMock(return_value=True)
    mock_coordinator.async_extinguish_furnace = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "record_cleaning"})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_record_cleaning.assert_awaited_once()

    resp = await client.post("/api/ecoal/control", json={"action": "extinguish"})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_extinguish_furnace.assert_awaited_once()

    # 5e. Test POST /api/ecoal/control -> set_auto_mode & sync_clock
    mock_coordinator.client.set_auto_mode = AsyncMock(return_value=True)
    mock_coordinator.client.sync_clock = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "set_auto_mode", "value": True})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.client.set_auto_mode.assert_awaited_with(True)

    resp = await client.post("/api/ecoal/control", json={"action": "sync_clock"})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.client.sync_clock.assert_awaited_once()

    # 5f. Test POST /api/ecoal/control -> set_room_day_temp & set_room_night_temp
    mock_coordinator.async_set_room_day_temp = AsyncMock(return_value=True)
    mock_coordinator.async_set_room_night_temp = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "set_room_day_temp", "temp": 21.5})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_set_room_day_temp.assert_awaited_with(21.5)

    resp = await client.post("/api/ecoal/control", json={"action": "set_room_night_temp", "temp": 19.0})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_set_room_night_temp.assert_awaited_with(19.0)

    # 5g. Test POST /api/ecoal/control -> set_cleaning_date & set_legionella_date
    mock_coordinator.async_set_cleaning_data = AsyncMock(return_value=True)
    mock_coordinator.async_set_legionella_date = AsyncMock(return_value=True)
    resp = await client.post("/api/ecoal/control", json={"action": "set_cleaning_date", "date": "2026-11-01T12:00:00", "coal_burned_kg": 15.0})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_set_cleaning_data.assert_awaited_with(last_cleaned_at="2026-11-01T12:00:00", coal_burned_kg=15.0)

    resp = await client.post("/api/ecoal/control", json={"action": "set_legionella_date", "date": "2026-11-03T18:30:00"})
    assert resp.status == 200
    assert await resp.json() == {"success": True}
    mock_coordinator.async_set_legionella_date.assert_awaited_with("2026-11-03T18:30:00")

    # 6. Test error cases
    resp = await client.get("/api/ecoal/com")
    assert resp.status == 400

    resp = await client.post("/api/ecoal/control", json={"action": "invalid_action"})
    assert resp.status == 400
