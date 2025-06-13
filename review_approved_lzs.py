#!/usr/bin/env python3
"""
review_approved_lzs.py
----------------------
Given two CSV files
  1. approved_lzs.csv   - a list of Landing Zones that have been cleared for
                          snapshot deletion (first column only)
  2. snapshot_report_*.csv - daily scan showing how many snapshots >30 days
                             each Landing Zone still owns.

The script prints:
  • which *approved* LZs still own ≥1 snapshot older than 30 days
  • which approved LZs are *missing* from the report (optional sanity-check)

Both CSVs may contain:
  - a header line
  - trailing empty columns (",,")
  - blank lines
  - any capitalisation of Landing-Zone names (we compare lower-case)

Usage
-----
$ python review_approved_lzs.py \
        --approved approved_lzs.csv \
        --report   snapshot_report_prod_20250610_0935.csv

Dependencies: only the Python 3 standard library.
"""

import csv
import argparse
import logging
from pathlib import Path
from typing import Dict, Set

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. LOAD THE APPROVED LIST  (approved_lzs.csv)
# ---------------------------------------------------------------------------


def load_approved_lzs(path: Path) -> Set[str]:
    """Return a set of approved landing-zone names (all lower-case)."""

    lzs: Set[str] = set()

    with path.open(newline="") as fh:
        for row in csv.reader(fh):
            if not row or not any(cell.strip() for cell in row):
                continue  # blank line

            first = row[0].strip()
            if not first or first.lower().startswith("landing"):
                continue  # header row

            lzs.add(first.lower())  # normalise case

    log.info("Loaded %d approved landing zones", len(lzs))
    return lzs


# ---------------------------------------------------------------------------
# 2. PARSE THE SNAPSHOT REPORT  (snapshot_report_*.csv)
# ---------------------------------------------------------------------------


def parse_snapshot_report(path: Path) -> Dict[str, int]:
    """Return {landing_zone: snapshot_count (>30 days)}."""

    results: Dict[str, int] = {}

    with path.open(newline="") as fh:
        for row in csv.reader(fh):
            # Skip blank lines and the header that starts with "Environment"
            if (
                not row
                or not any(cell.strip() for cell in row)
                or row[0].strip().lower().startswith("environment")
            ):
                continue

            try:
                lz = row[1].strip().lower()  # column 2 = Landing Zone
                cnt = int(row[2].strip())  # column 3 = Snapshots Count
            except (IndexError, ValueError):
                continue  # malformed line → ignore

            results[lz] = cnt

    log.info("Parsed %d landing zones from snapshot report", len(results))
    return results


# ---------------------------------------------------------------------------
# 3. MAIN ROUTINE
# ---------------------------------------------------------------------------


def main(approved_file: Path, report_file: Path) -> None:
    approved = load_approved_lzs(approved_file)
    snapshot_counts = parse_snapshot_report(report_file)

    offenders = {
        lz: snapshot_counts[lz] for lz in approved if snapshot_counts.get(lz, 0) > 0
    }

    not_approved_offenders = {
        lz: cnt for lz, cnt in snapshot_counts.items() 
        if lz not in approved and cnt > 0
    }

    missing = approved - snapshot_counts.keys()

    if offenders:
        print("Approved LZs that STILL have snapshots > 30 days old:")
        for lz, cnt in sorted(offenders.items(), key=lambda x: (-x[1], x[0])):
            print(f"  • {lz:10}  {cnt:,} snapshots")
    else:
        print("✅  All approved LZs are clean - no snapshots > 30 days remain.")

    if not_approved_offenders:
        print("\n🚨  NOT approved LZs that have snapshots > 30 days old:")
        for lz, cnt in sorted(not_approved_offenders.items(), key=lambda x: (-x[1], x[0])):
            print(f"  • {lz:10}  {cnt:,} snapshots")

    if missing:
        print("\n⚠️  Approved LZs NOT present in the snapshot report:")
        for lz in sorted(missing):
            print(f"  • {lz}")


# ---------------------------------------------------------------------------
# 4. CLI ENTRY-POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check which approved LZs still own >30-day-old snapshots",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--approved",
        required=True,
        type=Path,
        help="Path to approved_lzs.csv",
    )
    parser.add_argument(
        "--report",
        required=True,
        type=Path,
        help="Path to snapshot_report_*.csv",
    )

    args = parser.parse_args()
    main(args.approved, args.report)
