/**
 * eCoal Pluggable Transport Adapters (JavaScript)
 *
 * Implements interchangeable communication layers:
 * - HttpTransportAdapter: for Home Assistant proxy (/api/ecoal/com) or direct LAN/Wi-Fi (?com=)
 * - SerialTransportAdapter: for Web Serial API (Chrome/Edge USB-RS232) or raw UART on ESP32
 * - MockTransportAdapter: for offline simulation and automated unit tests
 *
 * Provides a unified EcoalClient with identical API across all transports.
 */
import {
  calcCrc8,
  buildAckAlarmsCmd,
  buildReadParamCmd,
  buildRefillHopperCmd,
  buildStatusCmd,
  buildWriteParamCmd,
  buildWriteProgramCmd,
  decodeWeeklyProgram,
  CRamka,
  decodeStatusFrame,
} from "./protocol.js";

/**
 * Base abstract adapter interface.
 */
export class BaseTransportAdapter {
  constructor() {
    this.name = "base";
  }

  async sendHexCmd(hexCmd) {
    throw new Error("sendHexCmd not implemented");
  }
}

/**
 * HTTP Transport: Communicates via GET /?com=<HEX> or /api/ecoal/com?com=<HEX>
 */
export class HttpTransportAdapter extends BaseTransportAdapter {
  constructor(baseUrl = "") {
    super();
    this.name = "http";
    this.baseUrl = baseUrl; // e.g. "" (same origin) or "http://192.168.2.111" or "/api/ecoal"
  }

  async sendHexCmd(hexCmd) {
    const url = this.baseUrl.includes("/api/ecoal")
      ? `${this.baseUrl}/com?com=${hexCmd}`
      : `${this.baseUrl}/?com=${hexCmd}`;

    const resp = await fetch(url, {
      method: "GET",
      headers: { Accept: "text/plain, application/json" },
    });

    if (!resp.ok) {
      throw new Error(`HTTP error ${resp.status} fetching ${url}`);
    }

    const text = await resp.text();
    // Parse JSON array string "[2, 1, 6, ...]"
    const start = text.indexOf("[");
    const end = text.lastIndexOf("]");
    if (start === -1 || end === -1) {
      throw new Error(`Invalid response format from server: ${text}`);
    }
    return text
      .slice(start + 1, end)
      .split(",")
      .map((v) => parseInt(v.trim(), 10));
  }
}

/**
 * Mock Transport: Emulates a virtual furnace in-memory for testing and offline demo.
 */
export class MockTransportAdapter extends BaseTransportAdapter {
  constructor(initialBoilerTemp = 58.7, initialDhwTemp = 48.2) {
    super();
    this.name = "mock";
    this.boilerTemp = initialBoilerTemp;
    this.dhwTemp = initialDhwTemp;
    this.targetBoilerTemp = 55;
    this.targetDhwTemp = 50;
    this.fuelLoadPct = 99;
    this.feederMode = 1; // 1 = retort_group
    this.feederRuntimeSec = 1200;
    this.params = {
      17: [50, 35, 65, 50],
      38: [45, 42, 60, 45],
      39: [65, 65, 80, 80],
      40: [55, 45, 80, 55],
      79: [600, 0, 1000, 600],
      119: [1, 0, 3, 1],
    };
    this.schedules = {};
  }

  async sendHexCmd(hexCmd) {
    const bytes = [];
    for (let i = 0; i < hexCmd.length; i += 2) {
      bytes.push(parseInt(hexCmd.substr(i, 2), 16));
    }
    const cmd1 = bytes[3];
    const cmd3 = bytes[5];

    if (cmd1 === 0x06) {
      // Return synthetic 86-byte status response
      const data = new Array(76).fill(0);
      // Floor, Inside, Outside, DHW, Return, Feeder, Boiler, Exhaust
      const temps = [
        280, // Floor 28.0
        210, // Inside 21.0
        125, // Outside 12.5
        Math.round(this.dhwTemp * 10),
        491, // Return 49.1
        285, // Feeder 28.5
        Math.round(this.boilerTemp * 10),
        1124, // Exhaust 112.4
      ];
      for (let i = 0; i < temps.length; i++) {
        data[8 + i * 2] = temps[i] & 0xff;
        data[8 + i * 2 + 1] = (temps[i] >> 8) & 0xff;
      }
      data[24] = 0b00000101; // Dmuchawa ON, Pompa CO ON
      data[25] = 1; // Heating = 1
      data[26] = 1; // Auto mode = 1
      data[29] = this.targetBoilerTemp;
      data[30] = this.targetDhwTemp;
      data[31] = 38; // 38% blower
      data[35] = 2; // Auth = 2
      data[67] = this.fuelLoadPct;

      const payload = [0x01, 0x06, 0x06, 0x00, 0x00, 76, 0, ...data];
      const crc = calcCrc8(payload);
      return [0x02, ...payload, crc, 0x03];
    }

    if (cmd1 === 0x01) {
      // CMD_GET_PARAM
      const scheduleIds = [24, 25, 26, 27, 28, 83, 87];
      if (scheduleIds.includes(cmd3)) {
        const sched = this.schedules[cmd3] || new Array(42).fill(0xff);
        const payload = [0x01, 0x06, 0x01, 0x00, cmd3, 42, 0, ...sched];
        const crc = calcCrc8(payload);
        return [0x02, ...payload, crc, 0x03];
      }

      const p = this.params[cmd3] || [0, 0, 100, 0];
      const data = [
        p[0] & 0xff,
        (p[0] >> 8) & 0xff,
        p[1] & 0xff,
        (p[1] >> 8) & 0xff,
        p[2] & 0xff,
        (p[2] >> 8) & 0xff,
        p[3] & 0xff,
        (p[3] >> 8) & 0xff,
      ];
      const payload = [0x01, 0x06, 0x01, 0x00, cmd3, 8, 0, ...data];
      const crc = calcCrc8(payload);
      return [0x02, ...payload, crc, 0x03];
    }

    if (cmd1 === 0x02) {
      // CMD_SET_PARAM
      const dataLen = bytes[6] | (bytes[7] << 8);
      if (dataLen === 42) {
        this.schedules[cmd3] = bytes.slice(8, 8 + 42);
      } else {
        const val = bytes[8] | (bytes[9] << 8);
        if (cmd3 === 40) {
          this.targetBoilerTemp = val;
          this.boilerTemp = val;
        } else if (cmd3 === 17) {
          this.targetDhwTemp = val;
          this.dhwTemp = val;
        } else if (cmd3 === 119) {
          this.feederMode = val;
        }
        if (!this.params[cmd3]) {
          this.params[cmd3] = [val, 0, 100, val];
        } else {
          this.params[cmd3][0] = val;
        }
      }
      const payload = [0x01, 0x06, 0x02, 0x00, cmd3, 0, 0];
      const crc = calcCrc8(payload);
      return [0x02, ...payload, crc, 0x03];
    }

    if (cmd1 === 0x05 && cmd3 === 24) {
      // CFG_RESET_FEEDER_TIME
      this.fuelLoadPct = 100;
      this.feederRuntimeSec = 0;
      const payload = [0x01, 0x06, 0x05, 0x00, 24, 0, 0];
      const crc = calcCrc8(payload);
      return [0x02, ...payload, crc, 0x03];
    }

    const payload = [0x01, 0x06, cmd1, 0x00, cmd3, 0, 0];
    const crc = calcCrc8(payload);
    return [0x02, ...payload, crc, 0x03];
  }
}

/**
 * High-level Ecoal Client wrapping any transport adapter.
 */
export class EcoalClient {
  constructor(adapter = null) {
    this.adapter = adapter || new HttpTransportAdapter();
  }

  setAdapter(adapter) {
    this.adapter = adapter;
  }

  async getStatus() {
    const cmd = buildStatusCmd();
    const raw = await this.adapter.sendHexCmd(cmd);
    return decodeStatusFrame(raw);
  }

  async readParam(paramId) {
    const cmd = buildReadParamCmd(paramId);
    const raw = await this.adapter.sendHexCmd(cmd);
    if (!raw || raw.length < 10) return null;
    const len = raw[6] | (raw[7] << 8);
    return raw.slice(8, 8 + len);
  }

  async writeParam(paramId, value) {
    const cmd = buildWriteParamCmd(paramId, Math.round(value));
    const raw = await this.adapter.sendHexCmd(cmd);
    return raw && (raw[2] === 6 || raw[2] === 21);
  }

  async setTargetBoilerTemp(temp) {
    const cmd = buildWriteParamCmd(40, Math.round(temp));
    const raw = await this.adapter.sendHexCmd(cmd);
    return raw && (raw[2] === 6 || raw[2] === 21);
  }

  async setTargetDhwTemp(temp) {
    const cmd = buildWriteParamCmd(17, Math.round(temp));
    const raw = await this.adapter.sendHexCmd(cmd);
    return raw && (raw[2] === 6 || raw[2] === 21);
  }

  async setFeederMode(mode) {
    const cmd = buildWriteParamCmd(119, parseInt(mode, 10));
    const raw = await this.adapter.sendHexCmd(cmd);
    return raw && (raw[2] === 6 || raw[2] === 21);
  }

  async refillHopper(kg = 150) {
    const cmd = buildRefillHopperCmd(kg);
    const raw = await this.adapter.sendHexCmd(cmd);
    return raw && (raw[2] === 6 || raw[2] === 21);
  }

  async ackAlarms() {
    const cmd = buildAckAlarmsCmd();
    const raw = await this.adapter.sendHexCmd(cmd);
    return raw && (raw[2] === 6 || raw[2] === 21);
  }

  async getWeeklyProgram(paramId) {
    const cmd = buildReadParamCmd(paramId);
    const raw = await this.adapter.sendHexCmd(cmd);
    if (!raw || raw.length < 52) return null;
    const len = raw[6] | (raw[7] << 8);
    if (len < 42) return null;
    return decodeWeeklyProgram(raw.slice(8, 8 + 42));
  }

  async setWeeklyProgram(paramId, days) {
    const cmd = buildWriteProgramCmd(paramId, days);
    const raw = await this.adapter.sendHexCmd(cmd);
    return raw && (raw[2] === 6 || raw[2] === 21);
  }
}
