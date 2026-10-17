/**
 * eCoal ESP32 Standalone Web Bridge & Controller Firmware
 *
 * Runs on ESP32-C3 or ESP32-S3.
 * - Serves modern SPA Web UI directly from LittleFS flash memory.
 * - Bridges HTTP requests (/?com=<HEX>) to physical furnace UART Serial1 at 19200 8N1.
 * - Compatible with Home Assistant, mobile browsers, and eCoal binary protocol.
 */

#include <WiFi.h>
#include <WebServer.h>
#include <LittleFS.h>

// --- WiFi Configuration ---
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

// Fallback SoftAP credentials if WiFi connection fails
const char* AP_SSID = "eCoal-Furnace-AP";
const char* AP_PASS = "ecoal1234";

// --- UART Pins (Adjust for your specific ESP32 board) ---
// For ESP32-C3: Rx=20, Tx=21
// For ESP32-S3 / standard ESP32: Rx=16, Tx=17 or Rx=18, Tx=19
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  #define UART_RX_PIN 20
  #define UART_TX_PIN 21
#elif defined(CONFIG_IDF_TARGET_ESP32S3)
  #define UART_RX_PIN 18
  #define UART_TX_PIN 17
#else
  #define UART_RX_PIN 16
  #define UART_TX_PIN 17
#endif

#define FURNACE_BAUD 19200

WebServer server(80);

// Dallas 1-wire CRC Table for eCoal protocol verification
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

uint8_t calcCrc8(const uint8_t* data, size_t len) {
  uint8_t crc = 0;
  for (size_t i = 0; i < len; i++) {
    crc = CRC_TABLE[crc ^ data[i]];
  }
  return crc;
}

// Convert 2 hex chars to byte
uint8_t hexToByte(char c1, char c2) {
  char str[3] = {c1, c2, 0};
  return (uint8_t)strtol(str, NULL, 16);
}

// Handle GET /?com=<HEX> - Forward command to UART and return response array
void handleComCommand() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Headers", "*");

  if (!server.hasArg("com")) {
    // If no com argument, serve index.html
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

  // Clear serial input buffer before sending
  while (Serial1.available()) {
    Serial1.read();
  }

  // Transmit command frame to furnace
  Serial1.write(sendBuf, sendLen);
  Serial1.flush();

  // Read response frame with timeout
  uint8_t respBuf[512];
  size_t respLen = 0;
  unsigned long startMs = millis();
  bool stxFound = false;

  while (millis() - startMs < 600) {
    if (Serial1.available()) {
      uint8_t b = Serial1.read();
      if (!stxFound) {
        if (b == 0x02) { // STX
          stxFound = true;
          respBuf[respLen++] = b;
        }
      } else {
        respBuf[respLen++] = b;
        // Check if ETX (0x03) received and length is adequate
        if (b == 0x03 && respLen >= 10) {
          // Check if dataLength matches
          size_t expectedLen = 10 + (respBuf[6] | (respBuf[7] << 8));
          if (respLen >= expectedLen) {
            break;
          }
        }
      }
      if (respLen >= sizeof(respBuf)) break;
    } else {
      delay(2);
    }
  }

  if (respLen < 10) {
    server.send(504, "text/plain", "Furnace timeout or no response");
    return;
  }

  // Format as JSON array: [2, 1, 6, 0, ...]
  String out = "[";
  for (size_t i = 0; i < respLen; i++) {
    if (i > 0) out += ", ";
    out += String(respBuf[i]);
  }
  out += "]";

  server.send(200, "text/plain", out);
}

// Serve static files from LittleFS
bool handleStaticFile(String path, const char* contentType) {
  if (path == "/") path = "/index.html";

  if (LittleFS.exists(path)) {
    File file = LittleFS.open(path, "r");
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.streamFile(file, contentType);
    file.close();
    return true;
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== eCoal ESP32 Bridge Starting ===");

  // Initialize LittleFS
  if (!LittleFS.begin(true)) {
    Serial.println("LittleFS mount failed!");
  } else {
    Serial.println("LittleFS mounted successfully.");
  }

  // Initialize UART to furnace
  Serial1.begin(FURNACE_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
  Serial.printf("Furnace UART initialized on Rx=%d, Tx=%d at %d baud\n",
                UART_RX_PIN, UART_TX_PIN, FURNACE_BAUD);

  // Connect to Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWi-Fi connected!");
    Serial.print("IP Address: http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWi-Fi connection failed. Starting SoftAP fallback...");
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.print("SoftAP IP Address: http://");
    Serial.println(WiFi.softAPIP());
  }

  // Web Server Routes
  server.on("/", HTTP_GET, handleComCommand);
  server.on("/index.html", HTTP_GET, []() { handleStaticFile("/index.html", "text/html"); });
  server.on("/style.css", HTTP_GET, []() { handleStaticFile("/style.css", "text/css"); });
  server.on("/app.js", HTTP_GET, []() { handleStaticFile("/app.js", "application/javascript"); });
  server.on("/protocol.js", HTTP_GET, []() { handleStaticFile("/protocol.js", "application/javascript"); });
  server.on("/adapter.js", HTTP_GET, []() { handleStaticFile("/adapter.js", "application/javascript"); });
  server.on("/params.js", HTTP_GET, []() { handleStaticFile("/params.js", "application/javascript"); });

  server.onNotFound([]() {
    if (!handleStaticFile(server.uri(), "text/plain")) {
      server.send(404, "text/plain", "File Not Found");
    }
  });

  server.begin();
  Serial.println("HTTP Web Server ready on port 80");
}

void loop() {
  server.handleClient();
}
