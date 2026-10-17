/**
 * End-to-End (E2E) Integration Test:
 * Tests the JavaScript EcoalClient and HttpTransportAdapter against the real Python
 * Virtual Furnace Simulator (tools/mock_furnace.py) over HTTP.
 *
 * Run with: node --test tests/frontend/e2e.test.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";

import { EcoalClient, HttpTransportAdapter } from "../../custom_components/ecoal/www/adapter.js";

test("E2E: JavaScript client interacts seamlessly with Python Virtual Furnace over HTTP", async (t) => {
  const port = 8089;
  // Spawn mock furnace python process
  const pythonProc = spawn("python3", ["tools/mock_furnace.py", "--port", String(port)], {
    stdio: "pipe",
  });

  // Wait for server to bind
  await new Promise((resolve) => setTimeout(resolve, 600));

  t.after(() => {
    pythonProc.kill("SIGTERM");
  });

  const client = new EcoalClient(new HttpTransportAdapter(`http://127.0.0.1:${port}`));

  // 1. Get Status
  const status = await client.getStatus();
  assert.notEqual(status, null, "Status must be decoded successfully");
  assert.equal(status.boiler_temp, 58.7);
  assert.equal(status.dhw_temp, 48.2);
  assert.equal(status.ch_pump, true);
  assert.equal(status.dhw_pump, false);
  assert.equal(status.air_pump, true);
  assert.equal(status.fuel_load_pct, 99);

  // 2. Read and Write Boiler Target Temp (PARAM 40)
  const initialParam40 = await client.readParam(40);
  assert.notEqual(initialParam40, null);
  assert.equal(initialParam40[0], 55); // Default 55°C

  const okBoiler = await client.setTargetBoilerTemp(62);
  assert.equal(okBoiler, true);

  const updatedParam40 = await client.readParam(40);
  assert.equal(updatedParam40[0], 62);

  // 3. Read and Write Feeder Mode (PARAM 119)
  const okFeeder = await client.setFeederMode(2); // eCoal mode
  assert.equal(okFeeder, true);

  const p119 = await client.readParam(119);
  assert.equal(p119[0], 2);

  // 4. Refill Hopper (Reset to 100%)
  const okRefill = await client.refillHopper(150);
  assert.equal(okRefill, true);

  const statusAfterRefill = await client.getStatus();
  assert.equal(statusAfterRefill.fuel_load_pct, 100);
  assert.equal(statusAfterRefill.feeder_runtime_sec, 0);

  // 5. Acknowledge Alarms
  const okAck = await client.ackAlarms();
  assert.equal(okAck, true);
});
