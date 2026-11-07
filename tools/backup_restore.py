#!/usr/bin/env python3
"""eCoal Parameter Backup, Diff & Restore Tool.

Allows backing up all controller registers (0..95) and weekly schedules (42 bytes),
comparing live controller settings against the golden profile, and restoring
the golden configuration after a factory reset.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import aiohttp

# Ensure custom_components is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from custom_components.ecoal.client import (
    EcoalClient,
    _build_value_cmd,
    _build_frame,
)

GOLDEN_CONFIG_PATH = BASE_DIR / "docs" / "golden_config.json"
SCHEDULE_IDS = [24, 25, 26, 27, 28, 83, 87]

PARAMETER_LABELS = {
    13: "Czas postoju podajnika w podtrzymaniu (min)",
    14: "Maksymalna temperatura podajnika (°C)",
    16: "Tryb pracy pompy CWU (0=wył, 1=zima, 2=lato)",
    17: "Zadana temperatura CWU (°C)",
    18: "Histereza CWU (°C x 10)",
    19: "Aktywacja ochrony powrotu / mieszacza (0=wył, 1=mieszacz, 2=podłoga)",
    29: "Obniżenie temperatury CWU (°C)",
    32: "Temperatura pokojowa dzienna (°C x 10)",
    33: "Temperatura pokojowa nocna (°C x 10)",
    40: "Zadana temperatura kotła CO (°C)",
    41: "Obniżenie temperatury CO (°C)",
    50: "Sposób zadawania temperatury CO (0=ręczne, 1=pogodowy)",
    51: "Tryb pracy kotła (0=manual, 1=auto)",
    69: "Praca cykliczna pompy CO (0=ciągła, 1=cykliczna)",
    70: "Czas pracy cyklicznej pompy CO (min)",
    71: "Czas postoju cyklicznego pompy CO (min)",
    78: "Zadawanie temperatury wewnętrznej (0=wył, 1=programator, 2=termostat)",
    79: "Czas pracy ślimaka do opróżnienia zasobnika (min)",
    80: "Histereza regulatora pokojowego (°C x 10)",
    88: "Wyjście pompy CWU",
    92: "Typ kotła",
    94: "Korekta dmuchawy grzanie (%)",
}


async def dump_live_config(client: EcoalClient) -> dict:
    """Read all registers 0..95 and weekly programs from controller."""
    print("Reading all registers (0..95)...")
    params = {}
    for pid in range(96):
        try:
            val = await client.read_param(pid)
            if val is not None:
                params[str(pid)] = val
        except Exception as err:
            print(f"Error reading register {pid}: {err}", file=sys.stderr)

    print("Reading weekly schedules...")
    schedules = {}
    for sid in SCHEDULE_IDS:
        try:
            sched = await client.get_weekly_program(sid)
            if sched is not None:
                schedules[str(sid)] = sched
        except Exception as err:
            print(f"Error reading schedule {sid}: {err}", file=sys.stderr)

    return {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "controller_ip": client.host,
            "description": "Ogniwo Eko Plus / eCoal Golden Configuration",
        },
        "params": params,
        "schedules": schedules,
    }


async def cmd_backup(args):
    """Backup controller settings to file."""
    async with aiohttp.ClientSession() as session:
        client = EcoalClient(args.host, args.username, args.password, session)
        config = await dump_live_config(client)

    out_file = Path(args.output) if args.output else GOLDEN_CONFIG_PATH
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"Golden configuration saved to: {out_file}")


async def cmd_diff(args):
    """Compare live controller settings against golden profile."""
    golden_path = Path(args.golden) if args.golden else GOLDEN_CONFIG_PATH
    if not golden_path.exists():
        print(f"Error: Golden config file not found at {golden_path}", file=sys.stderr)
        return

    with open(golden_path, "r", encoding="utf-8") as f:
        golden = json.load(f)

    async with aiohttp.ClientSession() as session:
        client = EcoalClient(args.host, args.username, args.password, session)
        print("Reading live parameters from controller...")
        differences = []

        for pid_str, golden_val in golden.get("params", {}).items():
            pid = int(pid_str)
            try:
                live_val = await client.read_param(pid)
                if live_val is None:
                    continue
                # Compare primary setting value (first 2 bytes Little Endian)
                golden_setting = golden_val[0] | (golden_val[1] << 8) if len(golden_val) >= 2 else golden_val[0]
                live_setting = live_val[0] | (live_val[1] << 8) if len(live_val) >= 2 else live_val[0]

                if golden_setting != live_setting:
                    desc = PARAMETER_LABELS.get(pid, f"Parametr ID {pid}")
                    differences.append({
                        "id": pid,
                        "desc": desc,
                        "golden": golden_setting,
                        "live": live_setting,
                    })
            except Exception as err:
                print(f"Failed to check param {pid}: {err}", file=sys.stderr)

    if not differences:
        print("\n[OK] Wszystkie parametry sterownika są w 100% zgodne ze złotym profilem!")
    else:
        print(f"\n[UWAGA] Znaleziono {len(differences)} rozbieżności pomiędzy sterownikiem a profilem:")
        print(f"{'ID':>4} | {'Opis parametru':<45} | {'Złoty profil':>12} | {'Sterownik':>12}")
        print("-" * 80)
        for d in differences:
            print(f"{d['id']:>4} | {d['desc']:<45} | {str(d['golden']):>12} | {str(d['live']):>12}")


async def cmd_restore(args):
    """Restore golden profile settings onto the physical controller."""
    golden_path = Path(args.golden) if args.golden else GOLDEN_CONFIG_PATH
    if not golden_path.exists():
        print(f"Error: Golden config file not found at {golden_path}", file=sys.stderr)
        return

    with open(golden_path, "r", encoding="utf-8") as f:
        golden = json.load(f)

    if not args.yes:
        confirm = input(f"Czy na pewno chcesz przywrócić parametry na sterownik {args.host}? [t/N]: ")
        if confirm.lower() not in ("t", "tak", "y", "yes"):
            print("Anulowano.")
            return

    async with aiohttp.ClientSession() as session:
        client = EcoalClient(args.host, args.username, args.password, session)

        print("\nPrzywracanie parametrów głównych...")
        restored = 0
        errors = 0

        # Key tuned parameters to restore with priority
        tuned_pids = [13, 14, 16, 17, 18, 19, 29, 32, 33, 40, 41, 50, 51, 69, 70, 71, 78, 79, 80, 88, 92, 94]
        # Then all other parameters from backup
        all_pids = sorted(list(set(tuned_pids + [int(k) for k in golden.get("params", {}).keys()])))

        for pid in all_pids:
            if pid >= 96:
                continue  # Firmware 0.2.9.16 strictly supports 0..95
            golden_val = golden["params"].get(str(pid))
            if not golden_val:
                continue
            val_int = golden_val[0] | (golden_val[1] << 8) if len(golden_val) >= 2 else golden_val[0]
            try:
                cmd = _build_value_cmd(pid, val_int)
                res = await client.send_raw_command(cmd)
                if res and (res.startswith("[2,1,6") or res.startswith("[2, 1, 6")):
                    desc = PARAMETER_LABELS.get(pid, f"ID {pid}")
                    print(f"  [OK] Param {pid:2d} -> {val_int:5d} ({desc})")
                    restored += 1
                else:
                    errors += 1
            except Exception as e:
                print(f"  [BŁĄD] Param {pid}: {e}")
                errors += 1
            await asyncio.sleep(0.08)

        print(f"\nPrzywracanie harmonogramów tygodniowych...")
        for sid_str, sched in golden.get("schedules", {}).items():
            sid = int(sid_str)
            try:
                ok = await client.set_weekly_program(sid, sched)
                print(f"  [{'OK' if ok else 'BŁĄD'}] Harmonogram ID {sid}")
            except Exception as e:
                print(f"  [BŁĄD] Harmonogram {sid}: {e}")

        print(f"\nZakończono przywracanie: {restored} parametrów zapisanych pomyślnie, {errors} błędów.")


def main():
    parser = argparse.ArgumentParser(description="eCoal Backup & Restore Tool")
    parser.add_argument("--host", default="192.168.2.111", help="Controller IP (default: 192.168.2.111)")
    parser.add_argument("--username", default="admin", help="HTTP username (default: admin)")
    parser.add_argument("--password", default="admin", help="HTTP password (default: admin)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # backup
    p_backup = subparsers.add_parser("backup", help="Dump controller settings to golden config")
    p_backup.add_argument("-o", "--output", help="Output JSON path")

    # diff
    p_diff = subparsers.add_parser("diff", help="Compare controller against golden config")
    p_diff.add_argument("-g", "--golden", help="Golden config path")

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore golden config onto controller")
    p_restore.add_argument("-g", "--golden", help="Golden config path")
    p_restore.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if args.command == "backup":
        asyncio.run(cmd_backup(args))
    elif args.command == "diff":
        asyncio.run(cmd_diff(args))
    elif args.command == "restore":
        asyncio.run(cmd_restore(args))


if __name__ == "__main__":
    main()
