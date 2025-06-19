#!/usr/bin/env python3
"""
AWS Backups Deletion Script

Deletes old AMIs and snapshots across AWS landing zones.

Usage:
    python delete_old_backups.py                           # All nonprod zones, 31 days
    python delete_old_backups.py -l zone1 zone2 -d 60     # Specific zones, 60 days
    python delete_old_backups.py -e prod --dry-run         # Dry run for prod
"""

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.logger import setup_logger
from utils.config import get_aws_region, get_provision_role, get_zones_url
from utils.lz import fetch_zones_from_url, filter_zones
from utils.session import SessionManager

logger = setup_logger(__name__, log_file="delete_old_backups.log")


def delete_old_backups(ec2_client, zone_name, days_threshold=31, dry_run=False):
    """Delete old AMIs and snapshots for a specific zone."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    ami_count = 0
    snapshot_count = 0

    # Process AMIs
    try:
        images = ec2_client.describe_images(Owners=["self"]).get("Images", [])
        for image in images:
            if "CreationDate" in image:
                created = datetime.fromisoformat(
                    image["CreationDate"].replace("Z", "+00:00")
                )
                if created < cutoff:
                    image_id = image["ImageId"]
                    if not dry_run:
                        try:
                            ec2_client.deregister_image(ImageId=image_id)
                            logger.info(f"Deregistered AMI: {image_id}")
                        except Exception as e:
                            logger.error(f"Failed to deregister AMI {image_id}: {e}")
                    ami_count += 1
    except Exception as e:
        logger.error(f"Failed to process AMIs in {zone_name}: {e}")

    # Process snapshots
    try:
        snapshots = ec2_client.describe_snapshots(OwnerIds=["self"]).get(
            "Snapshots", []
        )
        for snap in snapshots:
            if snap["StartTime"] < cutoff:
                snap_id = snap["SnapshotId"]
                if not dry_run:
                    try:
                        ec2_client.delete_snapshot(SnapshotId=snap_id)
                        logger.info(f"Deleted snapshot: {snap_id}")
                    except Exception as e:
                        logger.error(f"Failed to delete snapshot {snap_id}: {e}")
                snapshot_count += 1
    except Exception as e:
        logger.error(f"Failed to process snapshots in {zone_name}: {e}")

    action = "Would delete" if dry_run else "Deleted"
    logger.info(
        f"Zone {zone_name}: {action} {ami_count} AMIs, {snapshot_count} snapshots"
    )
    return ami_count, snapshot_count


def main():
    parser = argparse.ArgumentParser(
        description="Delete AMIs and snapshots older than 31 days."
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting",
    )
    args = parser.parse_args()

    landing_zones = args.landing_zones
    environment = args.environment
    days_threshold = args.days
    dry_run = args.dry_run

    if dry_run:
        logger.info("DRY RUN MODE: No resources will be deleted")

    zones_url = get_zones_url()
    region = get_aws_region()
    role = get_provision_role()
    sm = SessionManager()

    total_amis = 0
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

    mode = "DRY RUN" if dry_run else "DELETION"
    logger.info(
        f"{mode}: Processing {len(zones)} zones with {days_threshold} days threshold"
    )

    for line in zones:
        account_id, zone_name = line.split()

        try:
            session = sm.get_session(
                account_id, zone_name, role, region, "delete-backups"
            )
            ec2 = session.client("ec2")

            ami_count, snapshot_count = delete_old_backups(
                ec2, zone_name, days_threshold, dry_run
            )
            total_amis += ami_count
            total_snapshots += snapshot_count
            processed_zones += 1

        except Exception as e:
            logger.error(f"Error processing {zone_name}: {e}")

    # Show summary
    action = "Would delete" if dry_run else "Deleted"
    print(f"\nSummary:")
    print(f"  Zones processed: {processed_zones}")
    print(f"  {action}: {total_amis} AMIs, {total_snapshots} snapshots")
    print(f"  Age threshold: {days_threshold} days")

    logger.info(
        f"Completed: {processed_zones} zones, {action.lower()} {total_amis} AMIs and {total_snapshots} snapshots"
    )


if __name__ == "__main__":
    main()
