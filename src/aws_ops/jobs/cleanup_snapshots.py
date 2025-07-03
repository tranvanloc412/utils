#!/usr/bin/env python3
"""
Cleanup Snapshots Job - Simplified Version

This module provides functionality to cleanup old EBS snapshots across multiple AWS accounts.
Simplified version with essential features and safety checks.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .base import BaseJob
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY


class CleanupSnapshotsJob(BaseJob):
    """Job to cleanup old EBS snapshots"""

    def __init__(self):
        super().__init__(job_name="cleanup_snapshots", default_role="provision")

    def execute(self, zone_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Cleanup old snapshots in the specified zone

        Args:
            zone_info: Dictionary containing zone information
            **kwargs: Additional parameters (days_old, dry_run, etc.)

        Returns:
            Dictionary with cleanup results
        """
        try:
            # Get parameters
            days_old = kwargs.get("days_old", 30)
            dry_run = kwargs.get("dry_run", True)  # Default to dry run for safety
            exclude_ami_snapshots = kwargs.get("exclude_ami_snapshots", True)
            volume_id = kwargs.get("volume_id")
            managed_by = kwargs.get("managed_by")

            # Validate parameters
            if days_old < 7:
                return {
                    "status": "error",
                    "message": "Minimum retention period is 7 days for safety",
                }

            # Create EC2 client
            session = self.create_aws_session(zone_info)
            ec2 = session.client('ec2')

            # Find snapshots to cleanup
            snapshots_to_delete = self._find_snapshots_to_delete(
                ec2, days_old, exclude_ami_snapshots, volume_id, managed_by
            )

            if not snapshots_to_delete:
                return {
                    "status": "success",
                    "message": "No snapshots found for cleanup",
                    "snapshots_deleted": 0,
                }

            # Perform cleanup
            if dry_run:
                return {
                    "status": "success",
                    "message": f"DRY RUN: Would delete {len(snapshots_to_delete)} snapshots",
                    "snapshots_found": len(snapshots_to_delete),
                    "snapshots": [snap["SnapshotId"] for snap in snapshots_to_delete],
                    "total_size_gb": sum(
                        snap.get("VolumeSize", 0) for snap in snapshots_to_delete
                    ),
                }

            # Actually delete snapshots
            deleted_snapshots = self._delete_snapshots(ec2, snapshots_to_delete)

            return {
                "status": "success",
                "message": f"Deleted {len(deleted_snapshots)} snapshots",
                "snapshots_deleted": len(deleted_snapshots),
                "snapshots": deleted_snapshots,
                "total_size_gb": sum(
                    snap.get("VolumeSize", 0) for snap in snapshots_to_delete
                ),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to cleanup snapshots: {str(e)}",
                "error": str(e),
            }

    def _find_snapshots_to_delete(
        self,
        ec2_client,
        days_old: int,
        exclude_ami_snapshots: bool,
        volume_id: Optional[str],
        managed_by: Optional[str] = None,
    ) -> List[Dict]:
        """
        Find snapshots that should be deleted

        Args:
            ec2_client: EC2 client
            days_old: Minimum age in days for deletion
            exclude_ami_snapshots: Whether to exclude AMI-related snapshots
            volume_id: Specific volume ID to filter
            managed_by: Filter by management type (CMS or all)

        Returns:
            List of snapshot dictionaries to delete
        """
        # Calculate date threshold
        cutoff_date = datetime.now() - timedelta(days=days_old)

        # Build filters
        filters = [
            {"Name": "owner-id", "Values": ["self"]},
            {"Name": "status", "Values": ["completed"]},
        ]

        if volume_id:
            filters.append({"Name": "volume-id", "Values": [volume_id]})

        # Add managed_by filter - default to CMS if not specified or if CMS is explicitly chosen
        if not managed_by or managed_by.upper() != "ALL":
            filters.append({"Name": f"tag:{MANAGED_BY_KEY}", "Values": [CMS_MANAGED]})

        # Get snapshots
        response = ec2_client.describe_snapshots(Filters=filters)
        snapshots = response["Snapshots"]

        # Filter snapshots for deletion
        snapshots_to_delete = []
        for snapshot in snapshots:
            # Check age
            start_time = snapshot["StartTime"].replace(tzinfo=None)
            if start_time >= cutoff_date:
                continue  # Too recent

            # Check if it's an AMI snapshot
            if exclude_ami_snapshots and self._is_ami_snapshot(snapshot):
                continue

            # Check if snapshot is in use
            if self._is_snapshot_in_use(ec2_client, snapshot["SnapshotId"]):
                continue

            snapshots_to_delete.append(snapshot)

        return snapshots_to_delete

    def _is_ami_snapshot(self, snapshot: Dict) -> bool:
        """
        Check if snapshot is related to an AMI

        Args:
            snapshot: Snapshot dictionary

        Returns:
            True if snapshot is AMI-related
        """
        description = snapshot.get("Description", "")
        return (
            "Created by CreateImage" in description
            or "ami-" in description
            or "Copied for DestinationAmi" in description
        )

    def _is_snapshot_in_use(self, ec2_client, snapshot_id: str) -> bool:
        """
        Check if snapshot is currently in use by AMIs or other resources

        Args:
            ec2_client: EC2 client
            snapshot_id: Snapshot ID to check

        Returns:
            True if snapshot is in use
        """
        try:
            # Check if used by AMIs
            response = ec2_client.describe_images(
                Filters=[
                    {
                        "Name": "block-device-mapping.snapshot-id",
                        "Values": [snapshot_id],
                    }
                ]
            )

            if response["Images"]:
                return True  # Snapshot is used by an AMI

            # Could add more checks here (e.g., launch templates, etc.)
            return False

        except Exception:
            # If we can't determine, err on the side of caution
            return True

    def _delete_snapshots(self, ec2_client, snapshots: List[Dict]) -> List[str]:
        """
        Delete the specified snapshots

        Args:
            ec2_client: EC2 client
            snapshots: List of snapshot dictionaries to delete

        Returns:
            List of successfully deleted snapshot IDs
        """
        deleted_snapshots = []

        for snapshot in snapshots:
            try:
                snapshot_id = snapshot["SnapshotId"]
                ec2_client.delete_snapshot(SnapshotId=snapshot_id)
                deleted_snapshots.append(snapshot_id)

            except Exception as e:
                # Log error but continue with other snapshots
                self.logger.error(
                    f"Failed to delete snapshot {snapshot['SnapshotId']}: {e}"
                )
                continue

        return deleted_snapshots
