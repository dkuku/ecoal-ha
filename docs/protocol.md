# eCoal Furnace Protocol Documentation

## Hardware
- **Furnace brand**: Ogniwo (Ogniwo Biecz)
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
| Manual stop time         | 0x76  | 2 bytes LE (s) |
| Manual air pump power    | 0x61  | 1 byte (%)     |

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
