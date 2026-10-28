# Ogniwo Furnace Home Assistant Integration - Project Rules & Memory

## System Architecture & Connectivity
- **Furnace Model**: Ogniwo Eko Plus with retort underfeed stoker burner (podawanie od dołu).
- **Controller**: eCoal v0.2.9.16.
- **Controller Network**: IP `192.168.2.111`, HTTP port 80, Basic Auth (`admin` / `admin`).
- **Home Assistant**: Host `root@192.168.1.245`.
- **Database**: PostgreSQL on `192.168.30.104:5432`, database `homeassistant`.

## Protocol & Firmware Rules
- **Firmware Parameter Range**: Controller firmware `0.2.9.16` strictly supports parameter IDs in range `0 .. 95`. Any parameter ID $\ge 96$ (including group combustion parameters 120, 126–131) will return NAK `0x15` and must not be used.
- **Status Frame**: Command `02010006000000006103` via `GET http://192.168.2.111/?com=<hex>`.
- **Set Parameter**: CMD `0x02`, payload 2-byte LE.

## Feeder & Consumption Calibration (Updated 2026-10-23)
- **Feeder Throughput**: Exactly **0.3666 kg/min** (**22.0 kg/h**), calibrated from 136.4 minutes of auger runtime = 50.0 kg of coal (2 bags).
- **Formula**: `coal_consumed_kg = feeder_runtime_min * 0.3666`.

## Active Experiment Tracking (Baseline: 2026-10-23)
- **Hopper Capacity**: **150 kg** total (`number.garaz_ecoal_pojemnosc_zasobnika`).
- **2026-10-22 17:11 CEST**: 50 kg (2 bags) added to top off the hopper to **100% full (150 kg)**; feeder timer reset to 0. (The 136.4 min previous runtime corresponded to burning exactly the 50 kg needed to top it off).
- **2026-10-23 06:30 CEST**:
  - Found DHW Thermal Stall Trap (CO setpoint 53°C, DHW setpoint 53°C kept pump running continuously and burned 19.88 kg in 13.5 h).
  - Fixed by setting `PARAM 17` (Target DHW) to **50°C** (maintaining Target CO at 53°C, $\Delta T \ge 3^\circ\text{C}$).
  - Boiler immediately entered holding mode (`heating: 0`) with 45-minute feeder pauses (`PARAM 13`).
  - Remaining fuel in hopper: **~130 kg** (approx. 87-90%).
- **Memory File**: See [`docs/furnace_memory.md`](file:///home/kuku/Projects/ogniwo-furnace-ha/docs/furnace_memory.md) for step-by-step verification instructions, safety architecture (STB / WDT fail-safe), and hardware emulation rules (ESP32 vs Linux SBC for 1-Wire).
- **Technical Research Notes**: See [`docs/furnace_tuning_and_algorithms.md`](file:///home/kuku/Projects/ogniwo-furnace-ha/docs/furnace_tuning_and_algorithms.md).
