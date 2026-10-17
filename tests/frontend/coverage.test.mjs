/**
 * Parameter Coverage Test (1:1 match with physical eCoal controller)
 * Run with: node --test tests/frontend/coverage.test.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";

import { ECOAL_PARAMETERS } from "../../custom_components/ecoal/www/params.js";
import {
  buildReadParamCmd,
  buildWriteParamCmd,
  calcCrc8,
  CRamka,
} from "../../custom_components/ecoal/www/protocol.js";

test("Coverage: All 122 furnace registers are present and valid", () => {
  assert.equal(
    ECOAL_PARAMETERS.length,
    122,
    "Catalog must contain exactly 122 registered eCoal parameters"
  );

  const seenIds = new Set();
  const validGroups = new Set([
    "gr_user",
    "gr_spalanie",
    "gr_zaaw",
    "gr_kalib",
    "gr_krzywa",
    "gr_eth",
    "gr_serwer",
    "schedules",
    "extended",
  ]);

  for (const p of ECOAL_PARAMETERS) {
    assert.ok(p.id >= 0 && p.id <= 133, `Invalid parameter ID: ${p.id}`);
    assert.ok(!seenIds.has(p.id), `Duplicate parameter ID: ${p.id}`);
    seenIds.add(p.id);

    assert.ok(p.key && p.key.startsWith("PARAM_"), `Invalid key: ${p.key}`);
    assert.ok(p.name && p.name.length > 0, `Missing name for ${p.key}`);
    assert.ok(
      validGroups.has(p.group),
      `Invalid group '${p.group}' for ${p.key}`
    );
    assert.ok(p.min <= p.max, `Min (${p.min}) > Max (${p.max}) in ${p.key}`);
  }
});

test("Coverage: Every parameter can generate valid read and write frames", () => {
  for (const p of ECOAL_PARAMETERS) {
    // 1. Read command frame validation
    const readHex = buildReadParamCmd(p.id);
    assert.equal(
      readHex.length,
      20,
      `Read frame for ${p.key} must be 10 bytes (20 hex chars)`
    );

    const readBytes = [];
    for (let i = 0; i < readHex.length; i += 2) {
      readBytes.push(parseInt(readHex.substr(i, 2), 16));
    }
    const readFrame = new CRamka(readBytes);
    assert.equal(
      readFrame.valid,
      true,
      `Generated read frame for ${p.key} must be valid`
    );
    assert.equal(readFrame.cmd1, 1);
    assert.equal(readFrame.cmd3, p.id);

    // 2. Write command frame validation
    const writeHex = buildWriteParamCmd(p.id, p.min);
    assert.equal(
      writeHex.length,
      24,
      `Write frame for ${p.key} must be 12 bytes (24 hex chars)`
    );

    const writeBytes = [];
    for (let i = 0; i < writeHex.length; i += 2) {
      writeBytes.push(parseInt(writeHex.substr(i, 2), 16));
    }
    const writeFrame = new CRamka(writeBytes);
    assert.equal(
      writeFrame.valid,
      true,
      `Generated write frame for ${p.key} must be valid`
    );
    assert.equal(writeFrame.cmd1, 2);
    assert.equal(writeFrame.cmd3, p.id);
    assert.equal(writeFrame.dataLength, 2);
  }
});

test("Coverage: All 34 combustion parameters (gr_spalanie) are present", () => {
  const spalanieParams = ECOAL_PARAMETERS.filter((p) => p.group === "gr_spalanie");
  assert.equal(
    spalanieParams.length,
    34,
    "Must have all 34 combustion tuning parameters"
  );

  // Verify group combustion power steps (8..30 kW)
  const powerKeys = [
    "PARAM_ALG_MOCDMUCH8",
    "PARAM_ALG_MOCDMUCH12",
    "PARAM_ALG_MOCDMUCH16",
    "PARAM_ALG_MOCDMUCH20",
    "PARAM_ALG_MOCDMUCH25",
    "PARAM_ALG_MOCDMUCH30",
    "PARAM_ALG_ILGRUP8",
    "PARAM_ALG_ILGRUP12",
    "PARAM_ALG_ILGRUP16",
    "PARAM_ALG_ILGRUP20",
    "PARAM_ALG_ILGRUP25",
    "PARAM_ALG_ILGRUP30",
  ];
  for (const k of powerKeys) {
    assert.ok(
      spalanieParams.some((p) => p.key === k),
      `Missing power step parameter: ${k}`
    );
  }
});

test("Coverage: All 23 advanced parameters (gr_zaaw) are present", () => {
  const zaawParams = ECOAL_PARAMETERS.filter((p) => p.group === "gr_zaaw");
  assert.equal(
    zaawParams.length,
    23,
    "Must have all 23 advanced parameters from gr_zaaw"
  );

  // Verify key safety and mode parameters
  assert.ok(zaawParams.some((p) => p.key === "PARAM_TYP_PODAJNIKA" && p.id === 119));
  assert.ok(zaawParams.some((p) => p.key === "PARAM_ALG_WYGASZENIA" && p.id === 111));
  assert.ok(zaawParams.some((p) => p.key === "PARAM_CZUJNIK_ZAMZAS" && p.id === 132));
  assert.ok(zaawParams.some((p) => p.key === "PARAM_CZUJNIK_ZERZAW" && p.id === 133));
  assert.ok(zaawParams.some((p) => p.key === "PARAM_PODAJNIK_CZASWYRZUTU" && p.id === 122));
});
