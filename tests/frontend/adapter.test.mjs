/**
 * Unit tests for JavaScript Transport Adapters and EcoalClient.
 * Run with: node --test tests/frontend/adapter.test.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  EcoalClient,
  MockTransportAdapter,
  HttpTransportAdapter,
} from "../../custom_components/ecoal/www/adapter.js";

test("EcoalClient works with MockTransportAdapter", async () => {
  const mockAdapter = new MockTransportAdapter(58.5, 48.0);
  const client = new EcoalClient(mockAdapter);

  // Read status
  const status = await client.getStatus();
  assert.notEqual(status, null);
  assert.equal(status.boiler_temp, 58.5);
  assert.equal(status.dhw_temp, 48.0);
  assert.equal(status.ch_pump, true);
  assert.equal(status.auto_mode, true);
  assert.equal(status.fuel_load_pct, 99);

  // Set target boiler temperature to 62
  const ok1 = await client.setTargetBoilerTemp(62);
  assert.equal(ok1, true);

  // Set feeder mode to 2 (eCoal)
  const ok2 = await client.setFeederMode(2);
  assert.equal(ok2, true);

  // Refill hopper
  const ok3 = await client.refillHopper(150);
  assert.equal(ok3, true);

  // Verify updated status
  const updated = await client.getStatus();
  assert.equal(updated.boiler_temp, 62);
  assert.equal(updated.fuel_load_pct, 100);
});

test("EcoalClient allows switching adapters seamlessly", async () => {
  const client = new EcoalClient(new MockTransportAdapter(50.0, 40.0));
  const s1 = await client.getStatus();
  assert.equal(s1.boiler_temp, 50.0);

  // Switch to another adapter instance
  client.setAdapter(new MockTransportAdapter(65.0, 45.0));
  const s2 = await client.getStatus();
  assert.equal(s2.boiler_temp, 65.0);
});
