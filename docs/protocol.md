# eCoal Furnace Protocol Documentation

## Hardware
- **Furnace brand**: Various (tested with Ogniwo Biecz)
- **Controller**: eCoal.pl by eSterownik.pl
- **Tested firmware**: v0.2.9.16a
- **Web panel**: port 80 (HTTP only)

## Communication Protocol

### Transport
HTTP GET with Basic Auth over port 80:
```
GET http://<host>/?com=<hex_encoded_frame>
```

Response: `text/plain`, JSON-like array of integers: `[2,1,6,6,0,0,76,...]`

### Command Frame Format
```
| STX | ADDR_HI | ADDR_LO | CMD | 0x00 | PARAM | LEN | 0x00 | DATA... | CRC | ETX |
| 02  |   01    |   00    | XX  |  00  |  XX   | XX  |  00  | XX...   | XX  | 03  |
```

- **STX**: 0x02 (start)
- **ETX**: 0x03 (end)
- **CRC**: CRC-8 over bytes between STX and CRC (exclusive), using standard CRC table

### CRC-8 Table
```python
CRCTABLE = (
    0,49,98,83,196,245,166,151,185,136,219,234,125,76,31,46,
    67,114,33,16,135,182,229,212,250,203,152,169,62,15,92,109,
    134,183,228,213,66,115,32,17,63,14,93,108,251,202,153,168,
    197,244,167,150,1,48,99,82,124,77,30,47,184,137,218,235,
    61,12,95,110,249,200,155,170,132,181,230,215,64,113,34,19,
    126,79,28,45,186,139,216,233,199,246,165,148,3,50,97,80,
    187,138,217,232,127,78,29,44,2,51,96,81,198,247,164,149,
    248,201,154,171,60,13,94,111,65,112,35,18,133,180,231,214,
    122,75,24,41,190,143,220,237,195,242,161,144,7,54,101,84,
    57,8,91,106,253,204,159,174,128,177,226,211,68,117,38,23,
    252,205,158,175,56,9,90,107,69,116,39,22,129,176,227,210,
    191,142,221,236,123,74,25,40,6,55,100,85,194,243,160,145,
    71,118,37,20,131,178,225,208,254,207,156,173,58,11,88,105,
    4,53,102,87,192,241,162,147,189,140,223,238,121,72,27,42,
    193,240,163,146,5,52,103,86,120,73,26,43,188,141,222,239,
    130,179,224,209,70,119,36,21,59,10,89,104,255,206,157,172,
)

def calc_crc(buf):
    """Calculate CRC over payload bytes (between STX and CRC position)."""
    crc = 0
    for byte in buf:
        crc = CRCTABLE[crc & 0xFF ^ byte & 0xFF]
    return crc
```

---

## Commands

### Read Status (CMD 0x06)
```
Hex: 02010006000000006103
Frame: 02 | 01 00 06 00 00 00 00 | 61 | 03
```
Returns: 86 bytes (84 data + STX + ETX)

### Read Settings (CMD 0x05, PARAM 0x16)
```
Hex: 02010005001600002403
Frame: 02 | 01 00 05 00 16 00 00 | 24 | 03
```
Returns: settings array including firmware version string

### Read Version (CMD 0x05, PARAM 0x02)
```
Hex: 0201000500020000A903
```
Response bytes [8:11]: firmware version identifier

### Read Feeder Max Runtime (CMD 0x01, PARAM 0x4F)
```
Hex: 02010001004F00007903
```
Response: `vals[9]<<8 | vals[8]` = max feeder time in minutes

### Set Commands

#### On/Off Controls (CMD 0x05)
| Device              | PARAM | ON hex                           | OFF hex                          |
|---------------------|-------|----------------------------------|----------------------------------|
| Air pump (dmuchawa) | 0x0B  | `02010005000B0100018403`         | `02010005000B0100008503` |
| Coal feeder         | 0x0C  | `02010005000C0100011603`         | `02010005000C0100002703`         |
| CH pump (pompa CO)  | 0x0D  | `02010005000D0100018D03`         | `02010005000D010000BC03`         |
| DHW pump (pompa CWU)| 0x0E  | `02010005000E0100011103`         | `02010005000E0100002003`         |
| CH pump 2           | 0x0F  | (calculated with CRC)            | (calculated with CRC)            |
| Auto mode           | 0x33* | `020100020033020001006503`       | `020100020033020000009103`       |

*Auto mode uses CMD 0x02, not 0x05

#### Value Controls (CMD 0x02)
| Parameter                | PARAM | Encoding       |
|--------------------------|-------|----------------|
| Air pump power           | 0x08  | 1 byte (0-100%)|
| Target feedwater temp    | 0x28  | 1 byte (°C)    |
| Manual feeder time       | 0x52  | 2 bytes LE (s) |
| Feeder max runtime (alarm)| 0x4F | 2 bytes LE (min)|
| Blower power correction  | 0x5E  | 2 bytes signed LE (-6..+6 %) |
| Exhaust temp regulator   | 0x62  | 2 bytes LE (0=off, 1=on) |
| DHW priority             | 0x70  | 2 bytes LE (0=off, 1=on) |
| Feeder combustion mode   | 0x77  | 2 bytes LE (0=manual, 1=group, 2=eCoal, 3=batch) |
| Manual stop time         | 0x76  | 2 bytes LE (s) |
| Manual air pump power    | 0x61  | 1 byte (%)     |

#### Configuration Commands (CMD 0x05)
| Action                   | Subcmd | Data format | Hex example |
|--------------------------|--------|-------------|-------------|
| Set date & time          | 0x06   | 6 bytes: [Y-2000, M, D, H, Min, Sec] | `02010005000606001a0a10161500...03` |
| Acknowledge alarms       | 0x09   | 1 byte: `0x00` | `020100050009010000...03` |
| Reset feeder / refill    | 0x18 (24) | 2 bytes LE (kg of coal) | `020100050018020096009803` (150 kg) |


---

## Status Response Byte Map (86 bytes total)

### Header (bytes 0-15)
| Index | Description |
|-------|-------------|
| 0     | STX (start of frame) |
| 1     | Address high |
| 2     | Address low / command echo |
| 3     | Command echo |
| 4     | Unknown |
| 5     | Unknown |
| 6     | Unknown (stable) |
| 7     | Unknown |
| 8-10  | Version bytes |
| 11-15 | Unknown (all zero) |

### Temperatures (bytes 16-31)
16-bit signed little-endian, divide by 10.0 for °C.
Formula: `temp = ((hi << 8 | lo) - (hi >> 7 << 16)) / 10.0`

| Index   | Sensor                    | Polish              |
|---------|---------------------------|----------------------|
| [16,17] | Floor / unknown           | T. podłogowa         |
| [18,19] | Indoor temperature        | T. wewnętrzna        |
| [20,21] | Outdoor temperature       | T. zewnętrzna        |
| [22,23] | DHW temperature           | T. CWU               |
| [24,25] | Feedwater return temp     | T. powrotu           |
| [26,27] | Fuel feeder temperature   | T. podajnika         |
| [28,29] | Feedwater output (boiler) | T. CO (kotła)        |
| [30,31] | Exhaust / flue gas temp   | T. spalin            |

### Actuator States (byte 32)
Bitmask:
| Bit | Mask | Device                 | Polish          |
|-----|------|------------------------|-----------------|
| 0   | 0x01 | Air pump (blower)      | Dmuchawa        |
| 1   | 0x02 | Coal feeder            | Podajnik        |
| 2   | 0x04 | Central heating pump   | Pompa CO        |
| 3   | 0x08 | DHW pump               | Pompa CWU       |
| 4   | 0x10 | CH pump 2 / mixing     | Pompa mieszająca|

### Control State (bytes 33-39)
| Index | Description              |
|-------|--------------------------|
| 33    | Heating state            |
| 34    | Auto mode (1=auto, 0=manual) |
| 35    | Setpoint mode            |
| 36    | CWU work mode            |
| 37    | Target feedwater temp (°C) |
| 38    | Target DHW temp (°C)     |
| 39    | Current air pump power (%) |

### Alarms and Flags (bytes 40-63)
| Index   | Description |
|---------|-------------|
| [40,41] | Alarms bitmask (16-bit LE) |
| 42      | Mixer circuit mode |
| 43      | Auth level |
| [44-49] | Date/time: Y(+2000), M, D, H, Min, Sec |
| 50      | CO lowered active flag |
| 51      | CWU lowered active flag |
| 52      | Room heating mode |
| 53      | Internal setpoint |
| 54      | Day/night flag |
| [55,56] | Room day temp (signed LE / 10) |
| [57,58] | Room night temp (signed LE / 10) |
| 59      | CO lowered amount (°C) |
| 60      | CWU lowered amount (°C) |
| 61      | Inputs bitmask |
| [62,63] | Alarms2 bitmask (16-bit LE) |

### Feeder Runtime (bytes 64-67)
32-bit unsigned little-endian, value in seconds.

### Fuel Data (bytes 68-77)
| Index   | Description |
|---------|-------------|
| [68-72] | Fuel load date (Y+2000, M, D, H, Min) |
| [73,74] | Fuel remaining (16-bit LE) |
| 75      | Fuel load percentage |
| 76      | Feeding percentage |
| 77      | Fuel remaining high byte |

### Floor Heating (bytes 78-83)
| Index   | Description |
|---------|-------------|
| [78,79] | Floor day temp (signed LE / 10) |
| [80,81] | Floor night temp (signed LE / 10) |
| 82      | Floor day/night flag |
| 83      | Summer mode flag |

### CRC and ETX (bytes 84-85)
| Index | Description |
|-------|-------------|
| 84    | CRC-8       |
| 85    | ETX (end)   |

---

## Settings Response Byte Map

Command: `02010005001600002403` (CMD 0x05, read from offset 0x16=22)

Key fields:
| Index   | Description |
|---------|-------------|
| 8       | Boiler type |
| 9       | Target feedwater temp (°C) |
| 11      | Max feedwater temp (°C) |
| 15      | Target DHW temp (°C) |
| 17      | Max DHW temp (°C) |
| 24      | Max exhaust temp alarm (°C) |
| 30      | Max boiler temp alarm (°C) |
| 38      | Firmware version string length |
| [39..]  | Firmware version (ASCII) |

---

## Existing Libraries
- **ecoaliface** (v0.7.0): Python, supports v0.1 (Bruli) and v0.3 (Ecoal) only
- **sterownik**: Python, original library, same protocol
- **HA ecoal_boiler**: official integration, uses ecoaliface, treats device as boiler

## Known Limitations
- Firmware v0.2 not recognized by ecoaliface (version check fails)
- Web panel sends broken gzip (truncated responses)
- `getregister.cgi` API (newer Pello v3.5+) not supported on v0.2
- `/?com=sc` shorthand sometimes returns empty body when eSterownik cloud is connected

---

## Pełny rejestr parametrów sterownika (PARAM 0–133) oraz mapa encji HA

Poniższa tabela stanowi kompletny rejestr parametrów eCoal (odczytany z firmware panelu `www_eCoal.pl`), powiązany ze stałymi w [`client.py`](../custom_components/ecoal/client.py).
Dla każdego parametru zdefiniowano:
* **Stałą w kodzie integracji** (`PARAM_*`)
* **Dokładne przeznaczenie fizyczne / algorytmiczne**
* **Proponowaną docelową encję Home Assistant** (wraz z sugerowaną domeną: `number`, `switch`, `select`, `sensor`, `binary_sensor`)
* **Zakres wartości i jednostkę**
* **Aktualny status implementacji w integracji** (✅ Wdrożone vs 💡 Niewdrożone)

| Dec | Hex | Stała `PARAM_*` | Opis parametru | Proponowana encja HA | Zakres / Jednostka | Status w HA |
|:---:|:---:|:---|:---|:---|:---:|:---|
| 0 | `0x00` | `PARAM_OFFSET_Z1` | Offset czujnika temp. Z1 | `number.offset_z1` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 1 | `0x01` | `PARAM_OFFSET_WEW` | Offset czujnika pokojowego | `number.offset_wew` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 2 | `0x02` | `PARAM_OFFSET_ZEW` | Offset czujnika zewnętrznego | `number.offset_zew` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 3 | `0x03` | `PARAM_OFFSET_CWU` | Offset czujnika CWU | `number.offset_cwu` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 4 | `0x04` | `PARAM_OFFSET_POW` | Offset czujnika powrotu | `number.offset_powrot` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 5 | `0x05` | `PARAM_OFFSET_POD` | Offset czujnika podajnika | `number.offset_podajnik` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 6 | `0x06` | `PARAM_OFFSET_CO` | Offset czujnika kotła CO | `number.offset_co` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 7 | `0x07` | `PARAM_OFFSET_SPA` | Offset czujnika spalin | `number.offset_spaliny` | °C (-10..+10) | 💡 Niewdrożone (kalibracja) |
| 8 | `0x08` | `PARAM_MOC_DMUCH` | Moc dmuchawy w grzaniu | `sensor.air_pump_power` | % (0-100) | ✅ **sensor.air_pump_power** |
| 9 | `0x09` | `PARAM_MOC_DMUCH_PODT` | Moc dmuchawy w podtrzymaniu | `number.moc_dmuch_podtrzymanie` | % (0-100) | 💡 Niewdrożone (podtrzymanie) |
| 10 | `0x0A` | `PARAM_POD_CZASPRACY_PODT` | Czas pracy podajnika w podtrzymaniu | `number.czas_pracy_podajnik_podtrzymanie` | s (1-100) | 💡 Niewdrożone (podtrzymanie) |
| 11 | `0x0B` | `PARAM_POD_PRZERWA_PODT` | Czas krótkiej przerwy w podtrzymaniu | `number.czas_przerwy_podajnik_podtrzymanie` | s (1-100) | 💡 Niewdrożone (podtrzymanie) |
| 12 | `0x0C` | `PARAM_POWT_PODT` | Ilość powtórzeń cyklu podtrzymania | `number.ilosc_powtorzen_podtrzymanie` | ilość (1-10) | 💡 Niewdrożone (podtrzymanie) |
| 13 | `0x0D` | `PARAM_POD_POST_PODT` | Czas postoju podajnika w podtrzymaniu | `number.czas_postoju_podajnik_podtrzymanie` | min (1-100) | 💡 Niewdrożone (podtrzymanie) |
| 14 | `0x0E` | `PARAM_POD_MAX_TEMP` | Maksymalna dopuszczalna temp. podajnika (alarm żaru) | `number.max_temp_podajnika_alarm` | °C (40-90) | 💡 Niewdrożone (bezpieczeństwo) |
| 15 | `0x0F` | `PARAM_POD_CZAS_OBR` | Czas pełnego obrotu ślimaka podajnika | `number.czas_obrotu_podajnika` | s | 💡 Niewdrożone (serwis) |
| 16 | `0x10` | `PARAM_CWU_TRYB_PRACY` | Tryb pracy CWU (zima, lato, auto, prog, off) | `climate.cwu_mode` | 0-4 | ✅ **climate.hot_water / sensor.cwu_mode** |
| 17 | `0x11` | `PARAM_CWU_ZADANA` | Temperatura zadana CWU | `climate.target_dhw_temp` | °C (30-65) | ✅ **climate.hot_water / sensor.target_dhw_temp** |
| 18 | `0x12` | `PARAM_CWU_HIST` | Histereza temperatury CWU | `number.cwu_histereza` | °C (1-10) | 💡 Niewdrożone (histereza CWU) |
| 19 | `0x13` | `PARAM_MIESZOBIEG_AKTYWACJA` | Aktywacja obiegu mieszacza / pompy podłogowej | `switch.mixer_pump` | 0/1 | ✅ **switch.mixer_pump** |
| 21 | `0x15` | `PARAM_LANGUAGE` | Język menu sterownika | `select.jezyk` | PL/EN/CZ/DE | 💡 Niewdrożone (interfejs) |
| 22 | `0x16` | `PARAM_OBIEG_CZASPRACY` | Czas pracy pompy cyrkulacyjnej CWU | `number.czas_pracy_cyrkulacja` | s/min | 💡 Niewdrożone (cyrkulacja) |
| 23 | `0x17` | `PARAM_OBIEG_POSTOJ` | Czas postoju pompy cyrkulacyjnej CWU | `number.czas_postoju_cyrkulacja` | min | 💡 Niewdrożone (cyrkulacja) |
| 24 | `0x18` | `PARAM_PROG_CO_TAB` | Harmonogram tygodniowy CO | `schedule.co_weekly_program` | 42 bajty | ✅ **Obsługiwane w API client.py** |
| 25 | `0x19` | `PARAM_PROG_CWU_TAB` | Harmonogram tygodniowy CWU | `schedule.cwu_weekly_program` | 42 bajty | ✅ **Obsługiwane w API client.py** |
| 26 | `0x1A` | `PARAM_PROG_POGODOWY_TAB` | Harmonogram pogodowy CO | `schedule.weather_weekly_program` | 42 bajty | 💡 Niewdrożone (harmonogram) |
| 27 | `0x1B` | `PARAM_PROG_POKOJOWY_TAB` | Harmonogram regulatora pokojowego | `schedule.room_weekly_program` | 42 bajty | 💡 Niewdrożone (harmonogram) |
| 28 | `0x1C` | `PARAM_PROG_OBIEG_TAB` | Harmonogram pompy cyrkulacyjnej | `schedule.circ_weekly_program` | 42 bajty | 💡 Niewdrożone (harmonogram) |
| 29 | `0x1D` | `PARAM_PROG_CWU_OBNIZONA` | Wartość obniżenia temperatury CWU z programu | `sensor.cwu_lowered_amount` | °C | ✅ **sensor.cwu_lowered_amount** |
| 30 | `0x1E` | `PARAM_PROG_CO_M10` | Krzywa grzania: temp. zadana CO dla -10°C na zewnątrz | `number.krzywa_pogodowa_m10` | °C (30-80) | 💡 Niewdrożone (sterowanie pogodowe) |
| 31 | `0x1F` | `PARAM_PROG_CO_P10` | Krzywa grzania: temp. zadana CO dla +10°C na zewnątrz | `number.krzywa_pogodowa_p10` | °C (30-80) | 💡 Niewdrożone (sterowanie pogodowe) |
| 32 | `0x20` | `PARAM_PROG_POKOJOWY_DZIENNA` | Regulator pokojowy: zadana temperatura dzienna | `sensor.room_day_temp` | °C | ✅ **sensor.room_day_temp** |
| 33 | `0x21` | `PARAM_PROG_POKOJOWY_NOCNA` | Regulator pokojowy: zadana temperatura nocna | `sensor.room_night_temp` | °C | ✅ **sensor.room_night_temp** |
| 34 | `0x22` | `PARAM_POD_CZASPRACY_GRZ` | Czas pracy podajnika w grzaniu ręcznym | `number.czas_pracy_podajnik_grzanie` | s (1-60) | 💡 Niewdrożone (tryb ręczny) |
| 35 | `0x23` | `PARAM_POD_POST_GRZ` | Czas postoju podajnika w grzaniu ręcznym | `number.czas_postoju_podajnik_grzanie` | s (5-300) | 💡 Niewdrożone (tryb ręczny) |
| 38 | `0x26` | `PARAM_CO_MIN` | Minimalna dopuszczalna temperatura zadana CO | `number.co_min_temp` | °C (40-60) | 💡 Niewdrożone (limit bezpieczeństwa) |
| 39 | `0x27` | `PARAM_CO_MAX` | Maksymalna dopuszczalna temperatura zadana CO | `number.co_max_temp` | °C (70-90) | 💡 Niewdrożone (limit bezpieczeństwa) |
| 40 | `0x28` | `PARAM_CO_ZADANA` | Temperatura zadana kotła CO | `climate.target_boiler_temp` | °C (45-80) | ✅ **climate.heating / sensor.target_boiler_temp** |
| 41 | `0x29` | `PARAM_CO_OBNIZONA` | Wartość obniżenia temperatury CO | `sensor.co_lowered_amount` | °C | ✅ **sensor.co_lowered_amount** |
| 45 | `0x2D` | `PARAM_IP` | Adres IP sterownika | `text.ip_address` | IPv4 | 💡 Niewdrożone (sieć) |
| 46 | `0x2E` | `PARAM_MASKA` | Maska podsieci | `text.netmask` | IPv4 | 💡 Niewdrożone (sieć) |
| 47 | `0x2F` | `PARAM_BRAMA` | Brama domyślna | `text.gateway` | IPv4 | 💡 Niewdrożone (sieć) |
| 50 | `0x32` | `PARAM_ZADAWANIE` | Tryb zadawania temperatury CO (0=stała/program, 1=pogodowy) | `sensor.setpoint_mode` | 0/1 | ✅ **sensor.setpoint_mode** |
| 51 | `0x33` | `PARAM_TRYB_PRACY` | Tryb pracy kotła (0=ręczny, 1=automatyczny) | `switch.auto_mode` | 0/1 | ✅ **switch.auto_mode** |
| 52 | `0x34` | `PARAM_CHARAKTER_DMUCHAWY` | Charakterystyka wentylatora nadmuchowego | `select.typ_wentylatora` | typ | 💡 Niewdrożone (instalator) |
| 53 | `0x35` | `PARAM_MIN_MOC_DMUCH` | Minimalna moc dmuchawy w modulacji | `number.min_moc_dmuchawy` | % (1-100) | 💡 Niewdrożone (strojenie dmuchawy) |
| 54 | `0x36` | `PARAM_MAX_MOC_DMUCH` | Maksymalna moc dmuchawy w modulacji | `number.max_moc_dmuchawy` | % (1-100) | 💡 Niewdrożone (strojenie dmuchawy) |
| 55 | `0x37` | `PARAM_MOC_DMUCH_MIN1` | Parametr minimalnej mocy dmuchawy 1 | `number.moc_dmuchawy_min_1` | % | 💡 Niewdrożone (serwis) |
| 56 | `0x38` | `PARAM_MOC_DMUCH_START` | Moc dmuchawy podczas rozpalania | `number.moc_dmuchawy_rozpalanie` | % | 💡 Niewdrożone (rozpalanie) |
| 57 | `0x39` | `PARAM_MOC_DMUCH_DOPAL` | Moc dmuchawy podczas dopalania | `number.moc_dmuchawy_dopalanie` | % | 💡 Niewdrożone (dopalanie) |
| 58 | `0x3A` | `PARAM_PODAWANIE_POD_START` | Czas podawania paliwa na starcie | `number.czas_podawania_rozpalanie` | s | 💡 Niewdrożone (rozpalanie) |
| 59 | `0x3B` | `PARAM_PODAWANIE_POD_2` | Czas podawania paliwa 2 | `number.czas_podawania_2` | s | 💡 Niewdrożone |
| 60 | `0x3C` | `PARAM_MIN_PODAWANIE_POD` | Minimalny czas podawania | `number.min_czas_podawania` | s | 💡 Niewdrożone |
| 61 | `0x3D` | `PARAM_MAX_PODAWANIE_POD` | Maksymalny czas podawania | `number.max_czas_podawania` | s | 💡 Niewdrożone |
| 66 | `0x42` | `PARAM_MAC` | Adres fizyczny karty sieciowej sterownika | `sensor.mac_address` | MAC | 💡 Niewdrożone (sieć) |
| 67 | `0x43` | `PARAM_AUTORYZACJA_USER` | Dane autoryzacji konta użytkownika | `text.user_credentials` | login/hasło | 💡 Niewdrożone (bezpieczeństwo) |
| 68 | `0x44` | `PARAM_AUTORYZACJA_ADMIN` | Dane autoryzacji konta administratora | `text.admin_credentials` | login/hasło | 💡 Niewdrożone (bezpieczeństwo) |
| 69 | `0x45` | `PARAM_POMPACO_TRYB` | Cykliczna praca pompy CO po dogrzaniu pokoju | `switch.praca_cykliczna_pompy_co` | 0/1 | 💡 Niewdrożone (praca cykliczna) |
| 70 | `0x46` | `PARAM_POMPACO_PRACA` | Czas pracy pompy CO w cyklu | `number.czas_pracy_pompa_co_cykl` | min (0-60) | 💡 Niewdrożone (praca cykliczna) |
| 71 | `0x47` | `PARAM_POMPACO_POSTOJ` | Czas postoju pompy CO w cyklu | `number.czas_postoju_pompa_co_cykl` | min (0-60) | 💡 Niewdrożone (praca cykliczna) |
| 72 | `0x48` | `PARAM_SERWER_PORT` | Port serwera zdalnego eSterownik.pl | `number.port_serwera_zdalnego` | port | 💡 Niewdrożone (chmura) |
| 73 | `0x49` | `PARAM_SERWER_ID` | Identyfikator urządzenia na serwerze eSterownik | `text.id_serwera_zdalnego` | ID | 💡 Niewdrożone (chmura) |
| 74 | `0x4A` | `PARAM_SERWER_AKTYWACJA` | Aktywacja połączenia z serwerem eSterownik.pl | `switch.chmura_esterownik_aktywna` | 0/1 | 💡 Niewdrożone (chmura) |
| 75 | `0x4B` | `PARAM_SERWER_IP` | Adres IP serwera eSterownik.pl | `text.ip_serwera_zdalnego` | IPv4 | 💡 Niewdrożone (chmura) |
| 76 | `0x4C` | `PARAM_AUTOLATO` | Automatyczne przełączanie w tryb letni wg temp. zewn. | `switch.auto_lato_aktywne` | 0/1 | 💡 Niewdrożone (auto-lato) |
| 77 | `0x4D` | `PARAM_AUTOLATO_TEMP` | Temperatura zewnętrzna załączenia trybu Auto-Lato | `number.auto_lato_temp_graniczna` | °C (10-30) | 💡 Niewdrożone (auto-lato) |
| 78 | `0x4E` | `PARAM_WEW_ZADAWANIE` | Wybór regulatora pokojowego (0=wył, 1=program, 2=termostat) | `select.tryb_regulatora_pokojowego` | 0-2 | 💡 Niewdrożone (regulator pokojowy) |
| 79 | `0x4F` | `PARAM_PODAJNIK_CZASALARM` | Czas pracy podajnika do opróżnienia zasobnika | `number.feeder_max_runtime` | min (0-10000) | ✅ **number.feeder_max_runtime** |
| 80 | `0x50` | `PARAM_REG_POK_HISTEREZA` | Histereza regulatora temperatury pokojowej | `number.histereza_pokojowa` | °C (0.2-5.0) | 💡 Niewdrożone (regulator pokojowy) |
| 81 | `0x51` | `PARAM_POMPA_CWU_HISTEREZA_AL` | Histereza alarmu pompy CWU | `number.histereza_alarmu_cwu` | °C | 💡 Niewdrożone |
| 82 | `0x52` | `PARAM_PODAJNIK_CZASPRACY_GRZANIE` | Czas podawania paliwa w grzaniu | `number.czas_podawania_grzanie_2` | s | 💡 Niewdrożone |
| 83 | `0x53` | `PARAM_PROG_AUTOLATO` | Harmonogram blokowania trybu Auto-Lato | `schedule.auto_lato_program` | 42 bajty | 💡 Niewdrożone (harmonogram) |
| 84 | `0x54` | `PARAM_PODL_DZIENNA` | Temperatura zadana podłogi w dzień | `sensor.floor_day_temp` | °C (20-50) | ✅ **sensor.floor_day_temp** |
| 85 | `0x55` | `PARAM_PODL_NOCNA` | Temperatura zadana podłogi w nocy | `sensor.floor_night_temp` | °C (20-50) | ✅ **sensor.floor_night_temp** |
| 86 | `0x56` | `PARAM_PODL_HISTEREZA` | Histereza temperatury obwodu podłogowego | `number.histereza_podlogowa` | °C (0.2-5.0) | 💡 Niewdrożone (ogrzewanie podłogowe) |
| 87 | `0x57` | `PARAM_PROG_PODLOGOWA` | Harmonogram tygodniowy ogrzewania podłogowego | `schedule.floor_weekly_program` | 42 bajty | ✅ **Obsługiwane w API client.py** |
| 88 | `0x58` | `PARAM_POMPA_CWU_WYJSCIE` | Przypisanie fizycznego wyjścia pompy CWU | `select.przypisanie_wyjscia_cwu` | wyjście | 💡 Niewdrożone (konfiguracja sprzętu) |
| 89 | `0x59` | `PARAM_ALARM_CZASOPOZNIENIA` | Czas opóźnienia potwierdzenia i zgłoszenia alarmu | `number.czas_opoznienia_alarmu` | s (0-300) | 💡 Niewdrożone (alarmy) |
| 90 | `0x5A` | `PARAM_ALARM_INWERSJA` | Inwersja styków wejść alarmowych NO/NC | `switch.inwersja_wejsc_alarmowych` | 0/1 | 💡 Niewdrożone (alarmy) |
| 91 | `0x5B` | `PARAM_ALARM_ZATRZYMANIE` | Zatrzymanie pracy kotła po wystąpieniu alarmu | `switch.zatrzymanie_kotla_alarm` | 0/1 | 💡 Niewdrożone (bezpieczeństwo) |
| 92 | `0x5C` | `PARAM_TYP_KOTLA` | Kod modelu/typu kotła z fabryki | `sensor.typ_kotla` | kod | 💡 Niewdrożone (informacja) |
| 93 | `0x5D` | `PARAM_AKTYWACJA_MIESZAJACA_LATO` | Aktywacja pompy mieszającej / ochrony powrotu w lecie | `switch.mieszacz_aktywny_lato` | 0/1 | 💡 Niewdrożone (ochrona kotła) |
| 94 | `0x5E` | `PARAM_KOREKTA_DMUCHAWY_GRZANIE` | Korekta mocy dmuchawy w trybie automatycznym | `number.blower_correction` | % (-6..+6) | ✅ **number.blower_correction** |
| 95 | `0x5F` | `PARAM_OKRES_REJESTRACJI` | Okres próbkowania i zapisu historii parametrów | `number.interwal_zapisu_historii` | s | 💡 Niewdrożone (archiwum) |
| 96 | `0x60` | `PARAM_MAX_TEMP_SPALIN` | Maksymalna dopuszczalna temperatura spalin kotła | `number.max_temp_spalin` | °C (100-350) | 💡 Niewdrożone (ochrona komina) |
| 97 | `0x61` | `PARAM_MOC_DMUCH_GRZ` | Moc dmuchawy w trybie ręcznym | `number.moc_dmuchawy_grzanie_reczne` | % (1-100) | 💡 Niewdrożone (tryb ręczny) |
| 98 | `0x62` | `PARAM_REGULATOR_SPALIN` | Regulator temperatury spalin (obniża nadmuch) | `switch.exhaust_temp_regulator` | 0/1 | ✅ **switch.exhaust_temp_regulator** |
| 99 | `0x63` | `PARAM_MIN_MOC_DMUCH` | Minimalna moc dmuchawy 2 | `number.min_moc_dmuchawy_2` | % | 💡 Niewdrożone |
| 100 | `0x64` | `PARAM_ALG_MAXMOC` | Maksymalna moc kotła w spalaniu grupowym | `number.spalanie_grupowe_max_moc` | kW (8-30) | 💡 Niewdrożone (spalanie grupowe) |
| 101 | `0x65` | `PARAM_ALG_MOCDMUCH8` | Moc dmuchawy dla progu 8 kW | `number.wiatr_grupa_8kw` | % (1-100) | 💡 Niewdrożone (spalanie grupowe) |
| 102 | `0x66` | `PARAM_ALG_MOCDMUCH12` | Moc dmuchawy dla progu 12 kW | `number.wiatr_grupa_12kw` | % (1-100) | 💡 Niewdrożone (spalanie grupowe) |
| 103 | `0x67` | `PARAM_ALG_MOCDMUCH16` | Moc dmuchawy dla progu 16 kW | `number.wiatr_grupa_16kw` | % (1-100) | 💡 Niewdrożone (spalanie grupowe) |
| 104 | `0x68` | `PARAM_ALG_MOCDMUCH20` | Moc dmuchawy dla progu 20 kW | `number.wiatr_grupa_20kw` | % (1-100) | 💡 Niewdrożone (spalanie grupowe) |
| 105 | `0x69` | `PARAM_ALG_MOCDMUCH25` | Moc dmuchawy dla progu 25 kW | `number.wiatr_grupa_25kw` | % (1-100) | 💡 Niewdrożone (spalanie grupowe) |
| 106 | `0x6A` | `PARAM_ALG_MINMOC` | Minimalna moc kotła w spalaniu grupowym | `number.spalanie_grupowe_min_moc` | kW (8-30) | 💡 Niewdrożone (spalanie grupowe) |
| 107 | `0x6B` | `PARAM_ZASYP_CZASPRZEDMUCHU` | Czas przedmuchu w trybie zasypowym | `number.czas_przedmuchu_zasypowy` | s | 💡 Niewdrożone (zasypowy) |
| 108 | `0x6C` | `PARAM_ZASYP_ODSTEPPRZEDMUCH` | Odstęp między przedmuchami w trybie zasypowym | `number.odstep_przedmuchu_zasypowy` | min | 💡 Niewdrożone (zasypowy) |
| 109 | `0x6D` | `PARAM_ZASYP_MOCDMUCH` | Moc dmuchawy w trybie zasypowym | `number.moc_dmuchawy_zasypowy` | % | 💡 Niewdrożone (zasypowy) |
| 110 | `0x6E` | `PARAM_ZASYP_STREFAAUTO` | Strefa autoregulacji w trybie zasypowym | `number.strefa_autoregulacji_zasypowy` | °C | 💡 Niewdrożone (zasypowy) |
| 111 | `0x6F` | `PARAM_ALG_WYGASZENIA` | Automatyczne wygaszanie kotła przy braku opału | `switch.algorytm_wygaszania` | 0/1 | 💡 Niewdrożone (wygaszanie) |
| 112 | `0x70` | `PARAM_PRIORYTET_CWU` | Priorytet CWU (wyłącza CO przy dogrzewaniu wody) | `switch.dhw_priority` | 0/1 | ✅ **switch.dhw_priority** |
| 113 | `0x71` | `PARAM_TEMP_ZAL_CYRK` | Temperatura kotła zezwalająca na bieg cyrkulacji CWU | `number.temp_zalaczenia_cyrkulacji` | °C (30-60) | 💡 Niewdrożone (cyrkulacja) |
| 114 | `0x72` | `PARAM_PRACA_AUTO_CYRK` | Automatyczna praca pompy cyrkulacyjnej | `switch.automatyczna_cyrkulacja` | 0/1 | 💡 Niewdrożone (cyrkulacja) |
| 115 | `0x73` | `PARAM_TEMP_ZAL_MIESZ` | Temperatura kotła zezwalająca na bieg pompy mieszacza | `number.temp_zalaczenia_mieszacza` | °C (35-70) | 💡 Niewdrożone (ochrona powrotu) |
| 116 | `0x74` | `PARAM_PODLOGOWA_CZASPRACY` | Czas pracy pompy obwodu podłogowego | `number.czas_pracy_podlogowka` | s | 💡 Niewdrożone (podłogówka) |
| 117 | `0x75` | `PARAM_PODLOGOWA_POSTOJ` | Czas postoju pompy obwodu podłogowego | `number.czas_postoju_podlogowka` | min | 💡 Niewdrożone (podłogówka) |
| 118 | `0x76` | `PARAM_CZAS_POSTOJU_GRZANIE` | Czas postoju podajnika 2 w grzaniu ręcznym | `number.czas_postoju_grzanie_2` | s | 💡 Niewdrożone (tryb ręczny) |
| 119 | `0x77` | `PARAM_TYP_PODAJNIKA` | Algorytm spalania (0=ręczny, 1=grupowe, 2=eCoal, 3=zasypowy) | `select.feeder_mode` | 0-3 | ✅ **select.feeder_mode** |
| 120 | `0x78` | `PARAM_HIST_TEMP_CO` | Histereza temperatury kotła CO | `number.histereza_kotla_co` | °C (1-10) | 💡 Niewdrożone (histereza CO) |
| 121 | `0x79` | `PARAM_PODBICIE_TEMP` | O ile stopni podbić zadaną CO podczas grzania bojlera CWU | `number.podbicie_temp_przy_cwu` | °C (0-20) | 💡 Niewdrożone (CWU boost) |
| 122 | `0x7A` | `PARAM_PODAJNIK_CZASWYRZUTU` | Czas pracy podajnika po wykryciu cofnięcia żaru | `number.czas_awaryjnego_wyrzutu_paliwa` | s (10-300) | 💡 Niewdrożone (bezpieczeństwo) |
| 123 | `0x7B` | `PARAM_PRACA_POMPCOPODL` | Czas pracy pompy CO przy pracy podłogówki | `number.praca_pompy_co_przy_podlogowce` | s/min | 💡 Niewdrożone (obieg mieszany) |
| 124 | `0x7C` | `PARAM_POSTOJ_POMPCOPODL` | Czas postoju pompy CO przy pracy podłogówki | `number.postoj_pompy_co_przy_podlogowce` | min | 💡 Niewdrożone (obieg mieszany) |
| 125 | `0x7D` | `PARAM_ALG_MOCDMUCH30` | Moc dmuchawy dla progu 30 kW | `number.wiatr_grupa_30kw` | % (1-100) | 💡 Niewdrożone (spalanie grupowe) |
| 126 | `0x7E` | `PARAM_ALG_ILGRUP8` | Liczba podań paliwa dla progu 8 kW | `number.dawki_grupa_8kw` | ilość (1-15) | 💡 Niewdrożone (spalanie grupowe) |
| 127 | `0x7F` | `PARAM_ALG_ILGRUP12` | Liczba podań paliwa dla progu 12 kW | `number.dawki_grupa_12kw` | ilość (1-15) | 💡 Niewdrożone (spalanie grupowe) |
| 128 | `0x80` | `PARAM_ALG_ILGRUP16` | Liczba podań paliwa dla progu 16 kW | `number.dawki_grupa_16kw` | ilość (1-15) | 💡 Niewdrożone (spalanie grupowe) |
| 129 | `0x81` | `PARAM_ALG_ILGRUP20` | Liczba podań paliwa dla progu 20 kW | `number.dawki_grupa_20kw` | ilość (1-15) | 💡 Niewdrożone (spalanie grupowe) |
| 130 | `0x82` | `PARAM_ALG_ILGRUP25` | Liczba podań paliwa dla progu 25 kW | `number.dawki_grupa_25kw` | ilość (1-15) | 💡 Niewdrożone (spalanie grupowe) |
| 131 | `0x83` | `PARAM_ALG_ILGRUP30` | Liczba podań paliwa dla progu 30 kW | `number.dawki_grupa_30kw` | ilość (1-15) | 💡 Niewdrożone (spalanie grupowe) |
| 132 | `0x84` | `PARAM_CZUJNIK_ZAMZAS` | Kontaktron otwarcia klapy zasobnika paliwa | `binary_sensor.czujnik_zamkniecia_zasobnika` | styk | 💡 Niewdrożone (czujnik klapy) |
| 133 | `0x85` | `PARAM_CZUJNIK_ZERZAW` | Czujnik obrotu ślimaka / zerwania zawleczki | `binary_sensor.czujnik_zerwania_zawleczki` | styk | 💡 Niewdrożone (czujnik zawleczki) |


### Klasyfikacja niewdrożonych encji (propozycje rozszerzeń integracji)

Wszystkie niewdrożone parametry (101 pozycji) posiadają już swoje stałe `PARAM_*` w [`client.py`](../custom_components/ecoal/client.py) oraz metody `read_param()` / `_set_param()`, co pozwala na ich natychmiastowe wystawienie w kolejnych wersjach komponentu:

1. **Konfiguracja Spalania Grupowego (14 parametrów):**
   - Liczba podań i moc dmuchawy dla każdego z 6 progów mocy (8, 12, 16, 20, 25, 30 kW): `number.wiatr_grupa_*kw`, `number.dawki_grupa_*kw`
   - Zakres mocy pracy kotła: `number.spalanie_grupowe_min_moc`, `number.spalanie_grupowe_max_moc`
2. **Histerezy i Algorytmy Regulacji (6 parametrów):**
   - Histereza kotła CO: `number.histereza_kotla_co`
   - Histereza bojlera CWU: `number.cwu_histereza`
   - Podbicie temp. CO przy grzaniu CWU: `number.podbicie_temp_przy_cwu`
   - Algorytm automatycznego wygaszania kotła: `switch.algorytm_wygaszania`
3. **Cyrkulacja CWU i Ochrona Powrotu / Mieszacz (6 parametrów):**
   - Czasy pracy i postoju pompy cyrkulacyjnej: `number.czas_pracy_cyrkulacja`, `number.czas_postoju_cyrkulacja`
   - Praca automatyczna i temp. załączenia cyrkulacji: `switch.automatyczna_cyrkulacja`, `number.temp_zalaczenia_cyrkulacji`
   - Temp. załączenia ochrony powrotu / mieszacza: `number.temp_zalaczenia_mieszacza`
   - Praca pompy mieszającej w lecie: `switch.pompa_mieszajaca_lato`
4. **Obieg Podłogowy (4 parametry):**
   - Czasy pracy i postoju pompy podłogowej: `number.czas_pracy_podlogowka`, `number.czas_postoju_podlogowka`
   - Współpraca pompy CO z obwodem podłogowym: `number.praca_pompy_co_przy_podlogowce`, `number.postoj_pompy_co_przy_podlogowce`
5. **Czujniki fizyczne i Bezpieczeństwo (6 parametrów):**
   - Kontaktron klapy zasobnika: `binary_sensor.czujnik_zamkniecia_zasobnika` (styk)
   - Kontaktron zerwania zawleczki ślimaka: `binary_sensor.czujnik_zerwania_zawleczki` (styk)
   - Maksymalna temp. podajnika (alarm cofnięcia płomienia): `number.max_temp_podajnika_alarm`
   - Czas awaryjnego wyrzutu paliwa ze ślimaka: `number.czas_awaryjnego_wyrzutu_paliwa`
   - Zatrzymanie kotła w przypadku alarmu: `switch.zatrzymanie_kotla_przy_alarmie`
6. **Kalibracja offsetów czujników (8 parametrów):**
   - Korekty temperatur: `number.offset_co`, `number.offset_cwu`, `number.offset_powrot`, `number.offset_podajnik`, `number.offset_spaliny`, `number.offset_zew`, `number.offset_wew`, `number.offset_z1`
7. **Harmonogramy czasowe (6 parametrów):**
   - Programy tygodniowe CO, CWU, pogodowy, pokojowy, obiegowy: `PARAM_PROG_*_TAB`

## Komunikacja alternatywna: ESP32 zamiast Orange Pi (Port RS232 / UART)

Jeśli Twój piec jest obecnie podłączony do komputera jednoukładowego (np. Orange Pi / Raspberry Pi) w kotłowni, możesz zastąpić go małym i energooszczędnym mikrokontrolerem **ESP32** z łącznością Wi-Fi.

### 1. Jak sterownik eCoal komunikuje się wewnętrznie?
* Zapytania HTTP wysyłane na port 80 w formacie `GET /?com=<HEX>` to **w 100% przezroczysty tunel dla ramek szeregowych UART/RS232**.
* Płytka sieciowa sterownika po prostu odbiera ciąg znaków HEX z parametru URL `?com=`, konwertuje go na surowe bajty (`0x02 0x01 0x00 ... 0x03`) i przesyła przez wewnętrzny UART do mikrokontrolera kotła.
* Odpowiedź z procesora pieca jest odczytywana z UART-a i zwracana przez HTTP jako tablica liczb `[2, 1, 6, ...]`.

### 2. Połączenie sprzętowe (Port RS232 na płycie eCoal)
* Płyta sterownika eCoal (wewnątrz obudowy pieca) posiada fizyczne **złącze portu szeregowego RS-232** (używane m.in. przez aplikację serwisową `eCoalUpdater`).
* **Uwaga na napięcia:** Standardowy port RS232 w sterowniku eCoal operuje na napięciach przemysłowych **±12V** (scalak MAX232).
* **Wymagany moduł:** Nie wolno łączyć pinów RS232 bezpośrednio z pinami GPIO ESP32 (3.3V). Wymagany jest tani konwerter poziomów logicznych **MAX3232** (zasilany napięciem 3.3V z ESP32):
  ```
  Sterownik eCoal (RS232 ±12V) <---> Moduł MAX3232 (TTL 3.3V) <---> ESP32 (UART2: GPIO16/17)
  ```
* **Parametry transmisji:** `115200 baud` (w starszych wersjach `57600 baud`), `8 bitów danych`, `brak parzystości (None)`, `1 bit stopu (8N1)`.

### 3. Trzy warianty wdrożenia ESP32

#### Wariant A: ESPHome z własnym komponentem UART (Natywne HA)
* ESP32 działa pod kontrolą **ESPHome**.
* ESPHome cyklicznie wysyła ramkę `CMD_STATUS` (`02010006000000006103`), odbiera 86 bajtów odpowiedzi, weryfikuje CRC i wystawia encje (sensory temperatur, stan pomp, zapas paliwa) bezpośrednio do Home Assistanta przez natywne API ESPHome (bez pośrednictwa protokołu HTTP).

#### Wariant B: ESP32 jako transparentny serwer HTTP / Bridge
* ESP32 łączy się z domowym Wi-Fi i uruchamia prosty mini-serwer HTTP (`WebServer`), który nasłuchuje na ścieżce `GET /?com=<hex>`.
* Po odebraniu zapytania, ESP32 wysyła bajty przez UART do pieca, czeka na odpowiedź i zwraca ją jako JSON `[2, 1, ...]`.
* **Zaleta:** Integracja `ogniwo-furnace-ha` w Home Assistant działa bez żadnych zmian – wystarczy w konfiguracji HA podmienić adres IP z Orange Pi na adres IP ESP32!

#### Wariant C: ESP32 z Ethernetem lub gotowy mostek Wi-Fi-Ethernet (Bez otwierania obudowy)
* Jeśli nie chcesz ingerować w płytę główną pieca i lutować konwertera RS232, a Orange Pi służył Ci tylko jako mostek Wi-Fi dla gniazda Ethernet pieca:
* Możesz użyć płytki **ESP32 z gniazdem Ethernet** (np. *WT32-ETH01* za ~40 zł) lub miniaturowego adaptera Wi-Fi-Ethernet (np. *Vonets VAP11G-300* / *TP-Link TL-WR802N*).
* Wtedy piec jest wpięty normalnym kablem sieciowym RJ45, a komunikacja leci bezprzewodowo przez Wi-Fi.
