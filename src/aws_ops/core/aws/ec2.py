"""Simple EC2 Manager for AWS operations."""

from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_ops.utils.logger import setup_logger


class EC2Manager:
    """Simple AWS EC2 resource manager."""

    def __init__(self, session: boto3.Session, region: str = "ap-southeast-2"):
        """Initialize EC2Manager."""
        self.session = session
        self.region = region
        self.ec2_client = session.client("ec2", region_name=region)
        self.logger = setup_logger(__name__, "ec2_manager.log")

    def describe_instances(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        instance_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Describe EC2 instances with optional filtering."""
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

        except ClientError as e:
            self.logger.error(f"Error describing instances: {e}")
            return []

    def start_instances(self, instance_ids: List[str]) -> bool:
        """Start EC2 instances."""
        try:
            self.ec2_client.start_instances(InstanceIds=instance_ids)
            self.logger.info(f"Started instances: {instance_ids}")
            return True
        except ClientError as e:
            self.logger.error(f"Error starting instances: {e}")
            return False

    def stop_instances(self, instance_ids: List[str]) -> bool:
        """Stop EC2 instances."""
        try:
            self.ec2_client.stop_instances(InstanceIds=instance_ids)
            self.logger.info(f"Stopped instances: {instance_ids}")
            return True
        except ClientError as e:
            self.logger.error(f"Error stopping instances: {e}")
            return False

    def describe_images(self, image_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Describe AMI images."""
        try:
            params = {"Owners": ["self"]}
            if image_ids:
                params["ImageIds"] = image_ids
            response = self.ec2_client.describe_images(**params)
            return response["Images"]
        except ClientError as e:
            self.logger.error(f"Error describing images: {e}")
            return []

    def describe_snapshots(self, snapshot_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Describe EBS snapshots."""
        try:
            params = {"OwnerIds": ["self"]}
            if snapshot_ids:
                params["SnapshotIds"] = snapshot_ids
            response = self.ec2_client.describe_snapshots(**params)
            return response["Snapshots"]
        except ClientError as e:
            self.logger.error(f"Error describing snapshots: {e}")
            return []


def create_ec2_manager(session: boto3.Session, region: str = "ap-southeast-2") -> EC2Manager:
    """Create EC2Manager instance."""
    return EC2Manager(session, region)
