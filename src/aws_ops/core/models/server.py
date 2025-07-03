"""Simple Server Data Models

Simple data models for AWS EC2 server management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any


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
    name: str
    instance_type: str
    state: str
    platform: str = "linux"
    private_ip: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    @property
    def is_running(self) -> bool:
        return self.state == InstanceState.RUNNING.value

    @property
    def is_windows(self) -> bool:
        return self.platform.lower() == Platform.WINDOWS.value

    def get_tag(self, key: str, default: str = "") -> str:
        return self.tags.get(key, default)

    @classmethod
    def from_aws_instance(cls, instance: Dict[str, Any]) -> "ServerInfo":
        """Create ServerInfo from AWS instance data."""
        # Extract tags
        tags = {}
        for tag in instance.get("Tags", []):
            if tag.get("Key"):
                tags[tag["Key"]] = tag.get("Value", "")
        
        # Get name from tags
        name = tags.get("Name", instance.get("InstanceId", ""))
        
        return cls(
            instance_id=instance["InstanceId"],
            name=name,
            instance_type=instance.get("InstanceType", ""),
            state=instance.get("State", {}).get("Name", ""),
            platform=instance.get("Platform", "linux"),
            private_ip=instance.get("PrivateIpAddress"),
            tags=tags
        )
