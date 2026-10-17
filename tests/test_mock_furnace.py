"""Tests for eCoal Virtual Furnace Simulator (tools/mock_furnace.py)."""
from __future__ import annotations

import threading
import time
from typing import Generator

import aiohttp
import pytest

from custom_components.ecoal.client import (
    CMD_STATUS,
    PARAM_CO_MIN,
    PARAM_CO_ZADANA,
    PARAM_PODAJNIK_CZASALARM,
    PARAM_TYP_PODAJNIKA,
    EcoalClient,
)
from tools.mock_furnace import EcoalMockServer


@pytest.fixture
def mock_server() -> Generator[EcoalMockServer, None, None]:
    """Start mock furnace server in a background thread."""
    server = EcoalMockServer(("127.0.0.1", 0), simulate_quirk=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)  # Allow thread to start
    yield server
    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
async def test_mock_furnace_status(mock_server: EcoalMockServer) -> None:
    """Verify that EcoalClient parses mock furnace status correctly."""
    host, port = mock_server.server_address
    async with aiohttp.ClientSession() as session:
        client = EcoalClient(f"{host}:{port}", "admin", "admin", session=session)

        status = await client.get_status()
        assert status is not None
        assert status["boiler_temp"] == 58.7
        assert status["dhw_temp"] == 48.2
        assert status["exhaust_temp"] == 112.4
        assert status["feeder_temp"] == 28.5
        assert status["ch_pump"] is True
        assert status["dhw_pump"] is False
        assert status["air_pump"] is True
        assert status["heating"] == 1
        assert status["auto_mode"] is True
        assert status["fuel_load_pct"] == 99
        assert status["auth_level"] == 2


@pytest.mark.asyncio
async def test_mock_furnace_param_read_and_write(mock_server: EcoalMockServer) -> None:
    """Verify reading and writing parameters on mock furnace."""
    host, port = mock_server.server_address
    async with aiohttp.ClientSession() as session:
        client = EcoalClient(f"{host}:{port}", "admin", "admin", session=session)

        # 1. Read PARAM_CO_MIN (38)
        p38 = await client.read_param(PARAM_CO_MIN)
        assert p38 is not None
        # [val_l, val_h, min_l, min_h, max_l, max_h, def_l, def_h]
        assert p38[0] == 45  # Value = 45 °C
        assert p38[2] == 42  # Min = 42 °C
        assert p38[4] == 60  # Max = 60 °C

        # 2. Write PARAM_CO_ZADANA (40) -> change to 60 °C
        ok = await client.set_target_boiler_temp(60)
        assert ok is True

        p40 = await client.read_param(PARAM_CO_ZADANA)
        assert p40 is not None
        assert p40[0] == 60

        # 3. Write PARAM_TYP_PODAJNIKA (119) -> change from 1 (grupowe) to 2 (ecoal)
        ok = await client.set_feeder_mode(2)
        assert ok is True

        mode = await client.get_feeder_mode()
        assert mode == 2

        # 4. Refill hopper
        ok = await client.refill_hopper(150)
        assert ok is True

        status = await client.get_status()
        assert status is not None
        assert status["fuel_load_pct"] == 100
        assert status["feeder_runtime"] == 0.0


@pytest.mark.asyncio
async def test_mock_furnace_quirk_simulation() -> None:
    """Verify that simulate_quirk returns Status 21 (NAK) on PARAM >= 96."""
    server = EcoalMockServer(("127.0.0.1", 0), simulate_quirk=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)

    host, port = server.server_address
    try:
        async with aiohttp.ClientSession() as session:
            client = EcoalClient(f"{host}:{port}", "admin", "admin", session=session)

            # PARAM 38 (< 96) returns Status 6 (ACK)
            raw38 = await client._send("0201000100260000e603")
            assert raw38 is not None
            assert raw38[2] == 6  # Status 6 (ACK)

            # PARAM 119 (>= 96) in quirk mode returns Status 21 (NAK) with 2 bytes
            raw119 = await client._send("0201000100770000f603")
            assert raw119 is not None
            assert raw119[2] == 21  # Status 21 (NAK)
            assert raw119[6] == 2   # Len = 2 bytes
    finally:
        server.shutdown()
        server.server_close()
