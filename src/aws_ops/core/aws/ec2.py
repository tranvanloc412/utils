"""AWS EC2 Core Module

This module provides core EC2 functionality for the aws-ops package.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError


class EC2Manager:
    """AWS EC2 resource manager with common operations."""

    def __init__(self, session: boto3.Session, region: str = "ap-southeast-2"):
        """Initialize EC2Manager."""
        self.session = session
        self.region = region
        self.ec2_client = session.client("ec2", region_name=region)
        self.logger = logging.getLogger(__name__)

    def describe_instances(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        instance_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Describe EC2 instances with optional filtering.

        Args:
            filters: EC2 filters for describe_instances
            instance_ids: Specific instance IDs to describe

        Returns:
            List of instance information dictionaries
        """
        try:
            params = {}
            if filters:
                params["Filters"] = filters
            if instance_ids:
                params["InstanceIds"] = instance_ids

            response = self.ec2_client.describe_instances(**params)
            instances = []

            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instances.append(instance)

            return instances

        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error describing instances: {e}")
            return []

    def get_instances_by_filter(
        self, filter_name: str, filter_values: List[str]
    ) -> List[Dict[str, Any]]:
        """Get instances by filter."""
        filters = [{"Name": filter_name, "Values": filter_values}]
        return self.describe_instances(filters=filters)

    def get_resource_tags(
        self, resource_id: str, resource_type: str = "instance"
    ) -> Dict[str, str]:
        """Get tags for a specific resource."""
        try:
            response = self.ec2_client.describe_tags(
                Filters=[
                    {"Name": "resource-id", "Values": [resource_id]},
                    {"Name": "resource-type", "Values": [resource_type]},
                ]
            )
            return {tag["Key"]: tag["Value"] for tag in response["Tags"]}
        except (ClientError, BotoCoreError) as e:
            self.logger.error(
                f"Error getting tags for {resource_type} {resource_id}: {e}"
            )
            return {}

    def _extract_tag_value(self, tags: List[Dict[str, str]], key: str) -> str:
        """Extract tag value by key."""
        for tag in tags:
            if tag["Key"] == key:
                return tag["Value"]
        return "N/A"

    def describe_snapshots(
        self,
        owner_ids: Optional[List[str]] = None,
        snapshot_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Describe EBS snapshots."""
        try:
            params = {"OwnerIds": owner_ids or ["self"]}
            if snapshot_ids:
                params["SnapshotIds"] = snapshot_ids
            response = self.ec2_client.describe_snapshots(**params)
            return response["Snapshots"]
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error describing snapshots: {e}")
            return []

    def get_old_snapshots(self, days_old: int = 30) -> List[Dict[str, Any]]:
        """Get snapshots older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        snapshots = self.describe_snapshots()
        return [
            snapshot
            for snapshot in snapshots
            if snapshot["StartTime"].replace(tzinfo=None) < cutoff_date
        ]

    def describe_volumes(
        self,
        volume_ids: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Describe EBS volumes."""
        try:
            params = {}
            if volume_ids:
                params["VolumeIds"] = volume_ids
            if filters:
                params["Filters"] = filters
            response = self.ec2_client.describe_volumes(**params)
            return response["Volumes"]
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error describing volumes: {e}")
            return []

    def manage_instances(
        self, instance_ids: List[str], action: str, force: bool = False
    ) -> Dict[str, Any]:
        """Manage EC2 instances (start, stop, reboot)."""
        try:
            if action == "start":
                response = self.ec2_client.start_instances(InstanceIds=instance_ids)
            elif action == "stop":
                response = self.ec2_client.stop_instances(
                    InstanceIds=instance_ids, Force=force
                )
            elif action == "reboot":
                response = self.ec2_client.reboot_instances(InstanceIds=instance_ids)
            else:
                raise ValueError(f"Invalid action: {action}")

            self.logger.info(f"{action.capitalize()}ed instances: {instance_ids}")
            return response
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error {action}ing instances {instance_ids}: {e}")
            return {}


def create_ec2_manager(
    session: boto3.Session, region: str = "ap-southeast-2"
) -> EC2Manager:
    """Factory function to create EC2Manager instance."""
    return EC2Manager(session, region)
