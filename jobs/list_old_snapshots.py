#!/usr/bin/env python3
"""
AWS Snapshot Listing Script

Lists old EC2 snapshots across AWS landing zones and generates a CSV report.

Usage:
    python list_old_snapshots.py                           # All nonprod zones, 31 days
    python list_old_snapshots.py -l zone1 zone2 -d 60     # Specific zones, 60 days
    python list_old_snapshots.py -e prod                   # All prod zones
"""

import sys
import os
import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.logger import setup_logger
from utils.config import (
    get_aws_region,
    get_viewer_role,
    get_provision_role,
    get_zones_url,
)
from utils.lz import fetch_zones_from_url, filter_zones, get_account_id
from utils.session import SessionManager

logger = setup_logger(__name__, log_file="list_old_snapshots.log")


def list_old_snapshots(ec2_client, zone_name, days_threshold=31):
    """List old snapshots for a specific zone."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

    try:
        response = ec2_client.describe_snapshots(OwnerIds=["self"])
        snapshots = response.get("Snapshots", [])
        old_snapshots = [snap for snap in snapshots if snap["StartTime"] < cutoff_date]
        logger.info(f"Zone {zone_name}: {len(old_snapshots)} old snapshots found")
        return old_snapshots
    except Exception as e:
        logger.error(f"Failed to list snapshots in {zone_name}: {e}")
        return []


def format_snapshot_info(snapshot, zone_name):
    """Format snapshot info for CSV export."""
    tags = snapshot.get("Tags", [])
    tags_str = (
        "; ".join([f"{tag['Key']}={tag['Value']}" for tag in tags])
        if tags
        else "No tags"
    )

    return {
        "LandingZone": zone_name,
        "SnapshotId": snapshot["SnapshotId"],
        "StartTime": snapshot["StartTime"].strftime("%Y-%m-%d %H:%M:%S UTC"),
        "Tags": tags_str,
    }


def write_csv_report(snapshots_data, csv_file):
    """Write snapshot data to CSV file."""
    if not snapshots_data:
        logger.warning("No snapshots to export")
        return

    Path(csv_file).parent.mkdir(exist_ok=True)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["LandingZone", "SnapshotId", "StartTime", "Tags"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(snapshots_data)

    logger.info(f"CSV report: {csv_file}")


def main():
    parser = argparse.ArgumentParser(
        description="List old EC2 snapshots for specified landing zones."
    )
    parser.add_argument(
        "--landing-zones",
        "-l",
        nargs="*",
        default=[],
        help="Landing zone names (e.g., cmsnonprod appnonprod). Leave blank for all zones in the environment.",
    )
    parser.add_argument(
        "--environment",
        "-e",
        default="nonprod",
        choices=["prod", "nonprod"],
        help="Environment suffix to filter zones if landing-zones not specified.",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=31,
        help="Age threshold in days (default: 31)",
    )

    args = parser.parse_args()

    landing_zones = args.landing_zones
    environment = args.environment
    days_threshold = args.days

    # Generate CSV filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"results/old_snapshots_{timestamp}.csv"

    zones_url = get_zones_url()
    region = get_aws_region()
    role = get_provision_role()  # Using provision role for consistency
    sm = SessionManager()

    all_snapshots_data = []
    total_snapshots = 0
    processed_zones = 0

    # Get zones to process
    zones = fetch_zones_from_url(zones_url)
    if landing_zones:
        zones = [ln for ln in zones if any(ln.split()[1] == lz for lz in landing_zones)]
    else:
        zones = filter_zones(zones, environment=environment)

    if not zones:
        print("No zones found matching criteria")
        return

    logger.info(f"Processing {len(zones)} zones with {days_threshold} days threshold")

    for line in zones:
        account_id, zone_name = line.split()

        try:
            session = sm.get_session(
                account_id, zone_name, role, region, "list-snapshots"
            )
            ec2 = session.client("ec2")
            old_snaps = list_old_snapshots(ec2, zone_name, days_threshold)

            for snap in old_snaps:
                snapshot_info = format_snapshot_info(snap, zone_name)
                all_snapshots_data.append(snapshot_info)

            total_snapshots += len(old_snaps)
            processed_zones += 1

        except Exception as e:
            logger.error(f"Error processing {zone_name}: {e}")

    # Write CSV report and show summary
    write_csv_report(all_snapshots_data, csv_file)

    print(f"\nSummary:")
    print(f"  Zones processed: {processed_zones}")
    print(f"  Old snapshots found: {total_snapshots}")
    print(f"  Age threshold: {days_threshold} days")
    print(f"  CSV report: {csv_file}")

    logger.info(f"Completed: {processed_zones} zones, {total_snapshots} old snapshots")


if __name__ == "__main__":
    main()
