"""Simple Server Data Models

Simplified data models for AWS EC2 server management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class InstanceState(Enum):
    """EC2 Instance states."""

    RUNNING = "running"
    STOPPED = "stopped"
    TERMINATED = "terminated"


class Platform(Enum):
    """Server platforms."""

    WINDOWS = "windows"
    LINUX = "linux"


@dataclass
class ServerInfo:
    """Simple server information model."""

    instance_id: str
    instance_name: str
    instance_type: str
    state: InstanceState
    platform: str
    private_ip: Optional[str] = None
    launch_time: Optional[datetime] = None
    managed_by: str = "SS"
    environment: str = "DEVELOPMENT"
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

    @property
    def is_running(self) -> bool:
        return self.state == "running"

    @property
    def is_windows(self) -> bool:
        return self.platform.lower() == "windows"

    def get_tag(self, key: str, default: str = "") -> str:
        return self.tags.get(key, default)

    @property
    def is_cms_managed(self) -> bool:
        managed_by = self.get_tag("managed_by", "SS").upper()
        return managed_by == "CMS"

    @property
    def name(self) -> str:
        return self.get_tag("Name", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "instance_type": self.instance_type,
            "state": self.state,
            "platform": self.platform,
            "private_ip": self.private_ip,
            "launch_time": self.launch_time.isoformat() if self.launch_time else None,
            "managed_by": self.managed_by,
            "environment": self.environment,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerInfo":
        launch_time = None
        if data.get("launch_time"):
            if isinstance(data["launch_time"], str):
                launch_time = datetime.fromisoformat(data["launch_time"])
            elif isinstance(data["launch_time"], datetime):
                launch_time = data["launch_time"]

        return cls(
            instance_id=data["instance_id"],
            instance_name=data.get("instance_name", ""),
            instance_type=data.get("instance_type", ""),
            state=data.get("state", ""),
            platform=data.get("platform", ""),
            private_ip=data.get("private_ip"),
            launch_time=launch_time,
            managed_by=data.get("managed_by", "SS"),
            environment=data.get("environment", "DEVELOPMENT"),
            tags=data.get("tags", {}),
        )

    @classmethod
    def from_aws_instance(cls, instance: Dict[str, Any]) -> "ServerInfo":
        # Extract tags
        tags = {}
        instance_name = ""
        for tag in instance.get("Tags", []):
            key, value = tag["Key"], tag["Value"]
            tags[key] = value
            if key == "Name":
                instance_name = value

        # Handle launch time
        launch_time = instance.get("LaunchTime")
        if isinstance(launch_time, str):
            launch_time = datetime.fromisoformat(launch_time.replace("Z", "+00:00"))

        # Extract managed_by from tags
        managed_by = tags.get("managed_by", "SS")

        # Extract environment from tags
        environment = tags.get("Environment", "DEVELOPMENT")

        return cls(
            instance_id=instance["InstanceId"],
            instance_name=instance_name,
            instance_type=instance.get("InstanceType", ""),
            state=instance.get("State", {}).get("Name", ""),
            platform=instance.get("Platform", "linux"),
            private_ip=instance.get("PrivateIpAddress"),
            launch_time=launch_time,
            managed_by=managed_by,
            environment=environment,
            tags=tags,
        )


def create_server_info(instance_data: Dict[str, Any]) -> ServerInfo:
    """Factory function to create ServerInfo from AWS instance data."""
    return ServerInfo.from_aws_instance(instance_data)


def create_server_list(instances: List[Dict[str, Any]]) -> List[ServerInfo]:
    """Factory function to create list of ServerInfo from AWS instances."""
    return [create_server_info(instance) for instance in instances]
