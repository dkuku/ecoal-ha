/**
 * eCoal Protocol Engine (JavaScript)
 *
 * Implements frame serialization, CRC8 calculation, status decoding,
 * and command building for the eCoal furnace controller.
 * Compatible with Node.js and modern Web browsers (zero dependencies).
 */

// Dallas 1-wire CRC Table (exact match for eCoal firmware)
export const CRC_TABLE = [
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
  130, 179, 224, 209, 70, 119, 36, 21, 59, 10, 89, 104, 255, 206, 157, 172,
];

export const SENSOR_NAMES = [
  "floor_temp",    // 0: TEMP_PODLOG
  "indoor_temp",   // 1: TEMP_WEW
  "outdoor_temp",  // 2: TEMP_ZEW
  "dhw_temp",      // 3: TEMP_CWU
  "return_temp",   // 4: TEMP_POWR
  "feeder_temp",   // 5: TEMP_POD
  "boiler_temp",   // 6: TEMP_CO
  "exhaust_temp",  // 7: TEMP_SPALIN
];

export const OUTPUT_NAMES = [
  "air_pump",      // 0: OUT_DMUCHAWA
  "coal_feeder",   // 1: OUT_PODAJNIK
  "ch_pump",       // 2: OUT_POMPA_CO
  "dhw_pump",      // 3: OUT_POMPA_CWU
  "mixer_pump",    // 4: OUT_POMPA_MIESZ
  "z1_pump",       // 5: OUT_POMPA_Z1
  "valve_3d",      // 6: OUT_ZAWOR_3D
  "cwu_mixer",     // 7: OUT_CWU_MIESZ
];

export const FEEDER_MODES = {
  0: "retort_manual",
  1: "retort_group",
  2: "retort_ecoal",
  3: "batch",
};

/**
 * Calculates CRC8 checksum over array of bytes using eCoal polynomial.
 */
export function calcCrc8(bytes) {
  let crc = 0;
  for (let i = 0; i < bytes.length; i++) {
    crc = CRC_TABLE[(crc ^ (bytes[i] & 0xff)) & 0xff];
  }
  return crc;
}

/**
 * Decodes 16-bit signed LE integer to temperature (°C).
 */
export function decodeTemp(lo, hi) {
  let raw = (hi << 8) | lo;
  if (raw > 32767) raw -= 65536;
  return Math.round((raw / 10.0) * 10) / 10;
}

/**
 * Builds binary request frame and formats it as hexadecimal string.
 */
export function buildFrame(cmd1, cmd2, cmd3, data = []) {
  const dl = data.length;
  const payload = [
    0x01, // ADR
    0x00, // Status
    cmd1 & 0xff,
    cmd2 & 0xff,
    cmd3 & 0xff,
    dl & 0xff,
    (dl >> 8) & 0xff,
    ...data,
  ];
  const crc = calcCrc8(payload);
  const frame = [0x02, ...payload, crc, 0x03];
  return frame.map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function buildStatusCmd() {
  return buildFrame(0x06, 0x00, 0x00);
}

export function buildReadParamCmd(paramId) {
  return buildFrame(0x01, 0x00, paramId);
}

export function buildWriteParamCmd(paramId, value) {
  if (value < 0) value += 65536;
  const data = [value & 0xff, (value >> 8) & 0xff];
  return buildFrame(0x02, 0x00, paramId, data);
}

export function buildRefillHopperCmd(kg = 150) {
  const data = [kg & 0xff, (kg >> 8) & 0xff];
  return buildFrame(0x05, 0x00, 24, data); // CFG_RESET_FEEDER_TIME = 24
}

export function buildAckAlarmsCmd() {
  return buildFrame(0x05, 0x00, 9); // CFG_ACK_ALARM = 9
}

/**
 * Decodes 42-byte weekly schedule payload into array of 7 day strings (48 chars of '0' or '1').
 */
export function decodeWeeklyProgram(bytes) {
  const days = [];
  for (let day = 0; day < 7; day++) {
    let bits = "";
    for (let byteIdx = 0; byteIdx < 6; byteIdx++) {
      const b = bytes[day * 6 + byteIdx] || 0;
      for (let bit = 0; bit < 8; bit++) {
        bits += ((b >> bit) & 1) ? "1" : "0";
      }
    }
    days.push(bits);
  }
  return days;
}

/**
 * Encodes array of 7 day strings (48 chars each) into 42 bytes payload.
 */
export function encodeWeeklyProgram(days) {
  const bytes = [];
  for (let day = 0; day < 7; day++) {
    const dayBits = days[day] || "1".repeat(48);
    for (let byteIdx = 0; byteIdx < 6; byteIdx++) {
      let b = 0;
      for (let bit = 0; bit < 8; bit++) {
        const idx = byteIdx * 8 + bit;
        if (idx < dayBits.length && dayBits[idx] === "1") {
          b |= (1 << bit);
        }
      }
      bytes.push(b);
    }
  }
  return bytes;
}

export function buildWriteProgramCmd(paramId, days) {
  const data = encodeWeeklyProgram(days);
  return buildFrame(0x02, 0x00, paramId, data);
}

/**
 * Parsed Frame representation.
 */
export class CRamka {
  constructor(tab = []) {
    this.valid = false;
    this.stx = null;
    this.adr = null;
    this.status1 = null;
    this.cmd1 = null;
    this.cmd2 = null;
    this.cmd3 = null;
    this.dataLength = 0;
    this.data = [];
    this.crc = null;
    this.etx = null;
    this.crcOk = false;

    if (tab && tab.length >= 10) {
      this.parse(tab);
    }
  }

  parse(tab) {
    if (tab.length < 10) {
      this.valid = false;
      return false;
    }
    this.stx = tab[0];
    this.adr = tab[1];
    this.status1 = tab[2];
    this.cmd1 = tab[3];
    this.cmd2 = tab[4];
    this.cmd3 = tab[5];
    this.dataLength = tab[6] | (tab[7] << 8);

    this.data = tab.slice(8, 8 + this.dataLength);
    this.crc = tab[8 + this.dataLength];
    this.etx = tab[9 + this.dataLength];

    const payload = tab.slice(1, 8 + this.dataLength);
    const expectedCrc = calcCrc8(payload);
    this.crcOk = this.crc === expectedCrc;
    this.valid = this.stx === 0x02 && this.etx === 0x03 && this.crcOk;
    return this.valid;
  }
}

/**
 * Decodes 86-byte CMD_STATUS response into a clean, modern JavaScript object.
 */
export function decodeStatusFrame(tab) {
  if (!tab || tab.length < 86) return null;
  const frame = new CRamka(tab);
  if (!frame.valid) return null;

  const d = frame.data;
  const result = {
    connected_sensors: {},
    outputs: {},
  };

  // Sensor states (bytes 0..7 in data): 0=connected, 1=disconnected
  for (let i = 0; i < SENSOR_NAMES.length; i++) {
    const sName = SENSOR_NAMES[i];
    result.connected_sensors[sName] = d[i] === 0;
  }

  // Temperatures (bytes 8..23 in data)
  for (let i = 0; i < SENSOR_NAMES.length; i++) {
    const sName = SENSOR_NAMES[i];
    const idx = 8 + i * 2;
    result[sName] = decodeTemp(d[idx], d[idx + 1]);
  }

  // Outputs bitmask (byte 24 in data, 32 in frame)
  const outByte = d[24];
  for (let i = 0; i < OUTPUT_NAMES.length; i++) {
    const oName = OUTPUT_NAMES[i];
    result.outputs[oName] = ((outByte >> i) & 1) === 1;
    result[oName] = result.outputs[oName];
  }

  // Control states (bytes 25..31 in data)
  result.heating = d[25];
  result.auto_mode = d[26] === 1;
  result.setpoint_mode = d[27];
  result.cwu_mode = d[28];
  result.target_boiler_temp = d[29];
  result.target_dhw_temp = d[30];
  result.air_pump_power = d[31];

  // Alarms (bytes 32..33 in data)
  result.alarms_raw = d[32] | (d[33] << 8);
  result.alarm_active = result.alarms_raw !== 0;

  // Mixer circuit and Auth (bytes 34..35 in data)
  result.mixer_circuit = d[34];
  result.auth_level = d[35];

  // Clock (bytes 36..41 in data)
  result.clock = {
    year: 2000 + d[36],
    month: d[37],
    day: d[38],
    hour: d[39],
    minute: d[40],
    second: d[41],
  };

  // Feeder runtime in seconds (bytes 56..59 in data)
  const rtSec = d[56] | (d[57] << 8) | (d[58] << 16) | (d[59] << 24);
  result.feeder_runtime_sec = rtSec;
  result.feeder_runtime_min = Math.round((rtSec / 60.0) * 10) / 10;

  // Fuel data (byte 67 in data = fuel load percentage)
  result.fuel_load_pct = Math.max(0, Math.min(100, d[67]));

  return result;
}
