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


def delete_old_backups(ec2_client, days_threshold=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)

    # Deregister old AMIs
    images = ec2_client.describe_images(Owners=["self"]).get("Images", [])
    for image in images:
        if "CreationDate" in image:
            created = datetime.fromisoformat(
                image["CreationDate"].replace("Z", "+00:00")
            )
            if created < cutoff:
                image_id = image["ImageId"]
                try:
                    ec2_client.deregister_image(ImageId=image_id)
                    logger.info(f"Deregistered AMI: {image_id}")
                except Exception as e:
                    logger.error(f"Failed to deregister AMI {image_id}: {e}")

    # Delete old snapshots
    snapshots = ec2_client.describe_snapshots(OwnerIds=["self"]).get("Snapshots", [])
    for snap in snapshots:
        if snap["StartTime"] < cutoff:
            snap_id = snap["SnapshotId"]
            try:
                ec2_client.delete_snapshot(SnapshotId=snap_id)
                logger.info(f"Deleted snapshot: {snap_id}")
            except Exception as e:
                logger.error(f"Failed to delete snapshot {snap_id}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Delete AMIs and snapshots older than 30 days."
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
    args = parser.parse_args()

    landing_zones = args.landing_zones
    environment = args.environment

    zones_url = get_zones_url()
    region = get_aws_region()
    role = get_provision_role()
    sm = SessionManager()

    try:
        zones = fetch_zones_from_url(zones_url)
        if landing_zones:
            zones = [
                ln for ln in zones if any(ln.split()[1] == lz for lz in landing_zones)
            ]
        else:
            zones = filter_zones(zones, environment=environment)
    except Exception as e:
        logger.error(f"Failed to fetch landing zones: {e}")
        return

    for line in zones:
        account_id, zone_name = line.split()  # move this line up
        try:
            logger.info(f"Processing zone {zone_name} (account: {account_id})")
            session = sm.get_session(
                account_id, zone_name, role, region, "delete-backups"
            )
            ec2 = session.client("ec2")
            delete_old_backups(ec2)
        except Exception as e:
            logger.error(f"Error processing {zone_name}: {e}")


if __name__ == "__main__":
    main()
