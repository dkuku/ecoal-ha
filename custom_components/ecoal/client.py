"""eCoal protocol client for eCoal furnace controller."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
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

# eCMD_CFG subcommands (CMD 0x05)
CFG_SET_DATE = 6                  # 0x06 - Set controller date/time
CFG_ACK_ALARM = 9                 # 0x09 - Acknowledge active alarms
CFG_RESET_FEEDER_TIME = 24        # 0x18 - Reset feeder runtime / refill hopper (2-byte LE kg)

# ePARAM IDs (from firmware JS)
# --- Wdrożone w Home Assistant ---
PARAM_MOC_DMUCH = 8                   # 0x08 - Current blower power (%)
PARAM_CWU_TRYB = 16                   # 0x10 - CWU work mode
PARAM_CWU_ZADANA = 17                 # 0x11 - Target DHW temp (°C)
PARAM_PROG_CO_TAB = 24                # 0x18 - CO weekly program (42 bytes)
PARAM_PROG_CWU_TAB = 25               # 0x19 - CWU weekly program (42 bytes)
PARAM_CWU_OBNIZONA = 29               # 0x1D - DHW lowered amount (°C)
PARAM_MIESZ_AKTYWACJA = 19            # 0x13 - Mixer circuit activation
PARAM_CO_ZADANA = 40                  # 0x28 - Target boiler temp (°C)
PARAM_CO_OBNIZONA = 41                # 0x29 - CO lowered amount (°C)
PARAM_TRYB_PRACY = 51                 # 0x33 - Auto/manual mode
PARAM_PODAJNIK_CZASALARM = 79         # 0x4F - Feeder runtime to empty hopper (minutes)
PARAM_PODL_DZIENNA = 84               # 0x54 - Floor day temperature setpoint
PARAM_PODL_NOCNA = 85                 # 0x55 - Floor night temperature setpoint
PARAM_PROG_PODL_TAB = 87              # 0x57 - Floor weekly program (42 bytes)
PARAM_KOREKTA_DMUCHAWY = 94           # 0x5E - Blower power correction (-6..+6 %)
PARAM_REGULATOR_SPALIN = 98           # 0x62 - Exhaust temperature regulator (0=off, 1=on)
PARAM_PRIORYTET_CWU = 112             # 0x70 - DHW priority (0=off, 1=on)
PARAM_TYP_PODAJNIKA = 119             # 0x77 - Feeder combustion algorithm (0=manual, 1=group, 2=eCoal, 3=batch)

# --- Dostępne w sterowniku (niewdrożone) ---
# Histerezy i limity temperatur
PARAM_CWU_HIST = 18                   # 0x12 - Histereza CWU (°C x 10)
PARAM_CO_MIN = 38                     # 0x26 - Minimalna dopuszczalna temp. zadana CO (°C)
PARAM_CO_MAX = 39                     # 0x27 - Maksymalna dopuszczalna temp. zadana CO (°C)
PARAM_PODL_HISTEREZA = 86             # 0x56 - Histereza podłogówki (°C x 10)
PARAM_MAX_TEMP_SPALIN = 96            # 0x60 - Maksymalna temp. spalin dla regulatora (°C)
PARAM_HIST_TEMP_CO = 120              # 0x78 - Histereza temperatury kotła CO (°C)
PARAM_PODBICIE_TEMP = 121             # 0x79 - Podbicie temp. kotła CO przy grzaniu CWU (°C)

# Tryb letni i pogodowy
PARAM_PROG_POGODOWY_TAB = 26          # 0x1A - Harmonogram pogodowy CO (42 bytes)
PARAM_PROG_CO_M10 = 30                # 0x1E - Temp. zadana CO dla -10°C na zewnątrz (°C)
PARAM_PROG_CO_P10 = 31                # 0x1F - Temp. zadana CO dla +10°C na zewnątrz (°C)
PARAM_ZADAWANIE = 50                  # 0x32 - Tryb zadawania CO (0=stała/program, 1=pogodowy)
PARAM_AUTOLATO = 76                   # 0x4C - Automatyczny tryb letni (0=wył, 1=wł)
PARAM_AUTOLATO_TEMP = 77              # 0x4D - Temp. zewnętrzna załączenia Auto-Lato (°C)
PARAM_PROG_AUTOLATO = 83              # 0x53 - Harmonogram Auto-Lato (42 bytes)

# Regulator pokojowy
PARAM_PROG_POKOJOWY_TAB = 27          # 0x1B - Harmonogram regulatora pokojowego (42 bytes)
PARAM_PROG_POKOJOWY_DZIENNA = 32      # 0x20 - Temp. pokojowa dzienna (°C x 10)
PARAM_PROG_POKOJOWY_NOCNA = 33        # 0x21 - Temp. pokojowa nocna (°C x 10)
PARAM_WEW_ZADAWANIE = 78              # 0x4E - Tryb reg. pokojowego (0=wył, 1=program, 2=termostat)
PARAM_REG_POK_HISTEREZA = 80          # 0x50 - Histereza regulatora pokojowego (°C x 10)

# Pompy CO, cyrkulacja, podłogówka
PARAM_OBIEG_CZASPRACY = 22            # 0x16 - Czas pracy pompy cyrkulacyjnej
PARAM_OBIEG_POSTOJ = 23               # 0x17 - Czas postoju pompy cyrkulacyjnej
PARAM_PROG_OBIEG_TAB = 28             # 0x1C - Harmonogram pompy cyrkulacyjnej (42 bytes)
PARAM_POMPACO_TRYB = 69               # 0x45 - Praca cykliczna pompy CO (0=wył, 1=wł)
PARAM_POMPACO_PRACA = 70              # 0x46 - Czas pracy cyklicznej pompy CO (minuty)
PARAM_POMPACO_POSTOJ = 71             # 0x47 - Czas postoju cyklicznej pompy CO (minuty)
PARAM_POMPA_CWU_WYJSCIE = 88          # 0x58 - Wyjście pompy CWU
PARAM_AKTYWACJA_MIESZAJACA_LATO = 93  # 0x5D - Aktywacja mieszacza w lecie
PARAM_TEMP_ZAL_CYRK = 113             # 0x71 - Temp. załączenia cyrkulacji CWU (°C)
PARAM_PRACA_AUTO_CYRK = 114           # 0x72 - Automatyczna praca cyrkulacji CWU
PARAM_TEMP_ZAL_MIESZ = 115            # 0x73 - Temp. załączenia pompy mieszającej (°C)
PARAM_PODLOGOWA_CZASPRACY = 116       # 0x74 - Czas pracy obwodu podłogowego
PARAM_PODLOGOWA_POSTOJ = 117          # 0x75 - Czas postoju obwodu podłogowego
PARAM_PRACA_POMPCOPODL = 123          # 0x7B - Praca pompy CO przy podłogówce
PARAM_POSTOJ_POMPCOPODL = 124         # 0x7C - Postój pompy CO przy podłogówce

# Parametry podajnika i dmuchawy (tryb ręczny i podtrzymanie)
PARAM_MOC_DMUCH_PODT = 9              # 0x09 - Moc dmuchawy w podtrzymaniu (%)
PARAM_POD_CZASPRACY_PODT = 10         # 0x0A - Czas pracy podajnika w podtrzymaniu (s)
PARAM_POD_PRZERWA_PODT = 11           # 0x0B - Czas przerwy podajnika w podtrzymaniu (s)
PARAM_POWT_PODT = 12                  # 0x0C - Ilość powtórzeń w podtrzymaniu
PARAM_POD_POST_PODT = 13              # 0x0D - Czas postoju podajnika w podtrzymaniu (min)
PARAM_POD_MAX_TEMP = 14               # 0x0E - Maks. temp. podajnika - alarm (°C)
PARAM_POD_CZAS_OBR = 15               # 0x0F - Czas obrotu podajnika
PARAM_POD_CZASPRACY_GRZ = 34          # 0x22 - Czas pracy podajnika w grzaniu ręcznym (s)
PARAM_POD_POST_GRZ = 35               # 0x23 - Czas postoju podajnika w grzaniu ręcznym (s)
PARAM_PODAJNIK_CZASPRACY_GRZANIE = 82 # 0x52 - Czas podawania w grzaniu (s)
PARAM_MOC_DMUCH_GRZ = 97              # 0x61 - Moc dmuchawy w grzaniu ręcznym (%)
PARAM_CZAS_POSTOJU_GRZANIE = 118      # 0x76 - Czas postoju w grzaniu ręcznym (s)
PARAM_PODAJNIK_CZASWYRZUTU = 122      # 0x7A - Czas awaryjnego wyrzutu paliwa (s)

# Strojenie spalania grupowego (moce dmuchawy i dawki paliwa dla 8..30 kW)
PARAM_ALG_MAXMOC = 100                # 0x64 - Maksymalna moc kotła w spalaniu grupowym (kW)
PARAM_ALG_MINMOC = 106                # 0x6A - Minimalna moc kotła w spalaniu grupowym (kW)
PARAM_ALG_MOCDMUCH8 = 101             # 0x65 - Moc dmuchawy dla 8 kW (%)
PARAM_ALG_MOCDMUCH12 = 102            # 0x66 - Moc dmuchawy dla 12 kW (%)
PARAM_ALG_MOCDMUCH16 = 103            # 0x67 - Moc dmuchawy dla 16 kW (%)
PARAM_ALG_MOCDMUCH20 = 104            # 0x68 - Moc dmuchawy dla 20 kW (%)
PARAM_ALG_MOCDMUCH25 = 105            # 0x69 - Moc dmuchawy dla 25 kW (%)
PARAM_ALG_MOCDMUCH30 = 125            # 0x7D - Moc dmuchawy dla 30 kW (%)
PARAM_ALG_ILGRUP8 = 126               # 0x7E - Ilość podań paliwa dla 8 kW
PARAM_ALG_ILGRUP12 = 127              # 0x7F - Ilość podań paliwa dla 12 kW
PARAM_ALG_ILGRUP16 = 128              # 0x80 - Ilość podań paliwa dla 16 kW
PARAM_ALG_ILGRUP20 = 129              # 0x81 - Ilość podań paliwa dla 20 kW
PARAM_ALG_ILGRUP25 = 130              # 0x82 - Ilość podań paliwa dla 25 kW
PARAM_ALG_ILGRUP30 = 131              # 0x83 - Ilość podań paliwa dla 30 kW

# Czujniki bezpieczeństwa i alarmy
PARAM_ALARM_CZASOPOZNIENIA = 89       # 0x59 - Czas opóźnienia zgłoszenia alarmu (s)
PARAM_ALARM_INWERSJA = 90             # 0x5A - Inwersja wejść alarmowych (0/1)
PARAM_ALARM_ZATRZYMANIE = 91          # 0x5B - Zatrzymanie kotła przy alarmie (0/1)
PARAM_ALG_WYGASZENIA = 111            # 0x6F - Algorytm wygaszania kotła (0/1)
PARAM_CZUJNIK_ZAMZAS = 132            # 0x84 - Czujnik otwarcia zasobnika paliwa (0/1)
PARAM_CZUJNIK_ZERZAW = 133            # 0x85 - Czujnik zerwania zawleczki podajnika (0/1)
PARAM_TYP_KOTLA = 92                  # 0x5C - Identyfikator typu kotła

# Offsety kalibracji czujników temperatury (-10.0..+10.0 °C x 10)
PARAM_OFFSET_Z1 = 0                   # 0x00 - Offset czujnika Z1
PARAM_OFFSET_WEW = 1                  # 0x01 - Offset czujnika wewnętrznego (pokojowego)
PARAM_OFFSET_ZEW = 2                  # 0x02 - Offset czujnika zewnętrznego
PARAM_OFFSET_CWU = 3                  # 0x03 - Offset czujnika CWU
PARAM_OFFSET_POW = 4                  # 0x04 - Offset czujnika powrotu
PARAM_OFFSET_POD = 5                  # 0x05 - Offset czujnika podajnika
PARAM_OFFSET_CO = 6                   # 0x06 - Offset czujnika kotła CO
PARAM_OFFSET_SPA = 7                  # 0x07 - Offset czujnika spalin

# Parametry sieciowe i zdalnego dostępu
PARAM_IP = 45                         # 0x2D - Adres IP sterownika
PARAM_MASKA = 46                      # 0x2E - Maska podsieci
PARAM_BRAMA = 47                      # 0x2F - Brama domyślna
PARAM_MAC = 66                        # 0x42 - Adres MAC
PARAM_SERWER_PORT = 72                # 0x48 - Port serwera eSterownik.pl
PARAM_SERWER_ID = 73                  # 0x49 - ID urządzenia w chmurze
PARAM_SERWER_AKTYWACJA = 74           # 0x4A - Aktywacja chmury eSterownik.pl
PARAM_SERWER_IP = 75                  # 0x4B - Adres IP serwera chmury
PARAM_OKRES_REJESTRACJI = 95          # 0x5F - Okres rejestracji historii (s)

# Feeder combustion modes (eTYP_PODAJNIKA)
FEEDER_MODE_MANUAL = 0            # Retortowy - ręczny (stałe czasy)
FEEDER_MODE_GROUP = 1             # Retortowy - automatyczny (spalanie grupowe)
FEEDER_MODE_ECOAL = 2             # Retortowy - eCoal (modulowany PID)
FEEDER_MODE_BATCH = 3             # Zasypowy

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

    async def send_raw_command(self, cmd: str) -> str | None:
        """Send raw hex command frame to furnace and return response text."""
        url = f"{self._url}/?com={cmd}"
        try:
            async with self._session.get(
                url, auth=self._auth, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Error communicating with furnace at %s: %s", self.host, err)
            return None

    async def _send(self, cmd: str) -> list[int] | None:
        body = await self.send_raw_command(cmd)
        if body is None:
            return None
        start = body.find("[")
        end = body.find("]")
        if start == -1 or end == -1:
            return None
        return [int(v.strip()) for v in body[start + 1 : end].split(",")]

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
        fuel_load_dt: datetime | None = None
        try:
            fuel_load_dt = datetime(
                2000 + d[68], d[69], d[70], d[71], d[72]
            )
            result["fuel_load_date"] = fuel_load_dt.isoformat()
        except (ValueError, OverflowError):
            result["fuel_load_date"] = None

        # Fuel data (bytes 73-77)
        nowyzasyp_min = d[73] | (d[74] << 8) | (d[77] << 16)
        result["fuel_remaining"] = nowyzasyp_min
        result["fuel_load_pct"] = d[75]
        result["feeding_pct"] = d[76]

        if fuel_load_dt is not None and nowyzasyp_min > 0:
            try:
                result["estimated_empty_date"] = (
                    fuel_load_dt + timedelta(minutes=nowyzasyp_min)
                ).isoformat()
            except OverflowError:
                result["estimated_empty_date"] = None
        else:
            result["estimated_empty_date"] = None

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

    async def refill_hopper(self, kg: int = 150) -> bool:
        """Reset feeder runtime counter and record new coal refill (100% hopper)."""
        kg = max(1, min(1000, int(kg)))
        cmd = _build_frame(0x05, 0x00, CFG_RESET_FEEDER_TIME, [kg & 0xFF, (kg >> 8) & 0xFF])
        result = await self._send(cmd)
        return result is not None

    async def ack_alarms(self) -> bool:
        """Acknowledge active controller alarms."""
        cmd = _build_frame(0x05, 0x00, CFG_ACK_ALARM, [0x00])
        result = await self._send(cmd)
        return result is not None

    async def sync_clock(self, now: datetime | None = None) -> bool:
        """Synchronize controller clock with current system time."""
        if now is None:
            now = datetime.now()
        data = [
            max(0, now.year - 2000) & 0xFF,
            now.month & 0xFF,
            now.day & 0xFF,
            now.hour & 0xFF,
            now.minute & 0xFF,
            now.second & 0xFF,
        ]
        cmd = _build_frame(0x05, 0x00, CFG_SET_DATE, data)
        result = await self._send(cmd)
        return result is not None

    async def get_feeder_mode(self) -> int | None:
        """Read current feeder combustion algorithm (PARAM 119)."""
        data = await self.read_param(PARAM_TYP_PODAJNIKA)
        if not data:
            return None
        return data[0]

    async def set_feeder_mode(self, mode: int) -> bool:
        """Set feeder combustion algorithm (0=manual, 1=group, 2=eCoal, 3=batch)."""
        cmd = _build_value_cmd(PARAM_TYP_PODAJNIKA, int(mode))
        result = await self._send(cmd)
        return result is not None

    async def get_feeder_max_runtime(self) -> int | None:
        """Read feeder runtime required to empty a full hopper in minutes (PARAM 79)."""
        data = await self.read_param(PARAM_PODAJNIK_CZASALARM)
        if not data or len(data) < 2:
            return None
        return data[0] | (data[1] << 8)

    async def set_feeder_max_runtime(self, minutes: int) -> bool:
        """Set feeder runtime required to empty a full hopper in minutes (PARAM 79)."""
        cmd = _build_value_cmd(PARAM_PODAJNIK_CZASALARM, int(minutes))
        result = await self._send(cmd)
        return result is not None

    async def get_dhw_priority(self) -> bool | None:
        """Read DHW priority (PARAM 112)."""
        data = await self.read_param(PARAM_PRIORYTET_CWU)
        if not data:
            return None
        return bool(data[0])

    async def set_dhw_priority(self, on: bool) -> bool:
        """Set DHW priority (PARAM 112)."""
        cmd = _build_value_cmd(PARAM_PRIORYTET_CWU, 1 if on else 0)
        result = await self._send(cmd)
        return result is not None

    async def get_blower_correction(self) -> int | None:
        """Read blower power correction percentage (PARAM 94, -6..+6 %)."""
        data = await self.read_param(PARAM_KOREKTA_DMUCHAWY)
        if not data or len(data) < 2:
            return None
        val = data[0] | (data[1] << 8)
        if val > 32767:
            val -= 65536
        return val

    async def set_blower_correction(self, correction: int) -> bool:
        """Set blower power correction percentage (PARAM 94, -6..+6 %)."""
        correction = max(-6, min(6, int(correction)))
        cmd = _build_value_cmd(PARAM_KOREKTA_DMUCHAWY, correction)
        result = await self._send(cmd)
        return result is not None

    async def get_exhaust_temp_regulator(self) -> bool | None:
        """Read exhaust temperature regulator state (PARAM 98)."""
        data = await self.read_param(PARAM_REGULATOR_SPALIN)
        if not data:
            return None
        return bool(data[0])

    async def set_exhaust_temp_regulator(self, on: bool) -> bool:
        """Set exhaust temperature regulator state (PARAM 98)."""
        cmd = _build_value_cmd(PARAM_REGULATOR_SPALIN, 1 if on else 0)
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
