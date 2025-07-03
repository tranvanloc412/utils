#!/usr/bin/env python3
"""
EC2 utility functions for AWS Operations.

This module provides shared functionality for EC2 instance operations,
reducing code duplication across job classes.
"""

from typing import Dict, List, Optional
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY


def find_instances_by_state(
    ec2_client,
    instance_state: str,
    server_name: Optional[str] = None,
    operation_all: bool = False,
    managed_by: Optional[str] = None,
) -> List[Dict]:
    """
    Find EC2 instances by state with optional filtering.

    This is a shared utility function used by both start_servers and stop_servers
    jobs to eliminate code duplication.

    Args:
        ec2_client: Boto3 EC2 client instance
        instance_state: EC2 instance state to filter by ('running', 'stopped', etc.)
        server_name: Optional server name pattern to match (uses wildcard matching)
        operation_all: If True, ignores server_name filter for bulk operations
        managed_by: Management filter - 'ALL' for all instances, otherwise filters by tag

    Returns:
        List of EC2 instance dictionaries matching the criteria

    Example:
        # Find all stopped instances with CMS management
        instances = find_instances_by_state(ec2_client, 'stopped')

        # Find running instances for specific server
        instances = find_instances_by_state(
            ec2_client, 'running', server_name='web-server', operation_all=False
        )

        # Find all running instances regardless of management
        instances = find_instances_by_state(
            ec2_client, 'running', operation_all=True, managed_by='ALL'
        )
    """
    filters = [{"Name": "instance-state-name", "Values": [instance_state]}]

    # Add server name filter if specified and not doing bulk operation
    if server_name and not operation_all:
        filters.append({"Name": "tag:Name", "Values": [f"*{server_name}*"]})

    # Add managed_by filter - default to CMS if not specified or if CMS is explicitly chosen
    if not managed_by or managed_by.upper() != "ALL":
        filters.append({"Name": f"tag:{MANAGED_BY_KEY}", "Values": [CMS_MANAGED]})

    response = ec2_client.describe_instances(Filters=filters)

    instances = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instances.append(instance)

    return instances


def get_instance_name(instances: List[Dict], instance_id: str) -> str:
    """
    Get the Name tag value for a specific instance.

    Args:
        instances: List of EC2 instance dictionaries
        instance_id: The instance ID to look up

    Returns:
        The Name tag value, or a default string if not found

    Example:
        name = get_instance_name(instances, 'i-1234567890abcdef0')
    """
    for instance in instances:
        if instance.get("InstanceId") == instance_id:
            tags = instance.get("Tags", [])
            for tag in tags:
                if tag.get("Key") == "Name":
                    return tag.get("Value", "Unknown")
            return "No Name Tag"
    return "Unknown"


def get_instance_tags(instance: Dict) -> Dict[str, str]:
    """
    Extract tags from an EC2 instance as a key-value dictionary.

    Args:
        instance: EC2 instance dictionary

    Returns:
        Dictionary of tag keys and values

    Example:
        tags = get_instance_tags(instance)
        managed_by = tags.get('managed_by', 'Unknown')
    """
    tags = {}
    for tag in instance.get("Tags", []):
        key = tag.get("Key")
        value = tag.get("Value")
        if key and value:
            tags[key] = value
    return tags


def format_instance_info(instance: Dict) -> Dict[str, str]:
    """
    Format instance information for logging and display.

    Args:
        instance: EC2 instance dictionary

    Returns:
        Dictionary with formatted instance information

    Example:
        info = format_instance_info(instance)
        print(f"Instance: {info['name']} ({info['id']}) - {info['state']}")
    """
    tags = get_instance_tags(instance)

    return {
        "id": instance.get("InstanceId", "Unknown"),
        "name": tags.get("Name", "No Name Tag"),
        "state": instance.get("State", {}).get("Name", "Unknown"),
        "instance_type": instance.get("InstanceType", "Unknown"),
        "managed_by": tags.get("managed_by", "Unmanaged"),
        "availability_zone": instance.get("Placement", {}).get(
            "AvailabilityZone", "Unknown"
        ),
        "private_ip": instance.get("PrivateIpAddress", "N/A"),
        "public_ip": instance.get("PublicIpAddress", "N/A"),
    }
