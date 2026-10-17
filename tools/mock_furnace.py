#!/usr/bin/env python3
"""Virtual eCoal Furnace Simulator (Mock Server).

Emulates an eCoal furnace controller (firmware v0.2.9.16a) over HTTP protocol.
Supports full 122 parameter register table, 86-byte CMD_STATUS frames,
START handshake, fuel tracking, and parameter read/write commands.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
import sys
import time
from urllib.parse import parse_qs, urlparse

_LOGGER = logging.getLogger("ecoal_mock")

# Dallas 1-wire CRC table (exact eCoal match)
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


def calc_crc(payload: list[int]) -> int:
    crc = 0
    for b in payload:
        crc = CRC_TABLE[crc ^ (b & 0xFF)]
    return crc


def build_response_frame(
    status: int, cmd1: int, cmd2: int, cmd3: int, data: list[int] | None = None
) -> list[int]:
    if data is None:
        data = []
    dl = len(data)
    payload = [
        0x01,  # ADR
        status,  # Status1 (6=ACK, 21=NAK)
        cmd1,
        cmd2,
        cmd3,
        dl & 0xFF,
        (dl >> 8) & 0xFF,
    ] + data
    crc = calc_crc(payload)
    return [0x02] + payload + [crc, 0x03]


class VirtualFurnaceState:
    """In-memory state and registers for the simulated furnace."""

    def __init__(self) -> None:
        # Physical sensors (°C * 10)
        self.boiler_temp: int = 587  # 58.7 °C
        self.dhw_temp: int = 482  # 48.2 °C
        self.exhaust_temp: int = 1124  # 112.4 °C
        self.feeder_temp: int = 285  # 28.5 °C
        self.return_temp: int = 491  # 49.1 °C
        self.outside_temp: int = 125  # 12.5 °C
        self.inside_temp: int = 210  # 21.0 °C
        self.floor_temp: int = 280  # 28.0 °C

        # Operating state
        self.heating: int = 1  # 1 = Grzanie, 0 = Podtrzymanie
        self.auto_mode: int = 1  # 1 = Auto, 0 = Manual
        self.setpoint_mode: int = 0
        self.cwu_mode: int = 0  # 0 = Zima, 1 = Lato
        self.air_pump_power: int = 38  # 38% dmuchawy

        # Outputs bitmask: 0=Dmuchawa, 1=Podajnik, 2=Pompa CO, 3=Pompa CWU, 4=Mieszacz, 5=Z1, 6=Zawor 3D, 7=CWU Miesz
        self.outputs_byte: int = 0b00000101  # Dmuchawa ON, Pompa CO ON

        # Alarms
        self.alarms_raw: int = 0  # 0 = brak alarmów

        # Feeder runtime in seconds (counter for fuel consumption)
        self.feeder_runtime_sec: int = 1234
        self.feeder_max_runtime_min: int = 600  # PARAM 79 (600 min = 100% tank)
        self.fuel_load_pct: int = 99

        # Parameters storage: dict of param_id -> [val, min, max, default]
        self.params: dict[int, list[int]] = self._init_default_params()

        # Weekly programs (7 programs x 42 bytes = 294 bytes)
        self.programs: dict[int, list[int]] = {
            24: [0xFF] * 42,  # CMD_PROG_CO_TAB
            25: [0xFF] * 42,  # CMD_PROG_CWU_TAB
            26: [0xFF] * 42,  # CMD_PROG_POGODOWY_TAB
            27: [0xFF] * 42,  # CMD_PROG_POKOJOWY_TAB
            28: [0xFF] * 42,  # CMD_PROG_OBIEG_TAB
            83: [0xFF] * 42,  # CMD_PROG_AUTOLATO
            87: [0xFF] * 42,  # CMD_PROG_PODLOGOWA
        }

    def _init_default_params(self) -> dict[int, list[int]]:
        """Initialize all 122 furnace registers with default boundaries."""
        p: dict[int, list[int]] = {}

        # Default helper: [value, min, max, factory]
        def set_p(pid: int, val: int, pmin: int, pmax: int, pdef: int) -> None:
            p[pid] = [val, pmin, pmax, pdef]

        # 8 calibration offsets (-10.0 .. +10.0 °C x 10)
        for i in range(8):
            set_p(i, 0, -100, 100, 0)

        # Combustion & Blower
        set_p(8, 38, 1, 100, 38)  # CMD_MOC_DMUCH
        set_p(9, 38, 1, 100, 38)  # CMD_MOC_DMUCH_PODT
        set_p(10, 10, 1, 100, 10)  # CMD_POD_CZASPRACY_PODT
        set_p(11, 20, 1, 60, 20)  # CMD_POD_PRZERWA_PODT
        set_p(12, 1, 1, 10, 1)  # CMD_POWT_PODT
        set_p(13, 20, 1, 60, 20)  # CMD_POD_POST_PODT
        set_p(14, 90, 60, 110, 90)  # CMD_POD_MAX_TEMP
        set_p(15, 60, 1, 100, 60)  # CMD_POD_CZAS_OBR
        set_p(16, 0, 0, 4, 0)  # CMD_CWU_TRYB_PRACY
        set_p(17, 50, 35, 65, 50)  # CMD_CWU_ZADANA
        set_p(18, 20, 2, 50, 10)  # CMD_CWU_HIST
        set_p(19, 2, 0, 2, 0)  # CMD_MIESZOBIEG_AKTYWACJA
        set_p(21, 0, 0, 3, 0)  # CMD_LANGUAGE
        set_p(22, 5, 1, 60, 5)  # CMD_OBIEG_CZASPRACY
        set_p(23, 15, 1, 60, 15)  # CMD_OBIEG_POSTOJ
        set_p(30, 60, 45, 80, 60)  # CMD_PROG_CO_M10
        set_p(31, 45, 40, 70, 45)  # CMD_PROG_CO_P10
        set_p(34, 10, 1, 60, 10)  # CMD_POD_CZASPRACY_GRZ
        set_p(35, 20, 1, 60, 20)  # CMD_POD_POST_GRZ
        set_p(38, 45, 42, 60, 45)  # CMD_CO_MIN
        set_p(39, 65, 65, 80, 80)  # CMD_CO_MAX
        set_p(40, 55, 45, 80, 55)  # CMD_CO_ZADANA
        set_p(41, 5, 0, 20, 5)  # CMD_CO_OBNIZONA
        set_p(50, 0, 0, 3, 0)  # CMD_ZADAWANIE
        set_p(51, 1, 0, 1, 1)  # CMD_TRYB_PRACY (1=Auto)
        set_p(69, 1, 0, 2, 0)  # CMD_POMPACO_TRYB
        set_p(70, 5, 1, 60, 5)  # CMD_POMPACO_PRACA
        set_p(71, 15, 1, 60, 30)  # CMD_POMPACO_POSTOJ
        set_p(76, 0, 0, 1, 0)  # CMD_AUTOLATO
        set_p(77, 10, 0, 25, 10)  # CMD_AUTOLATO_TEMP
        set_p(79, 600, 0, 1000, 600)  # CMD_PODAJNIK_CZASALARM
        set_p(80, 5, 1, 20, 5)  # CMD_REG_POK_HISTEREZA
        set_p(81, 10, 5, 50, 10)  # CMD_POMPA_CWU_HISTEREZA_AL
        set_p(88, 0, 0, 1, 0)  # CMD_POMPA_CWU_WYJSCIE
        set_p(89, 30, 0, 600, 30)  # CMD_ALARM_CZASOPOZNIENIA
        set_p(90, 0, 0, 1, 0)  # CMD_ALARM_INWERSJA
        set_p(91, 0, 0, 1, 0)  # CMD_ALARM_ZATRZYMANIE
        set_p(92, 4, 0, 5, 4)  # CMD_TYP_KOTLA
        set_p(93, 0, 0, 1, 0)  # CMD_AKTYWACJA_MIESZAJACA_LATO
        set_p(94, 0, -6, 6, 0)  # CMD_KOREKTA_DMUCHAWY_GRZANIE
        set_p(95, 0, 0, 3, 0)  # CMD_OKRES_REJESTRACJI

        # Extended parameters (>= 96)
        set_p(96, 250, 100, 350, 250)  # CMD_MAX_TEMP_SPALIN
        set_p(97, 45, 1, 100, 45)  # CMD_MOC_DMUCH_GRZ
        set_p(98, 1, 0, 1, 1)  # CMD_REGULATOR_SPALIN
        set_p(99, 10, 1, 50, 10)  # CMD_MIN_MOC_DMUCH
        set_p(100, 16, 8, 30, 16)  # CMD_ALG_MAXMOC
        set_p(101, 38, 1, 100, 38)  # CMD_ALG_MOCDMUCH8
        set_p(102, 40, 1, 100, 40)  # CMD_ALG_MOCDMUCH12
        set_p(103, 42, 1, 100, 42)  # CMD_ALG_MOCDMUCH16
        set_p(104, 45, 1, 100, 45)  # CMD_ALG_MOCDMUCH20
        set_p(105, 48, 1, 100, 48)  # CMD_ALG_MOCDMUCH25
        set_p(106, 8, 8, 30, 8)  # CMD_ALG_MINMOC
        set_p(107, 10, 1, 60, 10)  # CMD_ZASYP_CZASPRZEDMUCHU
        set_p(108, 15, 1, 60, 15)  # CMD_ZASYP_ODSTEPPRZEDMUCH
        set_p(109, 45, 1, 100, 45)  # CMD_ZASYP_MOCDMUCH
        set_p(110, 5, 1, 20, 5)  # CMD_ZASYP_STREFAAUTO
        set_p(111, 1, 0, 1, 1)  # CMD_ALG_WYGASZENIA
        set_p(112, 0, 0, 1, 0)  # CMD_PRIORYTET_CWU
        set_p(113, 40, 30, 60, 40)  # CMD_TEMP_ZAL_CYRK
        set_p(114, 0, 0, 1, 0)  # CMD_PRACA_AUTO_CYRK
        set_p(115, 45, 35, 70, 45)  # CMD_TEMP_ZAL_MIESZ
        set_p(116, 5, 1, 60, 5)  # CMD_PODLOGOWA_CZASPRACY
        set_p(117, 15, 1, 60, 15)  # CMD_PODLOGOWA_POSTOJ
        set_p(118, 20, 1, 60, 20)  # CMD_CZAS_POSTOJU_GRZANIE
        set_p(119, 1, 0, 3, 1)  # CMD_TYP_PODAJNIKA (1=grupowe, 2=ecoal)
        set_p(120, 2, 1, 10, 2)  # CMD_HIST_TEMP_CO
        set_p(121, 5, 0, 20, 5)  # CMD_PODBICIE_TEMP
        set_p(122, 60, 10, 300, 60)  # CMD_PODAJNIK_CZASWYRZUTU
        set_p(123, 5, 1, 60, 5)  # CMD_PRACA_POMPCOPODL
        set_p(124, 15, 1, 60, 15)  # CMD_POSTOJ_POMPCOPODL
        set_p(125, 52, 1, 100, 52)  # CMD_ALG_MOCDMUCH30
        set_p(126, 4, 1, 15, 4)  # CMD_ALG_ILGRUP8
        set_p(127, 5, 1, 15, 5)  # CMD_ALG_ILGRUP12
        set_p(128, 6, 1, 15, 6)  # CMD_ALG_ILGRUP16
        set_p(129, 7, 1, 15, 7)  # CMD_ALG_ILGRUP20
        set_p(130, 8, 1, 15, 8)  # CMD_ALG_ILGRUP25
        set_p(131, 9, 1, 15, 9)  # CMD_ALG_ILGRUP30
        set_p(132, 1, 0, 1, 1)  # CMD_CZUJNIK_ZAMZAS
        set_p(133, 1, 0, 1, 1)  # CMD_CZUJNIK_ZERZAW

        return p

    def build_status_payload(self) -> list[int]:
        """Build 76 data bytes for CMD_STATUS (matching exact eCoal layout)."""
        data = [0] * 76
        # Sensor states (bytes 0..7 in data, 8..15 in frame): 0 = OK, 1 = disconnected
        # 0: CO, 1: CWU, 2: Powrot, 3: Podajnik, 4: Spaliny, 5: Zew, 6: Wew, 7: Podlog
        for i in range(8):
            data[i] = 0

        # SENSOR_NAMES: floor, indoor, outdoor, dhw, return, feeder, boiler, exhaust
        temps = [
            self.floor_temp,
            self.inside_temp,
            self.outside_temp,
            self.dhw_temp,
            self.return_temp,
            self.feeder_temp,
            self.boiler_temp,
            self.exhaust_temp,
        ]
        for i, t in enumerate(temps):
            val = t if t >= 0 else t + 65536
            data[8 + i * 2] = val & 0xFF
            data[8 + i * 2 + 1] = (val >> 8) & 0xFF

        # Outputs (byte 24 in data, 32 in frame)
        data[24] = self.outputs_byte

        # Control states (bytes 25..31 in data, 33..39 in frame)
        data[25] = self.heating
        data[26] = self.auto_mode
        data[27] = self.setpoint_mode
        data[28] = self.cwu_mode
        data[29] = self.params.get(40, [55])[0]  # Target boiler temp
        data[30] = self.params.get(17, [50])[0]  # Target DHW temp
        data[31] = self.air_pump_power

        # Alarms (bytes 32..33 in data, 40..41 in frame)
        data[32] = self.alarms_raw & 0xFF
        data[33] = (self.alarms_raw >> 8) & 0xFF

        # Mixer circuit and Auth (bytes 34..35 in data, 42..43 in frame)
        data[34] = 2  # Mixer circuit mode
        data[35] = 2  # Auth level = 2 (Admin)

        # Time: Y(+2000), M, D, H, Min, Sec (bytes 36..41 in data, 44..49 in frame)
        now = time.localtime()
        data[36] = now.tm_year - 2000
        data[37] = now.tm_mon
        data[38] = now.tm_mday
        data[39] = now.tm_hour
        data[40] = now.tm_min
        data[41] = now.tm_sec

        # Feeder runtime (bytes 56..59 in data, 64..67 in frame): 32-bit LE seconds
        rt = self.feeder_runtime_sec
        data[56] = rt & 0xFF
        data[57] = (rt >> 8) & 0xFF
        data[58] = (rt >> 16) & 0xFF
        data[59] = (rt >> 24) & 0xFF

        # Fuel percentage (byte 67 in data, 75 in frame)
        data[67] = max(0, min(100, self.fuel_load_pct))

        return data


class EcoalMockHandler(BaseHTTPRequestHandler):
    """HTTP handler processing ?com=<HEX> requests for eCoal simulator."""

    server_version = "eCoal_Simulator/1.0"

    def log_message(self, format: str, *args: object) -> None:
        _LOGGER.debug("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        params = parse_qs(url.query)

        if "com" not in params:
            # Simple health / info check
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"eCoal Virtual Furnace Simulator OK\n")
            return

        hex_cmd = params["com"][0].strip()
        resp_bytes = self.process_command(hex_cmd)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        # eCoal returns array as JSON text: [2, 1, 6, ...]
        resp_str = str(resp_bytes)
        self.wfile.write(resp_str.encode("ascii"))

    def process_command(self, hex_cmd: str) -> list[int]:
        state: VirtualFurnaceState = self.server.furnace_state  # type: ignore

        try:
            req_bytes = [int(hex_cmd[i : i + 2], 16) for i in range(0, len(hex_cmd), 2)]
        except ValueError:
            return build_response_frame(21, 0, 0, 0)

        if len(req_bytes) < 10 or req_bytes[0] != 0x02 or req_bytes[-1] != 0x03:
            return build_response_frame(21, 0, 0, 0)

        # Parse request frame
        # [0]=STX, [1]=ADR, [2]=Status, [3]=Cmd1, [4]=Cmd2, [5]=Cmd3, [6]=LenL, [7]=LenH, [8..]=Data, [last-1]=CRC
        cmd1 = req_bytes[3]
        cmd2 = req_bytes[4]
        cmd3 = req_bytes[5]
        data_len = req_bytes[6] | (req_bytes[7] << 8)
        data = req_bytes[8 : 8 + data_len]

        # Verify CRC
        calc = calc_crc(req_bytes[1:-2])
        if calc != req_bytes[-2]:
            return build_response_frame(21, cmd1, cmd2, cmd3)

        # Dispatch command
        if cmd1 == 0x06:
            # CMD_STATUS
            status_data = state.build_status_payload()
            return build_response_frame(6, 6, 0, 0, status_data)

        if cmd1 == 0x01:
            # CMD_GET_PARAM (Cmd3 = param_id)
            pid = cmd3
            if pid in state.params:
                pinfo = state.params[pid]
                val = pinfo[0] if pinfo[0] >= 0 else pinfo[0] + 65536
                pmin = pinfo[1] if pinfo[1] >= 0 else pinfo[1] + 65536
                pmax = pinfo[2] if pinfo[2] >= 0 else pinfo[2] + 65536
                pdef = pinfo[3] if pinfo[3] >= 0 else pinfo[3] + 65536

                # Firmware v0.2.9.16a quirk simulation:
                # Real furnace returns Status 21 (NAK) with 2 bytes for params >= 96!
                # If simulate_quirk is False (improved), it returns Status 6 (ACK).
                if pid >= 96 and getattr(self.server, "simulate_quirk", False):  # type: ignore
                    resp_data = [val & 0xFF, (val >> 8) & 0xFF]
                    return build_response_frame(21, 1, 0, pid, resp_data)

                resp_data = [
                    val & 0xFF,
                    (val >> 8) & 0xFF,
                    pmin & 0xFF,
                    (pmin >> 8) & 0xFF,
                    pmax & 0xFF,
                    (pmax >> 8) & 0xFF,
                    pdef & 0xFF,
                    (pdef >> 8) & 0xFF,
                ]
                return build_response_frame(6, 1, 0, pid, resp_data)
            return build_response_frame(21, 1, 0, pid)

        if cmd1 == 0x02:
            # CMD_SET_PARAM (Cmd3 = param_id, Data = [valL, valH])
            pid = cmd3
            if len(data) >= 2 and pid in state.params:
                val = data[0] | (data[1] << 8)
                if val > 32767:
                    val -= 65536
                # Update param value
                state.params[pid][0] = val

                # If setting target temp, update quick state
                if pid == 40:
                    state.boiler_temp = int(val * 10)
                elif pid == 17:
                    state.dhw_temp = int(val * 10)
                elif pid == 119:
                    # Feeder mode updated
                    pass

                # Return ACK with 0 data bytes
                return build_response_frame(6, 2, 0, pid)
            return build_response_frame(21, 2, 0, pid)

        if cmd1 == 0x05:
            # CMD_CFG
            if cmd3 == 22:
                # CMD_CFG_START (Start handshake)
                # Returns 53 bytes: auth, zad_co, min, max, obn_co, ..., version string
                ver = b"0.2.9.16"
                start_data = [
                    2,  # auth (2 = admin)
                    55,  # zad_co
                    35,  # zad_co_min
                    80,  # zad_co_max
                    10,
                    0,
                    30,  # obn_co
                    53,
                    35,
                    60,  # zad_cwu
                    10,
                    0,
                    20,  # obn_cwu
                    2,
                    0,
                    2,  # mieszobieg
                    190,
                    0,
                    50,
                    0,
                    94,
                    1,
                    170,
                    0,
                    50,
                    0,
                    94,
                    1,
                    88,
                    2,
                    len(ver),
                ]
                start_data += list(ver)
                start_data += [
                    210,
                    0,
                    50,
                    0,
                    94,
                    1,
                    190,
                    0,
                    50,
                    0,
                    94,
                    1,
                    0,
                    0,
                ]
                return build_response_frame(6, 5, 0, 22, start_data)

            if cmd3 == 24:
                # CMD_CFG_CZASPRACYPOD_ZERUJ (Reset feeder runtime counter)
                state.feeder_runtime_sec = 0
                state.fuel_load_pct = 100
                return build_response_frame(6, 5, 0, 24)

            if cmd3 == 9:
                # CMD_CFG_ACK_ALARM (Acknowledge alarms)
                state.alarms_raw = 0
                return build_response_frame(6, 5, 0, 9)

            if cmd3 == 26:
                # CMD_CFG_SPALANIEGRUPOWE
                return build_response_frame(6, 5, 0, 26, [10, 20, 30, 40, 50, 60])

        return build_response_frame(21, cmd1, cmd2, cmd3)


class EcoalMockServer(ThreadingHTTPServer):
    """Threading HTTP Server running VirtualFurnaceState."""

    def __init__(
        self,
        server_address: tuple[str, int],
        simulate_quirk: bool = False,
    ) -> None:
        super().__init__(server_address, EcoalMockHandler)
        self.furnace_state = VirtualFurnaceState()
        self.simulate_quirk = simulate_quirk


def main() -> None:
    parser = argparse.ArgumentParser(description="eCoal Virtual Furnace Simulator")
    parser.add_argument("--host", default="127.0.0.1", help="Bind IP address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Listen port (default: 8080)")
    parser.add_argument(
        "--quirk",
        action="store_true",
        help="Simulate firmware bug (NAK 21 on params >= 96)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    server = EcoalMockServer((args.host, args.port), simulate_quirk=args.quirk)
    _LOGGER.info("Starting eCoal Virtual Furnace Simulator on http://%s:%d", args.host, args.port)
    _LOGGER.info("Simulate NAK(21) quirk on PARAM >= 96: %s", args.quirk)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down simulator.")
        server.server_close()


if __name__ == "__main__":
    main()
