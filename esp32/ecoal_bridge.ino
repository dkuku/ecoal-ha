/**
 * eCoal ESP32 Standalone Web Bridge, OLED Diagnostics & Thermostat Controller
 *
 * Board: WEMOS LOLIN32 with onboard 0.96" SSD1306 OLED
 * - Built-in OLED I2C: SDA=GPIO5, SCL=GPIO4
 * - Continuous adjacent header block:
 *     [GND]   - Common Ground (for MAX3232 and Optocoupler)
 *     [3.3V]  - 3.3V Power for MAX3232 RS-232 module
 *     [TX 15] - Furnace Serial TX (ESP32 TX -> MAX3232 T1IN -> Furnace RxD)
 *     [RX 13] - Furnace Serial RX (ESP32 RX <- MAX3232 R1OUT <- Furnace TxD)
 *     [PIN 12]- Optocoupler Thermostat Output (GPIO 12 -> 1k -> Optocoupler Anode)
 *
 * Features:
 * - Live OLED display with WiFi status, IP, CO/CWU temps, boiler state, and thermostat status.
 * - Rest API (/thermostat) to toggle thermostat from Home Assistant.
 * - Serves complete Svelte SPA Web UI directly from LittleFS.
 * - Autonomous furnace background polling to keep display updated.
 */

#include <WiFi.h>
#include <WebServer.h>
#include <LittleFS.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoOTA.h>
#include <Update.h>

// --- WiFi Configuration ---
const char* WIFI_SSID = "CBA - Woz obserwacyjny";
const char* WIFI_PASS = "frRIsEy7B2Q97J";

// Fallback SoftAP credentials
const char* AP_SSID = "eCoal-Furnace-AP";
const char* AP_PASS = "ecoal1234";

// --- Pinout Configuration ---
#define OLED_SDA_PIN    5
#define OLED_SCL_PIN    4

int furnaceTxPin = 1;    // Pin TX (GPIO 1) -> kocioł (pad 12) - potwierdzone dziala!
int furnaceRxPin = 13;   // Pin RX (GPIO 13) <- kocioł (pad 11 przez dzielnik)
int furnaceBaud = 115200; // eCoal standard is 115200 (older versions 57600)

#define THERMOSTAT_PIN  12   // Pin 12 (GPIO 12) -> Transoptor (Termostat pokojowy)
#define THERMOSTAT_ACTIVE HIGH // HIGH = LED on / contacts closed (grzanie)

#define SCREEN_WIDTH    128
#define SCREEN_HEIGHT   64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
WebServer server(80);

// --- Forward Declarations ---
bool handleStaticFile(String path, const char* contentType = NULL);
void updateDisplay();
void setThermostat(bool state);
void handleSerialDebug();
void handleSwapUart();
void handleSetPins();
void handleScanBaud();
void handleSetCo();

// --- Live State ---
bool thermostatState = false; // false = open (off), true = closed (on)
bool oledReady = false;
bool furnaceConnected = false;
unsigned long lastFurnacePoll = 0;
unsigned long lastDisplayUpdate = 0;

float tempCO = 0.0;
float tempCOTarget = 0.0;
float tempCWU = 0.0;
float tempCWUTarget = 0.0;
uint8_t boilerStatus = 0; // 0=Stop, 1=Grzanie, 2=Podtrzymanie, etc.

// Dallas 1-wire CRC Table for eCoal protocol
const uint8_t CRC_TABLE[256] = {
  0, 49, 98, 83, 196, 245, 166, 151, 185, 136, 219, 234, 125, 76, 31, 46,
  67, 114, 33, 16, 135, 182, 229, 212, 250, 203, 152, 169, 62, 15, 92, 109,
  134, 183, 228, 213, 66, 115, 32, 17, 63, 14, 93, 108, 251, 202, 153, 168,
  197, 244, 167, 150, 1, 48, 99, 82, 124, 77, 30, 47, 184, 137, 218, 235,
  61, 12, 95, 110, 249, 200, 155, 170, 132, 181, 230, 215, 64, 113, 34, 19,
  126, 79, 28, 45, 186, 139, 216, 233, 199, 246, 165, 148, 3, 50, 97, 80,
  187, 138, 217, 232, 127, 78, 29, 44, 2, 51, 96, 81, 198, 247, 164, 149,
  248, 201, 154, 171, 60, 13, 94, 111, 65, 112, 35, 18, 133, 180, 231, 214,
  122, 75, 24, 41, 190, 143, 220, 237, 195, 242, 161, 144, 7, 54, 101, 84,
  57, 8, 91, 106, 253, 204, 159, 174, 128, 177, 226, 211, 68, 117, 38, 23,
  252, 205, 158, 175, 56, 9, 90, 107, 69, 116, 39, 22, 129, 176, 227, 210,
  191, 142, 221, 236, 123, 74, 25, 40, 6, 55, 100, 85, 194, 243, 160, 145,
  71, 118, 37, 20, 131, 178, 225, 208, 254, 207, 156, 173, 58, 11, 88, 105,
  4, 53, 102, 87, 192, 241, 162, 147, 189, 140, 223, 238, 121, 72, 27, 42,
  193, 240, 163, 146, 5, 52, 103, 86, 120, 73, 26, 43, 188, 141, 222, 239,
  130, 179, 224, 209, 70, 119, 36, 21, 59, 10, 89, 104, 255, 206, 157, 172
};

uint8_t hexToByte(char c1, char c2) {
  char str[3] = {c1, c2, 0};
  return (uint8_t)strtol(str, NULL, 16);
}

void setThermostat(bool state) {
  thermostatState = state;
  digitalWrite(THERMOSTAT_PIN, (thermostatState == true) ? THERMOSTAT_ACTIVE : !THERMOSTAT_ACTIVE);
  Serial.printf("[TERMOSTAT] Stan zmieniony na: %s (pin %d = %d)\n",
                thermostatState ? "ON (Zwarty)" : "OFF (Rozwarty)",
                THERMOSTAT_PIN,
                digitalRead(THERMOSTAT_PIN));
  updateDisplay();
}

void parseFurnaceStatus(const uint8_t* buf, size_t len) {
  if (len < 68 || buf[0] != 0x02 || buf[1] != 0x01) return;

  // Temperatures are 16-bit signed little-endian in 0.1°C units
  int16_t rawCO = (int16_t)(buf[10] | (buf[11] << 8));
  int16_t rawCOTarget = (int16_t)(buf[12] | (buf[13] << 8));
  int16_t rawCWU = (int16_t)(buf[14] | (buf[15] << 8));
  int16_t rawCWUTarget = (int16_t)(buf[16] | (buf[17] << 8));

  tempCO = rawCO / 10.0;
  tempCOTarget = rawCOTarget / 10.0;
  tempCWU = rawCWU / 10.0;
  tempCWUTarget = rawCWUTarget / 10.0;

  boilerStatus = buf[26]; // 0=Wylaczony, 1=Grzanie, 2=Podtrzymanie
  furnaceConnected = true;
}

void updateDisplay() {
  if (!oledReady) return;

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  // Line 1: Header + WiFi status
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("eCoal Bridge");

  display.setCursor(80, 0);
  if (WiFi.status() == WL_CONNECTED) {
    display.printf("%ddBm", WiFi.RSSI());
  } else {
    display.print("AP Mode");
  }

  // Line 2: IP Address
  display.setCursor(0, 10);
  if (WiFi.status() == WL_CONNECTED) {
    display.print("IP: ");
    display.print(WiFi.localIP().toString());
  } else {
    display.print("AP: ");
    display.print(WiFi.softAPIP().toString());
  }

  display.drawLine(0, 20, 127, 20, SSD1306_WHITE);

  // Line 3 & 4: Boiler Diagnostics
  if (furnaceConnected) {
    display.setCursor(0, 23);
    display.printf("CO: %.1fC  (Zad:%.0f)", tempCO, tempCOTarget);

    display.setCursor(0, 33);
    display.printf("CWU:%.1fC  (Zad:%.0f)", tempCWU, tempCWUTarget);

    display.setCursor(0, 43);
    display.print("Tryb: ");
    if (boilerStatus == 1) display.print("GRZANIE");
    else if (boilerStatus == 2) display.print("PODTRZYMANIE");
    else if (boilerStatus == 0) display.print("STOP");
    else display.printf("KOD %d", boilerStatus);
  } else {
    display.setCursor(0, 24);
    display.print("UART: Czekam na piec");
    display.setCursor(0, 34);
    display.printf("Piny: TX:%d  RX:%d", furnaceTxPin, furnaceRxPin);
    display.setCursor(0, 44);
    display.printf("Termostat: PIN %d", THERMOSTAT_PIN);
  }

  display.drawLine(0, 52, 127, 52, SSD1306_WHITE);

  // Line 5: Thermostat status (Optocoupler on Pin 12)
  display.setCursor(0, 55);
  display.print("TERMOSTAT: ");
  if (thermostatState) {
    display.print("[ZWARTY/ON]");
  } else {
    display.print("[ROZWARTY]");
  }

  display.display();
}

// Handle GET /?com=<HEX>
void handleComCommand() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Headers", "*");

  if (!server.hasArg("com")) {
    handleStaticFile("/index.html", "text/html");
    return;
  }

  String hexCmd = server.arg("com");
  if (hexCmd.length() < 10 || hexCmd.length() % 2 != 0) {
    server.send(400, "text/plain", "Invalid frame length");
    return;
  }

  size_t sendLen = hexCmd.length() / 2;
  uint8_t sendBuf[256];
  for (size_t i = 0; i < sendLen; i++) {
    sendBuf[i] = hexToByte(hexCmd[i * 2], hexCmd[i * 2 + 1]);
  }

  // Clear serial input buffer
  while (Serial1.available()) Serial1.read();

  // Transmit command frame
  Serial1.write(sendBuf, sendLen);
  Serial1.flush();

  // Read response frame
  uint8_t respBuf[512];
  size_t respLen = 0;
  unsigned long startMs = millis();
  bool stxFound = false;

  while (millis() - startMs < 1000) {
    if (Serial1.available()) {
      uint8_t b = Serial1.read();
      if (!stxFound) {
        if (b == 0x02) {
          stxFound = true;
          respBuf[respLen++] = b;
        }
      } else {
        respBuf[respLen++] = b;
        if (b == 0x03 && respLen >= 10) {
          size_t expectedLen = 10 + (respBuf[6] | (respBuf[7] << 8));
          if (respLen >= expectedLen) break;
        }
      }
      if (respLen >= sizeof(respBuf)) break;
    } else {
      delay(2);
    }
  }

  if (respLen < 10) {
    String err = "Furnace timeout: received " + String(respLen) + " bytes: [";
    for (size_t i = 0; i < respLen; i++) {
      if (i > 0) err += ",";
      err += String(respBuf[i]);
    }
    err += "] on RX=" + String(furnaceRxPin) + ", TX=" + String(furnaceTxPin);
    server.send(504, "text/plain", err);
    return;
  }

  // Intercept and parse status frame for OLED display
  parseFurnaceStatus(respBuf, respLen);
  lastFurnacePoll = millis();

  // Return JSON array to client
  String out = "[";
  for (size_t i = 0; i < respLen; i++) {
    if (i > 0) out += ", ";
    out += String(respBuf[i]);
  }
  out += "]";

  server.send(200, "text/plain", out);
  updateDisplay();
}

// Diagnostic: Raw serial debug endpoint
void handleSerialDebug() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  const uint8_t statusCmd[10] = {0x02, 0x01, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x61, 0x03};

  int rxBefore = digitalRead(furnaceRxPin);
  int txBefore = digitalRead(furnaceTxPin);

  while (Serial1.available()) Serial1.read();
  Serial1.write(statusCmd, sizeof(statusCmd));
  Serial1.flush();

  uint8_t raw[256];
  size_t count = 0;
  unsigned long start = millis();
  while (millis() - start < 1200 && count < sizeof(raw)) {
    if (Serial1.available()) {
      raw[count++] = Serial1.read();
    } else {
      delay(2);
    }
  }

  int rxAfter = digitalRead(furnaceRxPin);

  String json = "{";
  json += "\"tx_pin\":" + String(furnaceTxPin) + ",";
  json += "\"rx_pin\":" + String(furnaceRxPin) + ",";
  json += "\"baud\":" + String(furnaceBaud) + ",";
  json += "\"rx_level_before\":" + String(rxBefore) + ",";
  json += "\"rx_level_after\":" + String(rxAfter) + ",";
  json += "\"tx_level\":" + String(txBefore) + ",";
  json += "\"bytes_count\":" + String(count) + ",";
  json += "\"raw_bytes\":[";
  for (size_t i = 0; i < count; i++) {
    if (i > 0) json += ",";
    json += String(raw[i]);
  }
  json += "]}";
  server.send(200, "application/json", json);
}

// Diagnostic: Voltage and logic level measurement on a pin via /api/voltage?pin=13
void handleVoltage() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  int pin = 13;
  if (server.hasArg("pin")) pin = server.arg("pin").toInt();

  // If measuring furnaceRxPin or furnaceTxPin, temporarily release UART
  bool isUart = (pin == furnaceRxPin || pin == furnaceTxPin);
  if (isUart) {
    Serial1.end();
  }

  pinMode(pin, INPUT);

  // Digital level read
  int initialDig = digitalRead(pin);

  // Sample pin for 50ms to detect toggling or stable DC level
  const int samples = 200;
  int highCount = 0;
  int transitions = 0;
  int lastVal = initialDig;
  for (int i = 0; i < samples; i++) {
    int v = digitalRead(pin);
    if (v == HIGH) highCount++;
    if (v != lastVal) {
      transitions++;
      lastVal = v;
    }
    delayMicroseconds(250);
  }

  // Analog measurement
  uint32_t mv = analogReadMilliVolts(pin);
  int rawAdc = analogRead(pin);

  // Restore UART if needed
  if (isUart) {
    Serial1.begin(furnaceBaud, SERIAL_8N1, furnaceRxPin, furnaceTxPin);
  }

  String json = "{";
  json += "\"pin\":" + String(pin) + ",";
  json += "\"digital\":" + String(initialDig) + ",";
  json += "\"millivolts\":" + String(mv) + ",";
  json += "\"volts\":" + String(mv / 1000.0, 3) + ",";
  json += "\"raw_adc\":" + String(rawAdc) + ",";
  json += "\"samples_high_pct\":" + String((highCount * 100) / samples) + ",";
  json += "\"transitions\":" + String(transitions) + ",";
  json += "\"state\":\"" + String(initialDig == HIGH ? "HIGH" : "LOW") + "\"";
  json += "}";

  server.send(200, "application/json", json);
}

// Diagnostic: Swap RX and TX pins in software
void handleSwapUart() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  int tmp = furnaceRxPin;
  furnaceRxPin = furnaceTxPin;
  furnaceTxPin = tmp;

  Serial1.end();
  Serial1.begin(furnaceBaud, SERIAL_8N1, furnaceRxPin, furnaceTxPin);
  updateDisplay();

  String json = "{\"status\":\"swapped\",\"rx_pin\":" + String(furnaceRxPin) + ",\"tx_pin\":" + String(furnaceTxPin) + ",\"baud\":" + String(furnaceBaud) + "}";
  server.send(200, "application/json", json);
}

// Diagnostic: Reconfigure RX and TX pins and baud dynamically via /api/set_pins?rx=X&tx=Y&baud=Z
void handleSetPins() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  if (server.hasArg("tx")) furnaceTxPin = server.arg("tx").toInt();
  if (server.hasArg("rx")) furnaceRxPin = server.arg("rx").toInt();
  if (server.hasArg("baud")) furnaceBaud = server.arg("baud").toInt();

  Serial1.end();
  Serial1.begin(furnaceBaud, SERIAL_8N1, furnaceRxPin, furnaceTxPin);
  updateDisplay();

  String json = "{\"status\":\"ok\",\"rx_pin\":" + String(furnaceRxPin) + ",\"tx_pin\":" + String(furnaceTxPin) + ",\"baud\":" + String(furnaceBaud) + "}";
  server.send(200, "application/json", json);
}

// Diagnostic: Scan all standard baud rates and pin directions to find furnace
void handleScanBaud() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  const uint8_t statusCmd[10] = {0x02, 0x01, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x61, 0x03};
  const int bauds[] = {115200, 57600, 19200, 9600, 38400};
  const int pinPairs[][2] = {
    {13, 15}, // RX=13, TX=15
    {13, 1},  // RX=13, TX=1
    {15, 13}, // reversed
    {1, 13}   // reversed
  };

  int foundBaud = 0;
  int foundRx = furnaceRxPin;
  int foundTx = furnaceTxPin;
  String logStr = "[";

  bool detected = false;
  for (int p = 0; p < 4 && !detected; p++) {
    int rx = pinPairs[p][0];
    int tx = pinPairs[p][1];

    for (int b = 0; b < 5 && !detected; b++) {
      int testBaud = bauds[b];
      Serial1.end();
      Serial1.begin(testBaud, SERIAL_8N1, rx, tx);
      delay(30);

      while (Serial1.available()) Serial1.read();
      Serial1.write(statusCmd, sizeof(statusCmd));
      Serial1.flush();

      uint8_t buf[256];
      size_t count = 0;
      unsigned long start = millis();
      while (millis() - start < 350 && count < sizeof(buf)) {
        if (Serial1.available()) {
          buf[count++] = Serial1.read();
        } else {
          delay(2);
        }
      }

      if (logStr.length() > 1) logStr += ",";
      logStr += "{\"rx\":" + String(rx) + ",\"tx\":" + String(tx) + ",\"baud\":" + String(testBaud) + ",\"bytes\":" + String(count);
      if (count > 0) {
        logStr += ",\"first_byte\":" + String(buf[0]);
        if (buf[0] == 0x02) {
          foundBaud = testBaud;
          foundRx = rx;
          foundTx = tx;
          detected = true;
          if (count >= 68) {
            parseFurnaceStatus(buf, count);
          }
        }
      }
      logStr += "}";
    }
  }
  logStr += "]";

  if (detected) {
    furnaceBaud = foundBaud;
    furnaceRxPin = foundRx;
    furnaceTxPin = foundTx;
  }
  Serial1.end();
  Serial1.begin(furnaceBaud, SERIAL_8N1, furnaceRxPin, furnaceTxPin);
  updateDisplay();

  String json = "{";
  json += "\"detected\":" + String(detected ? "true" : "false") + ",";
  json += "\"active_baud\":" + String(furnaceBaud) + ",";
  json += "\"active_rx\":" + String(furnaceRxPin) + ",";
  json += "\"active_tx\":" + String(furnaceTxPin) + ",";
  json += "\"scan\":" + logStr;
  json += "}";

  server.send(200, "application/json", json);
}

// Command: Set target boiler CO temperature via /api/set_co?temp=55
void handleSetCo() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  int targetTemp = 55;
  if (server.hasArg("temp")) {
    targetTemp = server.arg("temp").toInt();
  }

  // Parameter 40 (0x28) = CO Zadana
  // Payload: [0x01, 0x00, 0x02, 0x00, 0x28, 0x02, 0x00, val_lo, val_hi]
  uint8_t payload[9] = {
    0x01, 0x00, 0x02, 0x00, 0x28, 0x02, 0x00,
    (uint8_t)(targetTemp & 0xFF),
    (uint8_t)((targetTemp >> 8) & 0xFF)
  };

  uint8_t crc = 0;
  for (size_t i = 0; i < sizeof(payload); i++) {
    crc = CRC_TABLE[crc ^ payload[i]];
  }

  uint8_t frame[12];
  frame[0] = 0x02; // STX
  memcpy(&frame[1], payload, sizeof(payload));
  frame[10] = crc;
  frame[11] = 0x03; // ETX

  // Send to furnace
  while (Serial1.available()) Serial1.read();
  Serial1.write(frame, sizeof(frame));
  Serial1.flush();

  // Read response
  uint8_t resp[64];
  size_t respLen = 0;
  unsigned long start = millis();
  while (millis() - start < 800 && respLen < sizeof(resp)) {
    if (Serial1.available()) {
      resp[respLen++] = Serial1.read();
    } else {
      delay(2);
    }
  }

  tempCOTarget = (float)targetTemp;
  updateDisplay();

  String hexCmd = "";
  for (size_t i = 0; i < sizeof(frame); i++) {
    if (frame[i] < 16) hexCmd += "0";
    hexCmd += String(frame[i], HEX);
  }

  String json = "{";
  json += "\"status\":\"sent\",";
  json += "\"target_co\":" + String(targetTemp) + ",";
  json += "\"frame_hex\":\"" + hexCmd + "\",";
  json += "\"resp_bytes\":" + String(respLen);
  json += "}";

  server.send(200, "application/json", json);
}

// Handle /thermostat REST endpoint
void handleThermostat() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Headers", "*");

  if (server.hasArg("state")) {
    String stateStr = server.arg("state");
    stateStr.toLowerCase();
    if (stateStr == "on" || stateStr == "1" || stateStr == "true") {
      setThermostat(true);
    } else if (stateStr == "off" || stateStr == "0" || stateStr == "false") {
      setThermostat(false);
    } else if (stateStr == "toggle") {
      setThermostat(!thermostatState);
    }
  }

  // Return status JSON
  String json = "{";
  json += "\"state\":\"" + String(thermostatState ? "on" : "off") + "\",";
  json += "\"active\":" + String(thermostatState ? "true" : "false") + ",";
  json += "\"pin\":" + String(THERMOSTAT_PIN);
  json += "}";

  server.send(200, "application/json", json);
}

String getContentType(String path) {
  if (path.endsWith(".html") || path.endsWith(".htm")) return "text/html";
  else if (path.endsWith(".css")) return "text/css";
  else if (path.endsWith(".js") || path.endsWith(".mjs")) return "application/javascript";
  else if (path.endsWith(".json")) return "application/json";
  else if (path.endsWith(".svg")) return "image/svg+xml";
  else if (path.endsWith(".png")) return "image/png";
  else if (path.endsWith(".jpg") || path.endsWith(".jpeg")) return "image/jpeg";
  else if (path.endsWith(".ico")) return "image/x-icon";
  return "text/plain";
}

bool handleStaticFile(String path, const char* contentType) {
  if (path == "/") path = "/index.html";

  int qIdx = path.indexOf('?');
  if (qIdx != -1) path = path.substring(0, qIdx);

  if (LittleFS.exists(path)) {
    File file = LittleFS.open(path, "r");
    server.sendHeader("Access-Control-Allow-Origin", "*");
    String cType = (contentType != NULL) ? String(contentType) : getContentType(path);
    server.streamFile(file, cType.c_str());
    file.close();
    return true;
  }
  return false;
}

void pollFurnaceAutonomous() {
  // Command: Status frame 02010006000000006103
  const uint8_t statusCmd[10] = {0x02, 0x01, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x61, 0x03};

  while (Serial1.available()) Serial1.read();
  Serial1.write(statusCmd, sizeof(statusCmd));
  Serial1.flush();

  uint8_t respBuf[512];
  size_t respLen = 0;
  unsigned long startMs = millis();
  bool stxFound = false;

  while (millis() - startMs < 500) {
    if (Serial1.available()) {
      uint8_t b = Serial1.read();
      if (!stxFound) {
        if (b == 0x02) {
          stxFound = true;
          respBuf[respLen++] = b;
        }
      } else {
        respBuf[respLen++] = b;
        if (b == 0x03 && respLen >= 10) {
          size_t expectedLen = 10 + (respBuf[6] | (respBuf[7] << 8));
          if (respLen >= expectedLen) break;
        }
      }
      if (respLen >= sizeof(respBuf)) break;
    } else {
      delay(2);
    }
  }

  if (respLen >= 68) {
    parseFurnaceStatus(respBuf, respLen);
  } else {
    // Timeout or disconnected
    // Keep previous readings but note timeout
  }
  lastFurnacePoll = millis();
}

void setup() {
  // Setup Optocoupler Pin (Thermostat)
  pinMode(THERMOSTAT_PIN, OUTPUT);
  digitalWrite(THERMOSTAT_PIN, !THERMOSTAT_ACTIVE); // Default: Off / open
  thermostatState = false;

  // Setup OLED Display
  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    oledReady = true;
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 10);
    display.println("eCoal Bridge Start...");
    display.setCursor(0, 25);
    display.println("Laczenie z Wi-Fi...");
    display.display();
  }

  // Initialize LittleFS
  LittleFS.begin(true);

  // Initialize UART to furnace on dedicated pins without Serial.begin conflict
  Serial1.begin(furnaceBaud, SERIAL_8N1, furnaceRxPin, furnaceTxPin);

  // Connect to Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 25) {
    delay(400);
    retries++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
  }

  // Web Server Routes
  server.on("/", HTTP_GET, handleComCommand);
  server.on("/thermostat", HTTP_ANY, handleThermostat);
  server.on("/api/thermostat", HTTP_ANY, handleThermostat);
  server.on("/api/serial_debug", HTTP_ANY, handleSerialDebug);
  server.on("/api/swap_uart", HTTP_ANY, handleSwapUart);
  server.on("/api/set_pins", HTTP_ANY, handleSetPins);
  server.on("/api/scan_baud", HTTP_ANY, handleScanBaud);
  server.on("/api/set_co", HTTP_ANY, handleSetCo);
  server.on("/api/voltage", HTTP_ANY, handleVoltage);

  // OTA Firmware Update Web Routes
  server.on("/update", HTTP_GET, []() {
    server.send(200, "text/html",
      "<html><head><title>eCoal OTA</title></head>"
      "<body style='font-family:sans-serif;background:#1e1e24;color:#eee;text-align:center;padding:40px;'>"
      "<h2>eCoal ESP32 - Aktualizacja OTA</h2>"
      "<form method='POST' action='/update' enctype='multipart/form-data' style='margin-top:20px;'>"
      "<input type='file' name='update' style='margin:10px;'><br>"
      "<input type='submit' value='Wgraj firmware (.bin)' style='padding:10px 24px;background:#00bcd4;border:none;border-radius:4px;color:#fff;font-weight:bold;cursor:pointer;'>"
      "</form></body></html>");
  });
  server.on("/update", HTTP_POST, []() {
    server.sendHeader("Connection", "close");
    server.send(200, "text/plain", (Update.hasError()) ? "BLAD OTA" : "SUKCES! Restartuje ESP32...");
    delay(1000);
    ESP.restart();
  }, []() {
    HTTPUpload& upload = server.upload();
    if (upload.status == UPLOAD_FILE_START) {
      Serial.printf("Start OTA: %s\n", upload.filename.c_str());
      if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
        Update.printError(Serial);
      }
    } else if (upload.status == UPLOAD_FILE_WRITE) {
      if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
        Update.printError(Serial);
      }
    } else if (upload.status == UPLOAD_FILE_END) {
      if (Update.end(true)) {
        Serial.printf("OTA Sukces: %u B\n", upload.totalSize);
      } else {
        Update.printError(Serial);
      }
    }
  });

  server.on("/index.html", HTTP_GET, []() { handleStaticFile("/index.html", "text/html"); });
  server.on("/bundle.js", HTTP_GET, []() { handleStaticFile("/bundle.js", "application/javascript"); });
  server.on("/bundle.css", HTTP_GET, []() { handleStaticFile("/bundle.css", "text/css"); });
  server.on("/style.css", HTTP_GET, []() { handleStaticFile("/style.css", "text/css"); });
  server.on("/app.js", HTTP_GET, []() { handleStaticFile("/app.js", "application/javascript"); });
  server.on("/protocol.js", HTTP_GET, []() { handleStaticFile("/protocol.js", "application/javascript"); });
  server.on("/adapter.js", HTTP_GET, []() { handleStaticFile("/adapter.js", "application/javascript"); });
  server.on("/params.js", HTTP_GET, []() { handleStaticFile("/params.js", "application/javascript"); });

  server.onNotFound([]() {
    if (!handleStaticFile(server.uri())) {
      server.send(404, "text/plain", "File Not Found");
    }
  });

  server.begin();
  Serial.println("HTTP Web Server ready on port 80");

  // Initialize ArduinoOTA
  ArduinoOTA.setHostname("ecoal-bridge");
  ArduinoOTA.begin();
  Serial.println("ArduinoOTA initialized.");

  updateDisplay();
}

void loop() {
  server.handleClient();
  ArduinoOTA.handle();

  // Autonomous status polling every 5 seconds if idle
  if (millis() - lastFurnacePoll > 5000) {
    pollFurnaceAutonomous();
    updateDisplay();
  }

  // Periodic display update every 2 seconds
  if (millis() - lastDisplayUpdate > 2000) {
    lastDisplayUpdate = millis();
    updateDisplay();
  }
}
