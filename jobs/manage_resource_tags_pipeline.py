#!/usr/bin/env python3
"""
Simplified AWS Resource Tag Scanner

Scans AWS resources across landing zones and applies tag-based filtering.
Supports both Resource Groups Tagging API and direct service APIs.
"""

import argparse
import csv
import logging
import sys
from dataclasses import dataclass, field


from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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

# Constants
SESSION_NAME = "scan-tags"
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

# Tag presets for common exclusion patterns
TAG_PRESETS = {
    "asg": [{"Key": "aws:autoscaling:groupName"}],
    "nabserv": [{"Key": "Name", "Values": ["nef-jenkins"], "MatchType": "contains"}],
    "nef2": [{"Key": "HIPmgmtEKS", "Values": ["Yes"]}],
    "cps": [{"Key": "HIPLocked", "Values": ["Yes"]}],
    "wiz": [{"Key": "wiz"}],
    "managed_by_cms": [{"Key": "managed_by", "Values": ["CMS"]}],
}

# Standard exclude rule combining all common exclusions
STANDARD_EXCLUDE = (
    TAG_PRESETS["nef2"]
    + TAG_PRESETS["nabserv"]
    + TAG_PRESETS["cps"]
    + TAG_PRESETS["wiz"]
)


@dataclass
class ServiceConfig:
    """Configuration for AWS service scanning"""

    resource_type: str
    api_method: str = "tagging_api"  # "tagging_api" or "direct"
    include_rules: List[Dict] = field(default_factory=list)
    exclude_rules: List[Dict] = field(default_factory=lambda: STANDARD_EXCLUDE)


# Unified service configuration
SERVICE_CONFIGS = {
    "ec2": ServiceConfig(
        resource_type="ec2:instance",
        include_rules=TAG_PRESETS["managed_by_cms"],
        exclude_rules=STANDARD_EXCLUDE + TAG_PRESETS["asg"],
    ),
    "ebs": ServiceConfig(
        resource_type="ec2:volume",
        exclude_rules=STANDARD_EXCLUDE + TAG_PRESETS["asg"],
    ),
    "asg": ServiceConfig(resource_type="autoscaling:autoScalingGroup"),
    "s3": ServiceConfig(resource_type="s3"),
    "sns": ServiceConfig(resource_type="sns"),
    "sqs": ServiceConfig(resource_type="sqs"),
    "dynamodb": ServiceConfig(resource_type="dynamodb:table"),
    "cloudwatch": ServiceConfig(resource_type="cloudwatch:alarm"),
    "events": ServiceConfig(resource_type="events:rule"),
    "lb": ServiceConfig(resource_type="elasticloadbalancing:loadbalancer"),
    "tg": ServiceConfig(resource_type="elasticloadbalancing:targetgroup"),
    "efs": ServiceConfig(resource_type="elasticfilesystem:file-system"),
    "fsx": ServiceConfig(resource_type="fsx:volume"),
    "sg": ServiceConfig(resource_type="ec2:security-group"),
    "kms": ServiceConfig(resource_type="kms:key"),
    "rds": ServiceConfig(resource_type="rds:db"),
    "lambda": ServiceConfig(resource_type="lambda:function"),
    # Direct API services
    "iam": ServiceConfig(resource_type="iam:role", api_method="direct"),
    "route53": ServiceConfig(resource_type="route53:hostedzone", api_method="direct"),
}


class TagMatcher:
    """Handles tag matching logic for include/exclude rules"""

    def __init__(
        self, include_rules: List[Dict] = None, exclude_rules: List[Dict] = None
    ):
        self.include_rules = include_rules or []
        self.exclude_rules = exclude_rules or []

    def matches(self, tags: List[Dict]) -> bool:
        """Check if tags match the configured rules"""
        return self._matches_includes(tags) and not self._matches_excludes(tags)

    def _matches_includes(self, tags: List[Dict]) -> bool:
        """Check if tags match include rules"""
        if not self.include_rules:
            return True

        tag_map = {t["Key"].lower(): t.get("Value", "").lower() for t in tags}

        for rule in self.include_rules:
            key = rule["Key"].lower()
            if "Values" in rule:
                tag_value = tag_map.get(key, "")
                match_type = rule.get("MatchType", "exact").lower()

                if match_type == "contains":
                    if not any(v.lower() in tag_value for v in rule["Values"]):
                        return False
                else:
                    if tag_value not in [v.lower() for v in rule["Values"]]:
                        return False
            elif key not in tag_map:
                return False
        return True

    def _matches_excludes(self, tags: List[Dict]) -> bool:
        """Check if tags match exclude rules"""
        tag_map = {t["Key"].lower(): t.get("Value", "").lower() for t in tags}

        for rule in self.exclude_rules:
            key = rule["Key"].lower()
            val = tag_map.get(key)
            if val:
                if "Values" in rule:
                    match_type = rule.get("MatchType", "contains").lower()
                    if match_type == "exact":
                        if val in [v.lower() for v in rule["Values"]]:
                            return True
                    else:
                        if any(bad_val.lower() in val for bad_val in rule["Values"]):
                            return True
                else:
                    return True
        return False


class ARNParser:
    """Handles ARN parsing and resource type extraction"""

    @staticmethod
    def extract_resource_type(arn: str) -> str:
        """Extract resource type from ARN"""
        arn_parts = arn.split(":")
        if len(arn_parts) < 3:
            return ""

        service = arn_parts[2]

        # Handle simplified ARN formats
        if service in ["s3", "sns", "sqs"]:
            return service

        # Handle DynamoDB, CloudWatch, EventBridge specific formats
        if len(arn_parts) >= 6:
            if service == "dynamodb" and "/table/" in arn:
                return "dynamodb:table"
            elif service == "cloudwatch" and ":alarm:" in arn:
                return "cloudwatch:alarm"
            elif service == "events" and "/rule/" in arn:
                return "events:rule"

            # Standard ARN format
            resource_part = arn_parts[5]
            if "/" in resource_part:
                resource_type = resource_part.split("/")[0]
                return f"{service}:{resource_type}"
            else:
                return f"{service}:{resource_part}"

        return service


class ResourceScanner:
    """Main resource scanning orchestrator"""

    def __init__(self, session):
        self.session = session
        self.arn_parser = ARNParser()

    def scan_all_resources(self) -> List[Tuple[str, Dict[str, str]]]:
        """Scan all configured resources"""
        matched = []

        # Scan via Resource Groups Tagging API
        tagging_api_services = {
            k: v for k, v in SERVICE_CONFIGS.items() if v.api_method == "tagging_api"
        }
        if tagging_api_services:
            resource_types = [
                config.resource_type for config in tagging_api_services.values()
            ]
            logger.info(
                f"🔍 Scanning via Tagging API: {len(resource_types)} resource types"
            )
            matched.extend(
                self._scan_with_tagging_api(resource_types, tagging_api_services)
            )

        # Scan via direct APIs
        direct_api_services = {
            k: v for k, v in SERVICE_CONFIGS.items() if v.api_method == "direct"
        }
        for service_name, config in direct_api_services.items():
            logger.info(f"🔍 Scanning {service_name} via direct API")
            matched.extend(self._scan_with_direct_api(service_name, config))

        logger.info(f"📊 Total scan complete: {len(matched)} resources matched")
        return matched

    def _scan_with_tagging_api(
        self, resource_types: List[str], service_configs: Dict[str, ServiceConfig]
    ) -> List[Tuple[str, Dict[str, str]]]:
        """Scan resources using Resource Groups Tagging API"""
        client = self.session.client("resourcegroupstaggingapi")
        paginator = client.get_paginator("get_resources")
        matched = []

        for page in paginator.paginate(ResourceTypeFilters=resource_types):
            for resource in page.get("ResourceTagMappingList", []):
                arn = resource["ResourceARN"]
                tags = resource.get("Tags", [])
                rtype = resource.get(
                    "ResourceType"
                ) or self.arn_parser.extract_resource_type(arn)

                # Find matching service config
                service_name = self._find_service_by_resource_type(
                    rtype, service_configs
                )
                if not service_name:
                    logger.debug(f"⚠️ Unknown resource type: {rtype} for ARN: {arn}")
                    continue

                config = service_configs[service_name]
                matcher = TagMatcher(config.include_rules, config.exclude_rules)

                if matcher.matches(tags):
                    tag_dict = {t["Key"]: t.get("Value", "") for t in tags}
                    matched.append((arn, tag_dict))
                    logger.info(f"[MATCH] {arn}")
                else:
                    logger.debug(f"⏭️ Filtered out: {arn}")

        return matched

    def _scan_with_direct_api(
        self, service_name: str, config: ServiceConfig
    ) -> List[Tuple[str, Dict[str, str]]]:
        """Scan resources using direct service APIs"""
        if service_name == "iam":
            return self._scan_iam_roles(config)
        elif service_name == "route53":
            return self._scan_route53_zones(config)
        else:
            logger.warning(f"⚠️ Direct API scanning not implemented for {service_name}")
            return []

    def _scan_iam_roles(self, config: ServiceConfig) -> List[Tuple[str, Dict[str, str]]]:
        """Scan IAM roles"""
        client = self.session.client("iam")
        paginator = client.get_paginator("list_roles")
        matched = []
        
        for page in paginator.paginate():
            for role in page.get("Roles", []):
                try:
                    role_name = role["RoleName"]
                    role_path = role.get("Path", "/")
                    arn = role["Arn"]
                    
                    # Filter out roles that start with TEST or ADES
                    if role_name.startswith(("TEST", "ADES")):
                        logger.debug(f"⏭️ Skipping role with excluded prefix: {role_name}")
                        continue
                    
                    # Filter out AWS service-linked roles
                    if role_path.startswith("/aws-service/"):
                        logger.debug(f"⏭️ Skipping AWS service-linked role: {role_name}")
                        continue
                    
                    # Add role without checking tags
                    matched.append((arn, {}))
                    logger.debug(f"✅ Added IAM role: {arn}")
                except Exception as e:
                    logger.debug(f"⚠️ Error processing IAM role {role.get('RoleName', 'unknown')}: {e}")
        
        return matched

    def _scan_route53_zones(
        self, config: ServiceConfig
    ) -> List[Tuple[str, Dict[str, str]]]:
        """Scan Route53 hosted zones"""
        client = self.session.client("route53")
        paginator = client.get_paginator("list_hosted_zones")
        matched = []
        matcher = TagMatcher(config.include_rules, config.exclude_rules)

        for page in paginator.paginate():
            for zone in page.get("HostedZones", []):
                try:
                    zone_id = zone["Id"].replace("/hostedzone/", "")
                    arn = f"arn:aws:route53:::hostedzone/{zone_id}"

                    response = client.list_tags_for_resource(
                        ResourceType="hostedzone", ResourceId=zone_id
                    )
                    tags = [
                        {"Key": tag["Key"], "Value": tag["Value"]}
                        for tag in response.get("ResourceTagSet", {}).get("Tags", [])
                    ]

                    if matcher.matches(tags):
                        tag_dict = {t["Key"]: t["Value"] for t in tags}
                        matched.append((arn, tag_dict))
                        logger.debug(f"✅ Matched Route53 zone: {arn}")
                except Exception as e:
                    logger.debug(f"⚠️ Error processing Route53 zone {zone_id}: {e}")

        return matched

    def _find_service_by_resource_type(
        self, resource_type: str, service_configs: Dict[str, ServiceConfig]
    ) -> Optional[str]:
        """Find service name by resource type"""
        for service_name, config in service_configs.items():
            if config.resource_type == resource_type:
                return service_name
        return None


class ResourceTagger:
    """Handles resource tagging operations"""

    def __init__(self, session):
        self.session = session

    def tag_resources_with_nis_managed(
        self, matched_resources: List[Tuple[str, Dict[str, str]]]
    ) -> Dict[str, int]:
        """Add 'nis_managed=true' tag to matched resources"""
        client = self.session.client("resourcegroupstaggingapi")
        stats = {"success": 0, "failed": 0, "errors": []}

        logger.info(
            f"🏷️ Tagging {len(matched_resources)} resources with nis_managed=true"
        )

        for arn, existing_tags in matched_resources:
            try:
                if "nis_managed" in existing_tags:
                    logger.debug(f"⏭️ Resource already tagged: {arn}")
                    stats["success"] += 1
                    continue

                response = client.tag_resources(
                    ResourceARNList=[arn], Tags={"nis_managed": "true"}
                )

                if response.get("FailedResourcesMap"):
                    error_info = response["FailedResourcesMap"][arn]
                    error_msg = f"{error_info.get('ErrorCode')}: {error_info.get('ErrorMessage')}"
                    logger.warning(f"⚠️ Failed to tag {arn}: {error_msg}")
                    stats["failed"] += 1
                    stats["errors"].append(f"{arn}: {error_msg}")
                else:
                    logger.debug(f"✅ Successfully tagged: {arn}")
                    stats["success"] += 1

            except ClientError as e:
                error_msg = (
                    f"{e.response['Error']['Code']}: {e.response['Error']['Message']}"
                )
                logger.warning(f"⚠️ Failed to tag {arn}: {error_msg}")
                stats["failed"] += 1
                stats["errors"].append(f"{arn}: {error_msg}")

        logger.info(
            f"🏷️ Tagging complete - Success: {stats['success']}, Failed: {stats['failed']}"
        )
        return stats


def write_results_to_csv(
    lz_name: str, matched_resources: List[Tuple[str, Dict[str, str]]]
):
    """Write scan results to CSV file"""
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
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Simplified AWS resource tag scanner")
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
        help="Environment suffix to filter zones",
    )
    parser.add_argument(
        "--test", "-t", action="store_true", help="Use test account configuration"
    )
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--tag-nis-managed",
        action="store_true",
        help="Add 'nis_managed=true' tag to matched resources",
    )
    parser.add_argument(
        "--pipeline",
        "-p",
        action="store_true",
        help="Pipeline mode: use AWS credentials from environment variables",
    )

    args = parser.parse_args()

    # Configure logging
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    # Initialize session manager
    sm = SessionManager()
    region = get_aws_region()
    
    if args.pipeline:
        # Pipeline mode: use environment variables
        logger.info("🔧 Pipeline mode: using AWS credentials from environment variables")
        try:
            session = sm.get_session_from_env(region, "pipeline")
            scanner = ResourceScanner(session)
            matched = scanner.scan_all_resources()
            
            if matched:
                logger.info(f"📊 Found {len(matched)} resources matching criteria")
                write_results_to_csv(matched, "pipeline")
                
                if args.tag_nis_managed:
                    tagger = ResourceTagger(session)
                    tagger.tag_resources(matched)
            else:
                logger.info("ℹ️ No resources found matching criteria")
                
        except ValueError as e:
            logger.error(f"❌ Pipeline mode error: {e}")
            return
        except Exception as e:
            logger.error(f"❌ Error in pipeline mode: {e}")
            return
            
    elif args.test:
        # Test mode
        role = get_provision_role()
        account_id = get_test_account_id()
        zone_name = get_test_account_name()

        if not account_id or not zone_name:
            logger.error("❌ Test account configuration not found")
            return

        logger.info(f"🧪 Test mode: {zone_name} ({account_id})")

        try:
            session = sm.get_session(account_id, zone_name, role, region, SESSION_NAME)
            scanner = ResourceScanner(session)
            matched = scanner.scan_all_resources()

            if args.tag_nis_managed and matched:
                tagger = ResourceTagger(session)
                tag_stats = tagger.tag_resources_with_nis_managed(matched)
                logger.info(
                    f"🏷️ Tagged - Success: {tag_stats['success']}, Failed: {tag_stats['failed']}"
                )

            write_results_to_csv(zone_name, matched)
            logger.info(f"📊 Scan complete: {len(matched)} resources matched")

        except Exception as e:
            logger.error(f"❌ Error scanning test account: {e}")

    else:
        # Production mode
        role = get_provision_role()
        try:
            zones_url = get_zones_url()
            zones = fetch_zones_from_url(zones_url)

            if args.landing_zones:
                zones = [
                    z
                    for z in zones
                    if any(z.split()[1] == lz for lz in args.landing_zones)
                ]
            else:
                zones = filter_zones(zones, environment=args.environment)

            logger.info(f"🔍 Scanning {len(zones)} zones")

            total_matched = 0
            total_tagged_success = 0
            total_tagged_failed = 0

            for line in zones:
                account_id, zone_name = line.split()
                try:
                    logger.info(f"🚀 Scanning: {zone_name} ({account_id})")
                    session = sm.get_session(
                        account_id, zone_name, role, region, SESSION_NAME
                    )
                    scanner = ResourceScanner(session)
                    matched = scanner.scan_all_resources()

                    if args.tag_nis_managed and matched:
                        tagger = ResourceTagger(session)
                        tag_stats = tagger.tag_resources_with_nis_managed(matched)
                        total_tagged_success += tag_stats["success"]
                        total_tagged_failed += tag_stats["failed"]

                    write_results_to_csv(zone_name, matched)
                    total_matched += len(matched)
                    logger.info(f"📊 {zone_name}: {len(matched)} resources matched")

                except Exception as e:
                    logger.error(f"❌ Error scanning {zone_name}: {e}")

            logger.info(f"🎯 Final summary: {total_matched} total resources matched")
            if args.tag_nis_managed:
                logger.info(
                    f"🏷️ Tagging summary - Success: {total_tagged_success}, Failed: {total_tagged_failed}"
                )

        except Exception as e:
            logger.error(f"❌ Failed to fetch landing zones: {e}")


if __name__ == "__main__":
    main()
