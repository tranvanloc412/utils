#!/usr/bin/env python3

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from boto3 import Session

from aws_ops.core.aws.ec2 import create_ec2_manager
from aws_ops.core.models.server import ServerInfo
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY
from aws_ops.core.processors.report_generator import CSVReportGenerator
from aws_ops.jobs.base import BaseJob
from aws_ops.utils.lz import extract_environment_from_zone
from aws_ops.utils.config import ConfigManager


@dataclass
class ScanMetrics:
    """Simple metrics for scan operation tracking."""

    total_instances: int = 0
    processed_instances: int = 0
    scan_duration: float = 0.0


def scan_ec2_servers(
    session: Session,
    zone_info: Dict[str, Any],
    managed_by: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    correlation_id: str = None,
) -> List[Dict[str, Any]]:
    """Scan EC2 servers in a zone with basic tag filtering.

    Args:
        session: AWS session
        zone_info: Zone information
        managed_by: Filter by managed_by tag (e.g., 'CMS') or None for all
        logger: Logger instance
        correlation_id: Correlation ID for tracking
        
    Returns:
        List of filtered servers
    """
    scan_start = time.time()
    metrics = ScanMetrics()

    try:
        if logger:
            logger.info( 
                f"[{correlation_id or 'N/A'}] Starting EC2 server scan for zone: {zone_info.get('name', 'unknown')}"
            )

        # Apply managed_by filtering - default to CMS unless 'all' is specified
        filters = []
        if managed_by and managed_by.lower() != "all":
            filters.append({
                "Name": f"tag:{MANAGED_BY_KEY}",
                "Values": [managed_by]
            })
        elif not managed_by or managed_by == CMS_MANAGED:
            # Default to CMS filtering when not specified or explicitly CMS
            filters.append({
                "Name": f"tag:{MANAGED_BY_KEY}",
                "Values": [CMS_MANAGED]
            })
            
        ec2_manager = create_ec2_manager(session)
        instances = ec2_manager.describe_instances(filters=filters) if filters else ec2_manager.describe_instances()
        metrics.total_instances = len(instances)

        servers = []

        # Process instances with basic information collection
        for instance in instances:
            server = ServerInfo.from_aws_instance(instance)

            # Get managed_by tag value
            managed_by_tag = server.get_tag(MANAGED_BY_KEY, "")
            managed_by_value = managed_by_tag if managed_by_tag else "SS"

            # Basic server information
            server_dict = {
                "instance_id": server.instance_id,
                "instance_name": server.get_tag("Name"),
                "instance_type": server.instance_type,
                "state": server.state,
                "platform": server.platform,
                "zone": zone_info.get("name", "unknown"),
                "environment_tag": server.get_tag("Environment", ""),
                "managed_by": managed_by_value,
            }

            servers.append(server_dict)
            metrics.processed_instances += 1

        # Calculate basic metrics
        metrics.scan_duration = time.time() - scan_start

        if logger:
            logger.info(
                f"[{correlation_id or 'N/A'}] Found {len(servers)} servers in zone {zone_info.get('name', 'unknown')} "
                f"(scan took {round(metrics.scan_duration, 2)}s)"
            )

        return servers

    except Exception as e:
        if logger:
            logger.error(f"[{correlation_id or 'N/A'}] Error scanning servers: {e}")
        else:
            print(f"Error scanning servers: {e}")
        return []


class ScanServers(BaseJob):
    """Simple job for scanning EC2 servers.

    Features:
    - Basic instance metadata collection
    - Simple tag-based filtering
    - CSV report generation
    """

    def __init__(self, config_manager: ConfigManager = None):
        super().__init__(
            config_manager=config_manager,
            job_name="scan_servers",
            default_role="provision",
        )
        self.report_generator = None

    def _generate_report(
        self, servers: List[Dict[str, Any]], zone_info: Dict[str, Any]
    ) -> str:
        """Generate a CSV report of servers"""
        # Initialize report generator if not already done
        if not self.report_generator:
            report_path = self.config_manager.get_report_path()
            self.report_generator = CSVReportGenerator(output_dir=report_path)

        # Prepare data for report - add timestamp and additional fields
        report_data = []
        scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for server in servers:
            # Extract environment from landing zone name
            landing_zone = server.get("zone", "")
            try:
                lz_environment = extract_environment_from_zone(landing_zone)
            except Exception:
                # Fallback to original environment if extraction fails
                lz_environment = zone_info.get("environment", "")

            # Get Environment tag or fallback to LzEnvironment
            environment = server.get("environment_tag", "") or lz_environment

            # Basic report item
            report_item = {
                "LandingZone": landing_zone,
                "Account": zone_info.get("account_id", ""),
                "LZEnvironment": lz_environment,
                "Environment": environment,
                "InstanceId": server.get("instance_id", ""),
                "InstanceName": server.get("instance_name", ""),
                "InstanceType": server.get("instance_type", ""),
                "Platform": server.get("platform", ""),
                "ScanTime": scan_time,
                "State": server.get("state", ""),
                "managed_by": server.get("managed_by", ""),
            }
            report_data.append(report_item)

        # Generate the report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zone_name = zone_info.get("name", "unknown").replace(" ", "_").lower()
        filename = f"servers_{zone_name}_{timestamp}.csv"

        # Define column order
        column_order = [
            "LandingZone",
            "Account",
            "LZEnvironment",
            "InstanceId",
            "InstanceName",
            "InstanceType",
            "Environment",
            "Platform",
            "ScanTime",
            "State",
            "managed_by",
        ]

        success = self.report_generator.generate_report(
            report_data, filename, column_order
        )
        if success:
            report_file = os.path.join(self.config_manager.get_report_path(), filename)
            self.logger.info(
                f"[{self.correlation_id}] Generated server report: {report_file}"
            )
            return report_file
        else:
            self.logger.warning(
                f"[{self.correlation_id}] Failed to generate server report"
            )
            return None

    def execute(self, zone_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute the server scanning job."""
        try:
            # Get parameters
            generate_report = kwargs.get("generate_report", True)
            managed_by = kwargs.get("managed_by")

            # Create AWS session
            session = self.create_aws_session(zone_info, role_type=self.default_role)

            # Scan servers
            servers = scan_ec2_servers(
                session, zone_info, managed_by, self.logger, self.correlation_id
            )

            # Generate report if requested
            report_path = None
            if generate_report and servers:
                report_path = self._generate_report(servers, zone_info)

            return {
                "status": "success",
                "servers_found": len(servers),
                "servers": servers,
                "report_path": report_path,
            }
        except Exception as e:
            self.logger.error(
                f"[{self.correlation_id}] Error executing scan server job: {e}"
            )
            return {
                "status": "error",
                "error": str(e),
                "servers_found": 0,
                "correlation_id": self.correlation_id,
            }
