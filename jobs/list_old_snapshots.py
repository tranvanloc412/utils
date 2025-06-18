import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.logger import setup_logger
from utils.config import get_aws_region, get_provision_role, get_zones_url
from utils.lz import fetch_zones_from_url, filter_zones, get_account_id
from utils.session import SessionManager

logger = setup_logger(__name__, log_file="list_old_snapshots.log")


def list_old_snapshots(ec2_client, days_threshold=30):
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    response = ec2_client.describe_snapshots(
        OwnerIds=["self"]
    )  # Adjust OwnerIds if needed
    snapshots = response.get("Snapshots", [])
    old_snapshots = [snap for snap in snapshots if snap["StartTime"] < cutoff_date]
    return old_snapshots


def main():
    parser = argparse.ArgumentParser(
        description="List old EC2 snapshots for specified landing zones."
    )
    parser.add_argument(
        "--landing-zones",
        nargs="*",
        default=[],
        help="Landing zone names (e.g., cmsnonprod appnonprod). Leave blank for all zones in the environment.",
    )
    parser.add_argument(
        "--environment",
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
        logger.error(f"Error loading landing zones: {e}")
        return

    if not zones:
        logger.warning("No landing zones matched the filter.")
        return

    for line in zones:
        try:
            account_id, zone_name = line.split()
            logger.info(f"Processing zone: {zone_name} (account: {account_id})")
            session = sm.get_session(
                account_id, zone_name, role, region, "list-snapshots"
            )
            ec2 = session.client("ec2")
            old_snaps = list_old_snapshots(ec2)
            for snap in old_snaps:
                logger.info(
                    f"Snapshot {snap['SnapshotId']} from {snap['StartTime']} in {zone_name}"
                )
        except Exception as e:
            logger.error(f"Error processing zone {line}: {e}")


if __name__ == "__main__":
    main()
