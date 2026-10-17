/**
 * Svelte Production Bundle Integrity Tests
 * Run with: node --test tests/frontend/bundle.test.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const wwwDir = path.resolve(__dirname, "../../custom_components/ecoal/www");
const esp32DataDir = path.resolve(__dirname, "../../esp32/data");

test("Bundle: Output assets exist and satisfy size requirements", () => {
  const indexHtml = path.join(wwwDir, "index.html");
  const bundleJs = path.join(wwwDir, "bundle.js");
  const bundleCss = path.join(wwwDir, "bundle.css");

  assert.ok(fs.existsSync(indexHtml), "index.html must exist in www");
  assert.ok(fs.existsSync(bundleJs), "bundle.js must exist in www");
  assert.ok(fs.existsSync(bundleCss), "bundle.css must exist in www");

  const htmlContent = fs.readFileSync(indexHtml, "utf-8");
  assert.ok(htmlContent.includes("bundle.js"), "index.html must reference bundle.js");
  assert.ok(htmlContent.includes("bundle.css"), "index.html must reference bundle.css");
  assert.ok(htmlContent.includes('id="app"'), "index.html must have #app root");

  const jsStat = fs.statSync(bundleJs);
  const cssStat = fs.statSync(bundleCss);

  assert.ok(jsStat.size > 20000, "bundle.js should be at least 20 KB");
  assert.ok(jsStat.size < 500000, "bundle.js must be under 500 KB for LittleFS flash");

  assert.ok(cssStat.size > 5000, "bundle.css should be at least 5 KB");
  assert.ok(cssStat.size < 100000, "bundle.css must be under 100 KB");
});

test("Bundle: ESP32 LittleFS data assets are synchronized with www", () => {
  const wwwJs = fs.readFileSync(path.join(wwwDir, "bundle.js"));
  const espJs = fs.readFileSync(path.join(esp32DataDir, "bundle.js"));
  assert.deepEqual(wwwJs, espJs, "ESP32 data/bundle.js must match custom_components/ecoal/www/bundle.js");

  const wwwCss = fs.readFileSync(path.join(wwwDir, "bundle.css"));
  const espCss = fs.readFileSync(path.join(esp32DataDir, "bundle.css"));
  assert.deepEqual(wwwCss, espCss, "ESP32 data/bundle.css must match custom_components/ecoal/www/bundle.css");
});
