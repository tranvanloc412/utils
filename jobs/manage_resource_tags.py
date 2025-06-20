#!/usr/bin/env python3
"""
Scan AWS resources by tag conditions and exclusions across landing zones.

This script identifies AWS resources that match specific tag conditions,
while excluding those containing unwanted tag values. For EC2 instances,
it only includes resources explicitly marked as managed by CMS.
"""

import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import boto3
from botocore.exceptions import ClientError
from utils.logger import setup_logger
from utils.config import (
    get_aws_region,
    get_provision_role,
    get_zones_url,
    get_test_account_id,
    get_test_account_name,
)
from utils.lz import fetch_zones_from_url, filter_zones
from utils.session import SessionManager

logger = setup_logger(__name__, log_file="scan_tagged_resources.log")

SESSION_NAME = "scan-tags"
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

SERVICES = {
    "ec2": "ec2:instance",
    "ebs": "ec2:volume",
    "asg": "autoscaling:autoScalingGroup",
    "s3": "s3",
    "sns": "sns",
    "sqs": "sqs",
    "dynamodb": "dynamodb:table",
    "cloudwatch": "cloudwatch:alarm",
    "events": "events:rule",
    "iam": "iam:role",
    "route53": "route53:hostedzone",
    "lb": "elasticloadbalancing:loadbalancer",
    "tg": "elasticloadbalancing:targetgroup",
    "efs": "elasticfilesystem:file-system",
    "fsx": "fsx:volume",
    "sg": "ec2:security-group",
    "kms": "kms:key",
    "rds": "rds:db",
}

# Services that require direct API calls (not supported by Resource Groups Tagging API)
DIRECT_API_SERVICES = ["iam", "route53"]

TAG_PRESETS = {
    "asg": [{"Key": "aws:autoscaling:groupName"}],
    "nabserv": [{"Key": "Name", "Values": ["nef-jenkins"], "MatchType": "contains"}],
    "nef2": [{"Key": "HIPmgmtEKS", "Values": ["Yes"]}],
    "cps": [{"Key": "HIPLocked", "Values": ["Yes"]}],
    "wiz": [{"Key": "wiz"}],
    "managed_by_cms": [{"Key": "managed_by", "Values": ["CMS"]}],
}


# Standard exclude rule for all services
STANDARD_EXCLUDE = TAG_PRESETS["nef2"] + TAG_PRESETS["nabserv"] + TAG_PRESETS["cps"] + TAG_PRESETS["wiz"]

SERVICE_TAG_RULES = {
    "ec2": {
        "include": TAG_PRESETS["managed_by_cms"],
        "exclude": STANDARD_EXCLUDE,
    },
    "ebs": {
        "exclude": STANDARD_EXCLUDE,
    },
    "asg": {"exclude": STANDARD_EXCLUDE},
    "s3": {"exclude": STANDARD_EXCLUDE},
    "lb": {"exclude": STANDARD_EXCLUDE},
    "tg": {"exclude": STANDARD_EXCLUDE},
    "efs": {"exclude": STANDARD_EXCLUDE},
    "fsx": {"exclude": STANDARD_EXCLUDE},
    "sg": {
        "exclude": STANDARD_EXCLUDE,
    },
    "kms": {
        "exclude": STANDARD_EXCLUDE,
    },
    "rds": {"exclude": STANDARD_EXCLUDE},
    "sns": {"exclude": STANDARD_EXCLUDE},
    "sqs": {"exclude": STANDARD_EXCLUDE},
    "dynamodb": {"exclude": STANDARD_EXCLUDE},
    "cloudwatch": {"exclude": STANDARD_EXCLUDE},
    "events": {"exclude": STANDARD_EXCLUDE},
    "iam": {"exclude": STANDARD_EXCLUDE},
    "route53": {"exclude": STANDARD_EXCLUDE},
    "lambda": {"exclude": STANDARD_EXCLUDE},
}

# Filter out services that require direct API calls
RESOURCE_TYPES = [v for k, v in SERVICES.items() if k not in DIRECT_API_SERVICES]


def matches_includes(tags, include_rules):
    tag_map = {t["Key"].lower(): t.get("Value", "").lower() for t in tags}
    for cond in include_rules:
        key = cond["Key"].lower()
        if "Values" in cond:
            tag_value = tag_map.get(key, "")
            match_type = cond.get("MatchType", "exact").lower()

            if match_type == "contains":
                # Substring matching - check if any rule value is contained in the tag value
                if not any(v.lower() in tag_value for v in cond["Values"]):
                    return False
            else:
                # Default exact matching
                if tag_value not in [v.lower() for v in cond["Values"]]:
                    return False
        elif key not in tag_map:
            return False
    return True


def matches_excludes(tags, exclude_rules):
    tag_map = {t["Key"].lower(): t.get("Value", "").lower() for t in tags}
    for cond in exclude_rules:
        key = cond["Key"].lower()
        val = tag_map.get(key)
        if val:
            if "Values" in cond:
                match_type = cond.get("MatchType", "contains").lower()  # Default to contains for excludes
                
                if match_type == "exact":
                    # Exact matching for excludes
                    if val in [v.lower() for v in cond["Values"]]:
                        return True
                else:
                    # Default substring matching for excludes (maintains backward compatibility)
                    for bad_val in cond["Values"]:
                        if bad_val.lower() in val:
                            return True
            else:
                return True
    return False


def scan_iam_roles(session) -> List[Tuple[str, Dict[str, str]]]:
    """Scan IAM roles using direct IAM API calls"""
    client = session.client("iam")
    paginator = client.get_paginator("list_roles")
    matched = []
    
    logger.debug("🔍 Scanning IAM roles...")
    
    for page in paginator.paginate():
        for role in page.get("Roles", []):
            role_name = role["RoleName"]
            arn = role["Arn"]
            
            try:
                # Get role tags
                response = client.list_role_tags(RoleName=role_name)
                tags = response.get("Tags", [])
                
                # Convert to standard tag format
                formatted_tags = [{"Key": tag["Key"], "Value": tag["Value"]} for tag in tags]
                
                logger.debug(f"🔍 Processing IAM role: {arn}, tags: {len(formatted_tags)}")
                
                # Apply filtering rules
                rules = SERVICE_TAG_RULES.get("iam", {})
                include_rules = rules.get("include", [])
                exclude_rules = rules.get("exclude", [])
                
                if matches_excludes(formatted_tags, exclude_rules):
                    logger.debug(f"⏭️ Excluded by tag rule: {arn}")
                    continue
                if include_rules and not matches_includes(formatted_tags, include_rules):
                    logger.debug(f"⏭️ Not included by tag rule: {arn}")
                    continue
                
                matched.append((arn, {"tags": formatted_tags, "service": "iam"}))
                logger.debug(f"✅ Matched IAM role: {arn}")
                
            except Exception as e:
                logger.debug(f"⚠️ Error processing IAM role {role_name}: {e}")
                continue
    
    logger.debug(f"📊 IAM roles scan complete: {len(matched)} matched")
    return matched


def scan_route53_zones(session) -> List[Tuple[str, Dict[str, str]]]:
    """Scan Route53 hosted zones using direct Route53 API calls"""
    client = session.client("route53")
    paginator = client.get_paginator("list_hosted_zones")
    matched = []
    
    logger.debug("🔍 Scanning Route53 hosted zones...")
    
    for page in paginator.paginate():
        for zone in page.get("HostedZones", []):
            zone_id = zone["Id"].replace("/hostedzone/", "")
            zone_name = zone["Name"]
            arn = f"arn:aws:route53:::hostedzone/{zone_id}"
            
            try:
                # Get zone tags
                response = client.list_tags_for_resource(
                    ResourceType="hostedzone",
                    ResourceId=zone_id
                )
                tags = response.get("ResourceTagSet", {}).get("Tags", [])
                
                # Convert to standard tag format
                formatted_tags = [{"Key": tag["Key"], "Value": tag["Value"]} for tag in tags]
                
                logger.debug(f"🔍 Processing Route53 zone: {arn} ({zone_name}), tags: {len(formatted_tags)}")
                
                # Apply filtering rules
                rules = SERVICE_TAG_RULES.get("route53", {})
                include_rules = rules.get("include", [])
                exclude_rules = rules.get("exclude", [])
                
                if matches_excludes(formatted_tags, exclude_rules):
                    logger.debug(f"⏭️ Excluded by tag rule: {arn}")
                    continue
                if include_rules and not matches_includes(formatted_tags, include_rules):
                    logger.debug(f"⏭️ Not included by tag rule: {arn}")
                    continue
                
                matched.append((arn, {"tags": formatted_tags, "service": "route53", "name": zone_name}))
                logger.debug(f"✅ Matched Route53 zone: {arn}")
                
            except Exception as e:
                logger.debug(f"⚠️ Error processing Route53 zone {zone_id}: {e}")
                continue
    
    logger.debug(f"📊 Route53 zones scan complete: {len(matched)} matched")
    return matched


def scan_resources(session) -> List[Tuple[str, Dict[str, str]]]:
    matched = []
    
    # Scan services supported by Resource Groups Tagging API
    if RESOURCE_TYPES:
        logger.info(f"🔍 Starting Resource Groups Tagging API scan with resource types: {RESOURCE_TYPES}")
        matched.extend(scan_resources_with_tagging_api(session))
    
    # Scan services requiring direct API calls
    for service in DIRECT_API_SERVICES:
        if service == "iam":
            logger.info("🔍 Starting IAM roles scan...")
            matched.extend(scan_iam_roles(session))
        elif service == "route53":
            logger.info("🔍 Starting Route53 hosted zones scan...")
            matched.extend(scan_route53_zones(session))
    
    logger.info(f"📊 Total scan complete: {len(matched)} resources matched across all services")
    return matched


def scan_resources_with_tagging_api(session) -> List[Tuple[str, Dict[str, str]]]:
    """Scan resources using the Resource Groups Tagging API"""
    client = session.client("resourcegroupstaggingapi")
    paginator = client.get_paginator("get_resources")
    matched = []
    total_resources = 0
    processed_resources = 0

    for page in paginator.paginate(ResourceTypeFilters=RESOURCE_TYPES):
        resources_in_page = page.get("ResourceTagMappingList", [])
        total_resources += len(resources_in_page)
        logger.debug(f"📄 Processing page with {len(resources_in_page)} resources")
        for res in resources_in_page:
            arn = res["ResourceARN"]
            tags = res.get("Tags", [])
            rtype = res.get("ResourceType") or ""
            processed_resources += 1

            # If ResourceType is empty, try to extract from ARN
            if not rtype:
                # Extract service and resource type from ARN format
                arn_parts = arn.split(":")
                if len(arn_parts) >= 3:
                    service = arn_parts[2]

                    # Handle different ARN formats
                    if service in ["s3", "sns", "sqs"]:
                        # Services with simplified ARN formats
                        # S3: arn:aws:s3:::bucket-name
                        # SNS: arn:aws:sns:region:account:topic-name
                        # SQS: arn:aws:sqs:region:account:queue-name
                        rtype = service
                    elif len(arn_parts) >= 6:
                        # Standard ARN format: arn:aws:service:region:account:resource-type/resource-id
                        resource_part = arn_parts[5]
                        if "/" in resource_part:
                            resource_type = resource_part.split("/")[0]
                            rtype = f"{service}:{resource_type}"
                        else:
                            rtype = f"{service}:{resource_part}"
                    else:
                        # Fallback for other services with shorter ARN formats
                        rtype = service

            logger.debug(f"🔍 Processing resource: {arn}, type: {rtype}")

            service_key = next((k for k, v in SERVICES.items() if v == rtype), None)
            if not service_key:
                logger.debug(f"⚠️ Unknown resource type: {rtype} for ARN: {arn}")
                continue

            rules = SERVICE_TAG_RULES.get(service_key, {})
            include_rules = rules.get("include", [])
            exclude_rules = rules.get("exclude", [])

            if matches_excludes(tags, exclude_rules):
                logger.debug(f"⏭️ Excluded by tag rule: {arn}")
                continue
            if include_rules and not matches_includes(tags, include_rules):
                logger.debug(f"⏭️ Missing required tags: {arn}")
                continue

            tag_dict = {t["Key"]: t.get("Value", "") for t in tags}
            matched.append((arn, tag_dict))
            logger.info(f"[MATCH] {arn} -> {tag_dict}")

    logger.info(
        f"📊 Scan summary - Total resources: {total_resources}, Processed: {processed_resources}, Matched: {len(matched)}"
    )
    return matched


def tag_resources_with_nis_managed(
    session, matched_resources: List[Tuple[str, Dict[str, str]]]
) -> Dict[str, int]:
    """
    Add 'nis_managed = true' tag to matched resources.

    Args:
        session: AWS session
        matched_resources: List of (ARN, tags) tuples

    Returns:
        Dictionary with success/failure counts
    """
    client = session.client("resourcegroupstaggingapi")
    stats = {"success": 0, "failed": 0, "errors": []}

    logger.info(
        f"🏷️ Starting to tag {len(matched_resources)} resources with nis_managed=true"
    )

    for arn, existing_tags in matched_resources:
        try:
            # Check if nis_managed tag already exists
            if "nis_managed" in existing_tags:
                logger.debug(f"⏭️ Resource already has nis_managed tag: {arn}")
                stats["success"] += 1
                continue

            # Add the nis_managed tag
            response = client.tag_resources(
                ResourceARNList=[arn], Tags={"nis_managed": "true"}
            )

            # Check for failures in the response
            if response.get("FailedResourcesMap"):
                error_info = response["FailedResourcesMap"][arn]
                error_msg = f"{error_info.get('ErrorCode', 'Unknown')}: {error_info.get('ErrorMessage', 'Unknown error')}"
                logger.warning(f"⚠️ Failed to tag resource {arn}: {error_msg}")
                stats["failed"] += 1
                stats["errors"].append(f"{arn}: {error_msg}")
            else:
                logger.debug(f"✅ Successfully tagged resource: {arn}")
                stats["success"] += 1

        except ClientError as e:
            error_msg = (
                f"{e.response['Error']['Code']}: {e.response['Error']['Message']}"
            )
            logger.warning(f"⚠️ Failed to tag resource {arn}: {error_msg}")
            stats["failed"] += 1
            stats["errors"].append(f"{arn}: {error_msg}")
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error tagging resource {arn}: {str(e)}")
            stats["failed"] += 1
            stats["errors"].append(f"{arn}: {str(e)}")

    logger.info(
        f"🏷️ Tagging completed - Success: {stats['success']}, Failed: {stats['failed']}"
    )
    return stats


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
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="Use test account configuration from settings.yaml instead of fetching zones",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging to see detailed resource processing",
    )
    parser.add_argument(
        "--tag-nis-managed",
        action="store_true",
        help="Add 'nis_managed=true' tag to all matched resources",
    )
    args = parser.parse_args()

    # Update logger level if debug is requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    landing_zones = args.landing_zones
    environment = args.environment
    use_test = args.test
    region = get_aws_region()
    role = get_provision_role()
    zones_url = get_zones_url()
    sm = SessionManager()

    if use_test:
        # Use test account configuration from settings.yaml
        account_id = get_test_account_id()
        zone_name = get_test_account_name()

        if not account_id or not zone_name:
            logger.error("❌ Test account configuration not found in settings.yaml")
            return

        logger.info(f"🧪 Using test mode with account: {account_id} ({zone_name})")

        try:
            logger.info(
                f"🚀 Scanning test account: {zone_name} (account: {account_id})"
            )
            session = sm.get_session(account_id, zone_name, role, region, SESSION_NAME)
            matched = scan_resources(session)

            # Tag resources if requested
            if args.tag_nis_managed and matched:
                tag_stats = tag_resources_with_nis_managed(session, matched)
                logger.info(
                    f"🏷️ Tagging results - Success: {tag_stats['success']}, Failed: {tag_stats['failed']}"
                )
                if tag_stats["errors"]:
                    logger.warning(
                        f"⚠️ Tagging errors encountered: {len(tag_stats['errors'])} resources failed"
                    )

            write_results_to_csv(zone_name, matched)

            # Log basic statistics
            logger.info(f"📊 Scan completed - Matched resources: {len(matched)}")
        except Exception as e:
            logger.error(f"❌ Error scanning test account {zone_name}: {e}")
    else:
        # Use normal zone fetching logic
        try:
            zones = fetch_zones_from_url(zones_url)
            if landing_zones:
                zones = [
                    ln
                    for ln in zones
                    if any(ln.split()[1] == lz for lz in landing_zones)
                ]
            else:
                zones = filter_zones(zones, environment=environment)
        except Exception as e:
            logger.error(f"❌ Failed to fetch landing zones: {e}")
            return

        logger.info(f"🔍 Matched {len(zones)} zones for scanning")

        total_matched = 0
        total_tagged_success = 0
        total_tagged_failed = 0

        for line in zones:
            account_id, zone_name = line.split()
            try:
                logger.info(f"🚀 Scanning LZ: {zone_name} (account: {account_id})")
                session = sm.get_session(
                    account_id, zone_name, role, region, SESSION_NAME
                )
                matched = scan_resources(session)

                # Tag resources if requested
                if args.tag_nis_managed and matched:
                    tag_stats = tag_resources_with_nis_managed(session, matched)
                    total_tagged_success += tag_stats["success"]
                    total_tagged_failed += tag_stats["failed"]
                    logger.info(
                        f"🏷️ Tagging results for {zone_name} - Success: {tag_stats['success']}, Failed: {tag_stats['failed']}"
                    )
                    if tag_stats["errors"]:
                        logger.warning(
                            f"⚠️ Tagging errors in {zone_name}: {len(tag_stats['errors'])} resources failed"
                        )

                write_results_to_csv(zone_name, matched)

                # Aggregate statistics
                total_matched += len(matched)

                logger.info(
                    f"✅ Completed {zone_name} - Matched: {len(matched)} resources"
                )
            except Exception as e:
                logger.error(f"❌ Error scanning {zone_name}: {e}")

        # Log overall statistics
        if args.tag_nis_managed:
            logger.info(
                f"🏁 Overall scan completed - Total matched resources: {total_matched}, "
                f"Tagged successfully: {total_tagged_success}, Tagging failed: {total_tagged_failed}"
            )
        else:
            logger.info(
                f"🏁 Overall scan completed - Total matched resources: {total_matched}"
            )


if __name__ == "__main__":
    main()
