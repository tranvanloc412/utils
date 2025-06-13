#!/usr/bin/env python3
"""
review_approved_lzs.py
—————————
Given:
  • approved_lzs.txt  -> one Landing Zone per line (no header, comments allowed)
  • snapshot_report_<date>.csv -> columns: Environment,Landing Zone,Snapshots Count …

Print the approved LZs that still have snapshots > 30 days old.
"""

import csv
import argparse
from pathlib import Path
import logging
from typing import Dict, Set

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def load_approved_lzs(path: Path) -> Set[str]:
    """Return a set of LZ names, ignoring blank lines and '#' comments."""
    with path.open() as fh:
        lzs = {
            line.strip()
            for line in fh
            if (line := line.strip()) and not line.startswith("#")
        }
    log.info("Loaded %d approved landing zones", len(lzs))
    return lzs


def parse_snapshot_report(path: Path) -> Dict[str, int]:
    """Return {landing_zone: snapshot_count (>30 d)}."""
    with path.open(newline="") as fh:
        reader = csv.DictReader((row for row in fh if not row.lstrip().startswith("#")))
        results = {
            r["Landing Zone"].strip(): int(r["Snapshots Count"])
            for r in reader
            if r["Landing Zone"].strip()
        }
    log.info("Parsed %d landing zones from snapshot report", len(results))
    return results


def main(approved_file: Path, report_file: Path) -> None:
    approved = load_approved_lzs(approved_file)
    snapshot_counts = parse_snapshot_report(report_file)

    offenders = {
        lz: snapshot_counts[lz] for lz in approved if snapshot_counts.get(lz, 0) > 0
    }

    if offenders:
        print("\nApproved LZs that STILL have snapshots > 30 days old:")
        for lz, cnt in sorted(offenders.items(), key=lambda x: (-x[1], x[0])):
            print(f"  • {lz:10}  {cnt:,}  snapshots")
    else:
        print("✅  All approved LZs are clean – no snapshots > 30 days remain.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check which approved LZs still own >30-day-old snapshots"
    )
    parser.add_argument(
        "--approved",
        required=True,
        type=Path,
        help="Path to approved_lzs.txt",
    )
    parser.add_argument(
        "--report",
        required=True,
        type=Path,
        help="Path to snapshot_report_*.csv",
    )
    args = parser.parse_args()
    main(args.approved, args.report)
