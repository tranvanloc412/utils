"""Simple data models for AWS AMI management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any


class AMIState(Enum):
    """AMI states."""
    PENDING = "pending"
    AVAILABLE = "available"
    INVALID = "invalid"
    FAILED = "failed"

@dataclass
class AMIInfo:
    """Simple AMI information model."""
    image_id: str
    name: str
    state: str = "available"
    platform: str = "linux"
    tags: Dict[str, str] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.state == AMIState.AVAILABLE.value

    @property
    def is_windows(self) -> bool:
        return self.platform.lower() == "windows"

    def get_tag(self, key: str, default: str = "") -> str:
        return self.tags.get(key, default)

    @classmethod
    def from_aws_image(cls, image: Dict[str, Any]) -> "AMIInfo":
        """Create AMIInfo from AWS image data."""
        # Extract tags
        tags = {}
        for tag in image.get("Tags", []):
            if tag.get("Key"):
                tags[tag["Key"]] = tag.get("Value", "")

        return cls(
            image_id=image["ImageId"],
            name=image.get("Name", ""),
            state=image.get("State", "available"),
            platform=image.get("Platform", "linux"),
            tags=tags
        )