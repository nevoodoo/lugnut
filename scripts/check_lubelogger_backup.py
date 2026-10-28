"""Dry run of a LubeLogger import: read a backup zip, build the plan, print counts and warnings.

Writes nothing and prints no record values.

Usage: python scripts/check_lubelogger_backup.py backup.zip [--tz ZONE] [--date-order DMY|MDY|YMD]
"""

import argparse
import json
import zipfile
from collections import Counter

from lugnut.lubelogger.litedb import read_collections
from lugnut.lubelogger.mapper import build_plan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--tz", dest="source_timezone")
    ap.add_argument("--date-order", choices=("DMY", "MDY", "YMD"))
    args = ap.parse_args()
    with zipfile.ZipFile(args.zip) as zf:
        names = set(zf.namelist())
        cols = read_collections(zf.read("data/cartracker.db"))
        config = (
            json.loads(zf.read("config/userConfig.json"))
            if "config/userConfig.json" in names
            else {}
        )
    options = {k: v for k, v in vars(args).items() if k != "zip" and v}
    plan = build_plan(cols, config, options)
    print("collections:", {k: len(v) for k, v in sorted(cols.items()) if v})
    print("guesses:", plan.guesses, "volume unit:", plan.volume_unit)
    for i, pv in enumerate(plan.vehicles, 1):
        counts = Counter(r["type"] for r in pv.records)
        repeating = sum(1 for r in pv.reminders if r["repeat_months"] or r["repeat_km"])
        print(f"vehicle {i}: records {dict(counts)}, reminders {len(pv.reminders)}", end="")
        print(f" ({repeating} repeating), photo {'yes' if pv.photo_zip_path else 'no'}")
    refs = {f["zip_path"] for pv in plan.vehicles for r in pv.records for f in r["files"]}
    refs |= {pv.photo_zip_path for pv in plan.vehicles if pv.photo_zip_path}
    print(f"files: {len(refs)} referenced, {len(refs - names)} missing from the zip")
    print("tax records needing a type check:", sum(1 for w in plan.warnings if "check type" in w))
    print("estimates:", len(plan.estimates), "skipped:", plan.skipped)
    print("warnings:", *plan.warnings or ["none"], sep="\n  ")


if __name__ == "__main__":
    main()
