#!/usr/bin/env python3

import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from boto3 import Session

from aws_ops.core.processors.report_generator import CSVReportGenerator
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY
from aws_ops.jobs.base import BaseJob
from aws_ops.utils.config import ConfigManager


def scan_ebs_snapshots(
    session: Session,
    zone_info: Dict[str, Any],
    days_old: int = 30,
    managed_by: Optional[str] = None,
    logger: Optional[object] = None,
    correlation_id: str = None,
) -> List[Dict[str, Any]]:
    """Scan EBS snapshots with simple filtering.
    
    Args:
        session: AWS session
        zone_info: Zone information
        days_old: Number of days to look back
        managed_by: Filter by managed_by tag (e.g., 'CMS') or None for all
        logger: Logger instance
        correlation_id: Correlation ID for tracking
        
    Returns:
        List of filtered snapshots
    """
    try:
        if logger:
            filter_msg = f"managed_by={managed_by}" if managed_by else "all snapshots"
            logger.info(
                f"[{correlation_id or 'N/A'}] Scanning snapshots in {zone_info.get('name', 'unknown')} "
                f"(last {days_old} days, {filter_msg})"
            )

        ec2 = session.client("ec2")
        
        # Calculate date threshold
        cutoff_date = datetime.now() - timedelta(days=days_old)

        # Basic filters
        filters = [
            {"Name": "owner-id", "Values": ["self"]},
            {"Name": "status", "Values": ["completed"]},
        ]
        
        # Add managed_by filter - default to CMS unless 'all' is specified
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

        # Get snapshots
        response = ec2.describe_snapshots(Filters=filters)
        snapshots = response["Snapshots"]

        # Filter by date and add basic metadata
        filtered_snapshots = []
        for snapshot in snapshots:
            start_time = snapshot["StartTime"].replace(tzinfo=None)
            if start_time >= cutoff_date:
                # Add simple calculated fields
                snapshot["Age"] = (datetime.now() - start_time).days
                snapshot["SizeGB"] = snapshot.get("VolumeSize", 0)
                snapshot["StartTimeStr"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
                filtered_snapshots.append(snapshot)

        if logger:
            logger.info(
                f"[{correlation_id or 'N/A'}] Found {len(filtered_snapshots)} snapshots"
            )

        return filtered_snapshots

    except Exception as e:
        if logger:
            logger.error(f"[{correlation_id or 'N/A'}] Error scanning snapshots: {e}")
        return []


class ScanBackups(BaseJob):
    """Simple job for scanning EBS snapshots with basic filtering."""

    def __init__(self, config_manager: ConfigManager = None):
        super().__init__(
            config_manager=config_manager,
            job_name="scan_backups",
            default_role="provision",
        )
        self.report_generator = None

    def execute(self, zone_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute the backup scanning job."""
        try:
            # Get parameters
            days_old = kwargs.get("days_old", 30)
            managed_by = kwargs.get("managed_by")
            generate_report = kwargs.get("generate_report", True)

            # Create AWS session
            session = self.create_aws_session(zone_info, role_type=self.default_role)

            # Scan snapshots
            snapshots = scan_ebs_snapshots(
                session, zone_info, days_old, managed_by, self.logger, self.correlation_id
            )

            # Generate report if requested
            report_path = None
            if generate_report and snapshots:
                report_path = self._generate_report(snapshots, zone_info)

            return {
                "status": "success",
                "zone": zone_info,
                "snapshots_found": len(snapshots),
                "snapshots": snapshots,
                "report_path": report_path,
                "correlation_id": self.correlation_id,
            }

        except Exception as e:
            self.logger.error(
                f"[{self.correlation_id}] Error executing scan backup job: {e}"
            )
            return {
                "status": "error",
                "error": str(e),
                "snapshots_found": 0,
                "correlation_id": self.correlation_id,
            }

    def _generate_report(
        self, snapshots: List[Dict[str, Any]], zone_info: Dict[str, Any]
    ) -> str:
        """Generate a simple CSV report of snapshots."""
        try:
            # Initialize report generator
            if not self.report_generator:
                report_path = self.config_manager.get_report_path()
                self.report_generator = CSVReportGenerator(output_dir=report_path)

            # Prepare report data
            report_data = []
            scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for snapshot in snapshots:
                # Get managed_by tag
                managed_by = ""
                for tag in snapshot.get("Tags", []):
                    if tag["Key"] == MANAGED_BY_KEY:
                        managed_by = tag["Value"]
                        break

                report_item = {
                    "LandingZone": zone_info.get("name", ""),
                    "Account": zone_info.get("account_id", ""),
                    "SnapshotId": snapshot.get("SnapshotId", ""),
                    "VolumeId": snapshot.get("VolumeId", ""),
                    "Description": snapshot.get("Description", ""),
                    "StartTime": snapshot.get("StartTimeStr", ""),
                    "State": snapshot.get("State", ""),
                    "SizeGB": snapshot.get("SizeGB", 0),
                    "Age": snapshot.get("Age", 0),
                    "ManagedBy": managed_by,
                    "ScanTime": scan_time,
                }
                report_data.append(report_item)

            # Generate report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zone_name = zone_info.get("name", "unknown").replace(" ", "_").lower()
            filename = f"backups_{zone_name}_{timestamp}.csv"

            column_order = [
                "LandingZone",
                "Account",
                "SnapshotId",
                "VolumeId",
                "Description",
                "StartTime",
                "State",
                "SizeGB",
                "Age",
                "ManagedBy",
                "ScanTime",
            ]

            success = self.report_generator.generate_report(
                report_data, filename, column_order
            )
            
            if success:
                report_file = os.path.join(self.config_manager.get_report_path(), filename)
                self.logger.info(
                    f"[{self.correlation_id}] Generated backup report: {report_file}"
                )
                return report_file
            else:
                self.logger.warning(
                    f"[{self.correlation_id}] Failed to generate backup report"
                )
                return None
                
        except Exception as e:
            self.logger.error(
                f"[{self.correlation_id}] Error generating report: {e}"
            )
            return None
