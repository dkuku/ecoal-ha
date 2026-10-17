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
    EcoalComProxyView,
    EcoalControlView,
    EcoalStatusView,
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

    # 5. Test error cases
    resp = await client.get("/api/ecoal/com")
    assert resp.status == 400

    resp = await client.post("/api/ecoal/control", json={"action": "invalid_action"})
    assert resp.status == 400
