#!/usr/bin/env python3
"""
Scan AWS resources by tag conditions and exclusions across landing zones.

This script identifies AWS resources that match specific tag conditions,
while excluding those containing unwanted tag values. For EC2 instances,
it only includes resources explicitly marked as managed by CMS.
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import boto3
from botocore.exceptions import ClientError
from utils.logger import setup_logger
from utils.config import get_aws_region, get_provision_role, get_zones_url
from utils.lz import fetch_zones_from_url, filter_zones
from utils.session import SessionManager

logger = setup_logger(__name__, log_file="scan_tagged_resources.log")

# Constants
SESSION_NAME = "scan-tags"
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

# Tags/keywords that should NOT be present depending on resource type
EXCLUSIONS = {
    "ec2:instance": ["asg"],
    "ec2:volume": ["asg", "nabserv"],
    "autoscaling:autoScalingGroup": ["nabserv"],
    "s3": ["nabserv"],
    "elasticloadbalancing:loadbalancer": ["nef2"],
    "elasticloadbalancing:targetgroup": ["nef2"],
    "efs:file-system": ["nef2"],
    "fsx:volume": ["nef"],
    "ec2:security-group": ["cps", "nabserv", "nef2"],
    "kms:key": ["nabserv", "wiz", "nef2"],
}

# Tag conditions (included if present)
TAG_CONDITIONS = [
    {"Key": "aws:autoscaling:groupName"},
    {"Key": "HIPLocked", "Values": ["Yes"]},
    {"Key": "Name", "Values": ["nef-jenkins"]},
    {"Key": "wiz"},
    {"Key": "HIPmgmtEKS", "Values": ["Yes"]},
]

RESOURCE_TYPES = list(EXCLUSIONS.keys()) + ["rds:db", "eks:cluster"]


def is_excluded(resource_type: str, tags: List[Dict[str, str]]) -> bool:
    tag_map = {tag["Key"]: tag.get("Value", "") for tag in tags}
    exclusion_keywords = EXCLUSIONS.get(resource_type, [])
    for keyword in exclusion_keywords:
        for value in tag_map.values():
            if keyword and value and keyword.lower() in value.lower():
                return True
    return False


def is_cms_managed(tags: List[Dict[str, str]]) -> bool:
    tag_map = {tag["Key"].lower(): tag.get("Value", "").lower() for tag in tags}
    return tag_map.get("managed_by") == "cms"


def scan_resources(session) -> List[Tuple[str, Dict[str, str]]]:
    client = session.client("resourcegroupstaggingapi")
    paginator = client.get_paginator("get_resources")
    matched = []

    for page in paginator.paginate(
        ResourceTypeFilters=RESOURCE_TYPES, TagFilters=TAG_CONDITIONS
    ):
        for res in page.get("ResourceTagMappingList", []):
            arn = res["ResourceARN"]
            tags = res.get("Tags", [])
            rtype = res.get("ResourceType") or ""

            tag_dict = {t["Key"]: t.get("Value", "") for t in tags}
            if not is_excluded(rtype, tags):
                if rtype == "ec2:instance" and not is_cms_managed(tags):
                    logger.debug(f"⏭️ Skipped non-CMS EC2: {arn}")
                    continue
                matched.append((arn, tag_dict))
                logger.info(f"[MATCH] {arn} -> {tag_dict}")

    return matched


def write_results_to_csv(
    lz_name: str, matched_resources: List[Tuple[str, Dict[str, str]]]
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"{lz_name}_matched_resources_{timestamp}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ResourceARN", "Tags"])
        for arn, tags in matched_resources:
            tag_str = "; ".join(f"{k}={v}" for k, v in tags.items())
            writer.writerow([arn, tag_str])
    logger.info(f"✅ Results written to: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Scan AWS resources by tag conditions and exclusions."
    )
    parser.add_argument(
        "--landing-zones",
        "-l",
        nargs="*",
        default=[],
        help="Landing zone names (e.g., cmsnonprod appanonprod)",
    )
    parser.add_argument(
        "--environment",
        "-e",
        default="nonprod",
        choices=["prod", "nonprod", "preprod"],
        help="Environment suffix to filter zones if landing-zones not specified.",
    )
    args = parser.parse_args()

    landing_zones = args.landing_zones
    environment = args.environment
    region = get_aws_region()
    role = get_provision_role()
    zones_url = get_zones_url()
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
        logger.error(f"❌ Failed to fetch landing zones: {e}")
        return

    logger.info(f"🔍 Matched {len(zones)} zones for scanning")

    for line in zones:
        account_id, zone_name = line.split()
        try:
            logger.info(f"🚀 Scanning LZ: {zone_name} (account: {account_id})")
            session = sm.get_session(account_id, zone_name, role, region, SESSION_NAME)
            matched = scan_resources(session)
            write_results_to_csv(zone_name, matched)
        except Exception as e:
            logger.error(f"❌ Error scanning {zone_name}: {e}")


if __name__ == "__main__":
    main()
