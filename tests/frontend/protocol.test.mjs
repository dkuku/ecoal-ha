/**
 * Unit tests for JavaScript eCoal Protocol Engine.
 * Run with: node --test tests/frontend/protocol.test.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  calcCrc8,
  buildStatusCmd,
  buildReadParamCmd,
  buildWriteParamCmd,
  buildRefillHopperCmd,
  buildAckAlarmsCmd,
  CRamka,
  decodeStatusFrame,
} from "../../custom_components/ecoal/www/protocol.js";

test("CRC8 calculation matches eCoal standard", () => {
  // Test CMD_STATUS payload: [ADR=1, Status=0, Cmd1=6, Cmd2=0, Cmd3=0, LenL=0, LenH=0]
  const statusPayload = [0x01, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00];
  const crc = calcCrc8(statusPayload);
  assert.equal(crc, 0x61, "CRC of status command must be 0x61 (97)");

  // Test CMD_SETTINGS payload: [1, 0, 5, 0, 22, 0, 0]
  const settingsPayload = [0x01, 0x00, 0x05, 0x00, 0x16, 0x00, 0x00];
  assert.equal(calcCrc8(settingsPayload), 0x24, "CRC of settings must be 0x24 (36)");
});

test("Command builders produce exact hex frames", () => {
  assert.equal(buildStatusCmd(), "02010006000000006103");
  assert.equal(buildReadParamCmd(38), "0201000100260000e603");
  assert.equal(buildWriteParamCmd(40, 60), "02010002002802003c009103");
  assert.equal(buildRefillHopperCmd(150), "02010005001802009600f903");
});

test("CRamka parses raw frames and validates CRC", () => {
  // Authentic frame from physical furnace
  const rawStatus = [
    2, 1, 6, 6, 0, 0, 76, 0, 1, 0, 0, 0, 0, 0, 0, 0, 205, 8, 209, 0, 79, 0,
    14, 2, 172, 1, 38, 1, 52, 2, 184, 3, 5, 1, 1, 0, 0, 55, 53, 38, 0, 0, 2,
    2, 26, 10, 17, 7, 22, 20, 0, 0, 1, 0, 1, 190, 0, 170, 0, 10, 10, 2, 0, 0,
    199, 6, 0, 0, 26, 10, 16, 23, 12, 162, 39, 95, 6, 0, 210, 0, 190, 0, 0, 0,
    8, 3,
  ];

  const frame = new CRamka(rawStatus);
  assert.equal(frame.valid, true);
  assert.equal(frame.status1, 6);
  assert.equal(frame.cmd1, 6);
  assert.equal(frame.dataLength, 76);
  assert.equal(frame.data.length, 76);
  assert.equal(frame.crcOk, true);
});

test("decodeStatusFrame decodes real physical furnace frame with 100% precision", () => {
  const rawStatus = [
    2, 1, 6, 6, 0, 0, 76, 0, 1, 0, 0, 0, 0, 0, 0, 0, 205, 8, 209, 0, 79, 0,
    14, 2, 172, 1, 38, 1, 52, 2, 184, 3, 5, 1, 1, 0, 0, 55, 53, 38, 0, 0, 2,
    2, 26, 10, 17, 7, 22, 20, 0, 0, 1, 0, 1, 190, 0, 170, 0, 10, 10, 2, 0, 0,
    199, 6, 0, 0, 26, 10, 16, 23, 12, 162, 39, 95, 6, 0, 210, 0, 190, 0, 0, 0,
    8, 3,
  ];

  const status = decodeStatusFrame(rawStatus);
  assert.notEqual(status, null);

  // Temperatures from live physical furnace capture
  assert.equal(status.boiler_temp, 56.4);
  assert.equal(status.dhw_temp, 52.6);
  assert.equal(status.return_temp, 42.8);
  assert.equal(status.feeder_temp, 29.4);
  assert.equal(status.exhaust_temp, 95.2);
  assert.equal(status.indoor_temp, 20.9);
  assert.equal(status.outdoor_temp, 7.9);

  // Outputs (0b00000101 = 5 -> Dmuchawa ON, Podajnik OFF, Pompa CO ON)
  assert.equal(status.air_pump, true);
  assert.equal(status.coal_feeder, false);
  assert.equal(status.ch_pump, true);
  assert.equal(status.dhw_pump, false);

  // States
  assert.equal(status.heating, 1);
  assert.equal(status.auto_mode, true);
  assert.equal(status.target_boiler_temp, 55);
  assert.equal(status.target_dhw_temp, 53);
  assert.equal(status.air_pump_power, 38);

  // Fuel load percentage from live capture (95%)
  assert.equal(status.fuel_load_pct, 95);
  assert.equal(status.auth_level, 2);
});

test("CRamka handles Status 21 (NAK) without throwing", () => {
  // NAK frame for PARAM 119
  const nakFrame = [2, 1, 21, 1, 0, 119, 2, 0, 1, 0, 185, 3];
  const frame = new CRamka(nakFrame);
  assert.equal(frame.status1, 21);
  assert.equal(frame.cmd1, 1);
  assert.equal(frame.cmd3, 119);
  assert.equal(frame.dataLength, 2);
  assert.deepEqual(frame.data, [1, 0]);
  assert.equal(frame.crcOk, true);
  assert.equal(frame.valid, true);
});

test("Weekly programs: decode and encode round-trip with 42 bytes", async () => {
  const { decodeWeeklyProgram, encodeWeeklyProgram, buildWriteProgramCmd } =
    await import("../../custom_components/ecoal/www/protocol.js");

  // Create test days: day 0 has alternating bits, other days all 1s
  const testDays = [
    "101010101010101010101010101010101010101010101010",
    "1".repeat(48),
    "0".repeat(48),
    "1".repeat(48),
    "1".repeat(48),
    "1".repeat(48),
    "1".repeat(48),
  ];

  const encodedBytes = encodeWeeklyProgram(testDays);
  assert.equal(encodedBytes.length, 42, "Encoded schedule must be exactly 42 bytes");

  const decodedDays = decodeWeeklyProgram(encodedBytes);
  assert.equal(decodedDays.length, 7);
  assert.equal(decodedDays[0], testDays[0]);
  assert.equal(decodedDays[1], testDays[1]);
  assert.equal(decodedDays[2], testDays[2]);

  const hexCmd = buildWriteProgramCmd(24, testDays);
  // Frame: STX(1) + ADR(1) + STATUS(1) + CMD1(1) + CMD2(1) + CMD3(1) + LEN(2) + DATA(42) + CRC(1) + ETX(1) = 52 bytes = 104 hex chars
  assert.equal(hexCmd.length, 104);
});
