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

## Active Experiment Tracking (Updated: 2026-11-04)
- **Hopper Capacity**: **100 kg** total (`number.garaz_ecoal_pojemnosc_zasobnika`) - optimized for easy 4-bag (4x25kg) refills without spillage/jamming.
- **2026-10-22 17:11 CEST**: 50 kg (2 bags) added to top off the hopper to **100% full**; feeder timer reset to 0.
- **2026-10-23 06:30 CEST**:
  - Found DHW Thermal Stall Trap (CO setpoint 53°C, DHW setpoint 53°C kept pump running continuously and burned 19.88 kg in 13.5 h).
  - Fixed by setting `PARAM 17` (Target DHW) to **50°C** (maintaining Target CO at 53°C, $\Delta T \ge 3^\circ\text{C}$).
  - Boiler immediately entered holding mode (`heating: 0`) with 45-minute feeder pauses (`PARAM 13`).
- **2026-11-04**: Capacity officially calibrated to **100 kg** (4 bags). Holding mode analysis confirmed safe ember preservation for >5h without feed. Added thermal disinfection (Legionella) UI controls & HA entities.
- **2026-11-05**: Fixed overheating in Kawalerka (23.9°C) & eliminated risky manual boiler shutdown cycles. Lowered Target CO (`PARAM 40`) from 56°C to **50°C**, set lowered CO delta (`PARAM 41`) to **5°C** (lowered target 45°C), tuned CO pump cycling to 4m run / 20m pause (`PARAM 70/71`). Added seasonal cold-weather guide in `docs/furnace_memory.md`.
- **2026-11-07**: Fixed rapid boiler cooldown in holding mode. Enabled room regulator (`PARAM 78 = 1`), which activated the 4m run / 20m pause CH pump cycling (`PARAM 69/70/71`) when rooms are warm (indoor temp 22.3°C > target 19.0°C). Stops radiators from dumping boiler heat in holding mode. Added boiler cleaning tracking & safe extinguishing mode.
- **Memory File**: See [`docs/furnace_memory.md`](file:///home/kuku/Projects/ogniwo-furnace-ha/docs/furnace_memory.md) for step-by-step verification instructions, safety architecture (STB / WDT fail-safe), and hardware emulation rules (ESP32 vs Linux SBC for 1-Wire).
- **Technical Research Notes**: See [`docs/furnace_tuning_and_algorithms.md`](file:///home/kuku/Projects/ogniwo-furnace-ha/docs/furnace_tuning_and_algorithms.md).
