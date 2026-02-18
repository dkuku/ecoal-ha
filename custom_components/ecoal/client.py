"""eCoal protocol client for eCoal furnace controller."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

CRC_TABLE = (
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
)

# Pre-built commands
CMD_STATUS = "02010006000000006103"
CMD_SETTINGS = "02010005001600002403"
CMD_AUTO_ON = "020100020033020001006503"
CMD_AUTO_OFF = "020100020033020000009103"

# ePARAM IDs (from firmware JS)
PARAM_CO_ZADANA = 40       # 0x28
PARAM_CO_OBNIZONA = 41     # 0x29
PARAM_CWU_ZADANA = 17      # 0x11
PARAM_CWU_OBNIZONA = 29    # 0x1D
PARAM_PROG_CO_TAB = 24     # 0x18 - CO weekly program (42 bytes)
PARAM_PROG_CWU_TAB = 25    # 0x19 - CWU weekly program (42 bytes)
PARAM_CWU_TRYB = 16        # 0x10 - CWU work mode
PARAM_MIESZ_AKTYWACJA = 19 # 0x13 - Mixer circuit activation (floor heating on/off)
PARAM_TRYB_PRACY = 51      # 0x33 - auto/manual mode
PARAM_PODL_DZIENNA = 84    # 0x54 - Floor day temperature setpoint
PARAM_PODL_NOCNA = 85      # 0x55 - Floor night temperature setpoint
PARAM_PROG_PODL_TAB = 87   # 0x57 - Floor weekly program (42 bytes)

# CWU work modes
CWU_MODE_WINTER = 0
CWU_MODE_SUMMER = 1
CWU_MODE_AUTO_TEMP = 2
CWU_MODE_AUTO_PROG = 3
CWU_MODE_OFF = 4

SENSOR_NAMES = [
    "floor_temp",    # 0: TEMP_PODLOG
    "indoor_temp",   # 1: TEMP_WEW
    "outdoor_temp",  # 2: TEMP_ZEW
    "dhw_temp",      # 3: TEMP_CWU
    "return_temp",   # 4: TEMP_POWR
    "feeder_temp",   # 5: TEMP_POD
    "boiler_temp",   # 6: TEMP_CO
    "exhaust_temp",  # 7: TEMP_SPALIN
]

OUTPUT_NAMES = [
    "air_pump",      # 0: OUT_DMUCHAWA
    "coal_feeder",   # 1: OUT_PODAJNIK
    "ch_pump",       # 2: OUT_POMPA_CO
    "dhw_pump",      # 3: OUT_POMPA_CWU
    "mixer_pump",    # 4: OUT_POMPA_MIESZ
    "z1_pump",       # 5: OUT_POMPA_Z1
    "valve_3d",      # 6: OUT_ZAWOR_3D
    "cwu_mixer",     # 7: OUT_CWU_MIESZ
]


def _calc_crc(payload: list[int]) -> int:
    crc = 0
    for b in payload:
        crc = CRC_TABLE[crc ^ (b & 0xFF)]
    return crc


def _decode_temp(lo: int, hi: int) -> float:
    raw = (hi << 8) | lo
    if raw > 32767:
        raw -= 65536
    return round(raw / 10.0, 1)


def _build_frame(cmd: int, cmd2: int, cmd3: int, data: list[int] | None = None) -> str:
    if data is None:
        data = []
    dl = len(data)
    payload = [0x01, 0x00, cmd, cmd2, cmd3, dl & 0xFF, (dl >> 8) & 0xFF] + data
    crc = _calc_crc(payload)
    frame = [0x02] + payload + [crc, 0x03]
    return "".join(f"{b:02x}" for b in frame)


def _build_switch_cmd(param: int, on: bool) -> str:
    return _build_frame(0x05, 0x00, param, [0x01 if on else 0x00])


def _build_value_cmd(param: int, value: int) -> str:
    """Build CMD_SET_PARAM (0x02) frame. Always 2-byte LE per protocol."""
    if value < 0:
        value = value + 65536
    data = [value & 0xFF, (value >> 8) & 0xFF]
    return _build_frame(0x02, 0x00, param, data)


def _build_read_cmd(param: int) -> str:
    return _build_frame(0x01, 0x00, param)


def _parse_program(data: list[int]) -> list[str]:
    """Parse 42-byte weekly program into 7 day strings of 48 '0'/'1' chars.
    Each day = 48 half-hour slots. '1'=normal temp, '0'=lowered.
    Days: 0=Sunday..6=Saturday.
    """
    days = []
    for day in range(7):
        bits = ""
        for byte_idx in range(6):
            b = data[day * 6 + byte_idx]
            for bit in range(8):
                bits += "1" if (b >> bit) & 1 else "0"
        days.append(bits)
    return days


def _encode_program(days: list[str]) -> list[int]:
    result = []
    for day_bits in days:
        for byte_idx in range(6):
            b = 0
            for bit in range(8):
                idx = byte_idx * 8 + bit
                if idx < len(day_bits) and day_bits[idx] == "1":
                    b |= (1 << bit)
            result.append(b)
    return result


class EcoalClient:
    """Client for communicating with furnace via eCoal HTTP protocol."""

    def __init__(
        self, host: str, username: str, password: str, session: aiohttp.ClientSession
    ) -> None:
        self.host = host
        self._auth = aiohttp.BasicAuth(username, password)
        self._session = session
        self._url = f"http://{host}"

    async def _send(self, cmd: str) -> list[int] | None:
        url = f"{self._url}/?com={cmd}"
        try:
            async with self._session.get(
                url, auth=self._auth, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return None
                body = await resp.text()
                start = body.find("[")
                end = body.find("]")
                if start == -1 or end == -1:
                    return None
                return [int(v.strip()) for v in body[start + 1 : end].split(",")]
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Error communicating with furnace at %s: %s", self.host, err)
            return None

    async def get_status(self) -> dict[str, Any] | None:
        """Read full furnace status (CMD 0x06). All fields decoded per JS CStatus."""
        vals = await self._send(CMD_STATUS)
        if vals is None or len(vals) < 86:
            return None

        d = vals
        result: dict[str, Any] = {}

        # Sensor states (bytes 8-15): per sensor, 0=OK, 1=disconnected
        for i, name in enumerate(SENSOR_NAMES):
            result[f"{name}_state"] = d[8 + i]

        # Temperatures (bytes 16-31): 8x2 bytes, signed LE / 10
        for i, name in enumerate(SENSOR_NAMES):
            idx = 16 + i * 2
            result[name] = _decode_temp(d[idx], d[idx + 1])

        # Outputs bitmask (byte 32)
        out_byte = d[32]
        for i, name in enumerate(OUTPUT_NAMES):
            result[name] = bool((out_byte >> i) & 1)

        # Control state (bytes 33-39)
        result["heating"] = d[33]
        result["auto_mode"] = d[34] == 1
        result["setpoint_mode"] = d[35]
        result["cwu_mode"] = d[36]
        result["target_boiler_temp"] = d[37]
        result["target_dhw_temp"] = d[38]
        result["air_pump_power"] = d[39]

        # Alarms (bytes 40-41)
        result["alarms_raw"] = (d[41] << 8) | d[40]
        result["alarm_active"] = result["alarms_raw"] != 0

        # Mixer and auth (bytes 42-43)
        result["mixer_circuit"] = d[42]
        result["auth_level"] = d[43]

        # Date/time (bytes 44-49)
        try:
            result["controller_datetime"] = datetime(
                2000 + d[44], d[45], d[46], d[47], d[48], d[49]
            ).isoformat()
        except (ValueError, OverflowError):
            result["controller_datetime"] = None

        # Mode flags (bytes 50-54)
        result["co_lowered_active"] = bool(d[50])
        result["cwu_lowered_active"] = bool(d[51])
        result["room_heating"] = d[52]
        result["internal_setpoint"] = d[53]
        result["day_night"] = d[54]

        # Room temperature setpoints (bytes 55-58)
        result["room_day_temp"] = _decode_temp(d[55], d[56])
        result["room_night_temp"] = _decode_temp(d[57], d[58])

        # Lowered amounts (bytes 59-60)
        result["co_lowered_amount"] = d[59]
        result["cwu_lowered_amount"] = d[60]

        # Inputs bitmask (byte 61)
        result["inputs_raw"] = d[61]

        # More alarms (bytes 62-63)
        result["alarms2_raw"] = (d[63] << 8) | d[62]

        # Feeder time (bytes 64-67): 32-bit LE seconds
        feeder_secs = d[64] | (d[65] << 8) | (d[66] << 16) | (d[67] << 24)
        result["feeder_runtime"] = round(feeder_secs / 60.0, 1)

        # Fuel load date (bytes 68-72)
        try:
            result["fuel_load_date"] = datetime(
                2000 + d[68], d[69], d[70], d[71], d[72]
            ).isoformat()
        except (ValueError, OverflowError):
            result["fuel_load_date"] = None

        # Fuel data (bytes 73-77)
        result["fuel_remaining"] = d[73] | (d[74] << 8) | (d[77] << 16)
        result["fuel_load_pct"] = d[75]
        result["feeding_pct"] = d[76]

        # Floor heating setpoints (bytes 78-81)
        result["floor_day_temp"] = _decode_temp(d[78], d[79])
        result["floor_night_temp"] = _decode_temp(d[80], d[81])

        # Final flags (bytes 82-83)
        result["floor_day_night"] = d[82]
        result["is_summer"] = bool(d[83])

        result["raw_status"] = vals
        return result

    async def get_firmware_version(self) -> str | None:
        vals = await self._send(CMD_SETTINGS)
        if vals is None or len(vals) < 48:
            return None
        vlen = vals[38]
        if vlen > 0 and 39 + vlen <= len(vals):
            try:
                return "".join(chr(v) for v in vals[39 : 39 + vlen])
            except (ValueError, IndexError):
                return None
        return None

    async def get_weekly_program(self, param: int) -> list[str] | None:
        """Read 42-byte weekly program. Returns 7 strings of 48 '0'/'1' chars."""
        cmd = _build_read_cmd(param)
        vals = await self._send(cmd)
        if vals is None:
            return None
        data_len = vals[6] | (vals[7] << 8)
        if data_len < 42:
            return None
        return _parse_program(vals[8 : 8 + 42])

    async def set_weekly_program(self, param: int, days: list[str]) -> bool:
        data = _encode_program(days)
        cmd = _build_frame(0x02, 0x00, param, data)
        result = await self._send(cmd)
        return result is not None

    async def set_switch(self, param: int, on: bool) -> bool:
        cmd = _build_switch_cmd(param, on)
        result = await self._send(cmd)
        return result is not None

    async def set_auto_mode(self, on: bool) -> bool:
        cmd = CMD_AUTO_ON if on else CMD_AUTO_OFF
        result = await self._send(cmd)
        return result is not None

    async def set_target_boiler_temp(self, temp: int) -> bool:
        cmd = _build_value_cmd(PARAM_CO_ZADANA, temp)
        result = await self._send(cmd)
        return result is not None

    async def set_co_lowered_temp(self, temp: int) -> bool:
        cmd = _build_value_cmd(PARAM_CO_OBNIZONA, temp)
        result = await self._send(cmd)
        return result is not None

    async def set_target_dhw_temp(self, temp: int) -> bool:
        cmd = _build_value_cmd(PARAM_CWU_ZADANA, temp)
        result = await self._send(cmd)
        return result is not None

    async def set_cwu_lowered_temp(self, temp: int) -> bool:
        cmd = _build_value_cmd(PARAM_CWU_OBNIZONA, temp)
        result = await self._send(cmd)
        return result is not None

    async def set_cwu_mode(self, mode: int) -> bool:
        cmd = _build_value_cmd(PARAM_CWU_TRYB, mode)
        result = await self._send(cmd)
        return result is not None

    async def set_floor_day_temp(self, temp: int) -> bool:
        cmd = _build_value_cmd(PARAM_PODL_DZIENNA, temp)
        result = await self._send(cmd)
        return result is not None

    async def set_floor_night_temp(self, temp: int) -> bool:
        cmd = _build_value_cmd(PARAM_PODL_NOCNA, temp)
        result = await self._send(cmd)
        return result is not None

    async def set_mixer_activation(self, on: bool) -> bool:
        cmd = _build_value_cmd(PARAM_MIESZ_AKTYWACJA, 1 if on else 0)
        result = await self._send(cmd)
        return result is not None

    async def read_param(self, param: int) -> list[int] | None:
        cmd = _build_read_cmd(param)
        vals = await self._send(cmd)
        if vals is None:
            return None
        data_len = vals[6] | (vals[7] << 8)
        return vals[8 : 8 + data_len]

    async def test_connection(self) -> bool:
        return await self.get_status() is not None
