"""Simple data models for AWS EBS snapshot management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any


class SnapshotState(Enum):
    """EBS Snapshot states."""
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SnapshotInfo:
    """Simple snapshot information model."""
    snapshot_id: str
    volume_id: str
    volume_size: int
    state: str
    description: str = ""
    encrypted: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    
    @property
    def is_completed(self) -> bool:
        return self.state == SnapshotState.COMPLETED.value
    
    def get_tag(self, key: str, default: str = "") -> str:
        return self.tags.get(key, default)
    
    @classmethod
    def from_aws_snapshot(cls, snapshot: Dict[str, Any]) -> "SnapshotInfo":
        """Create SnapshotInfo from AWS snapshot data."""
        # Extract tags
        tags = {}
        for tag in snapshot.get("Tags", []):
            if tag.get("Key"):
                tags[tag["Key"]] = tag.get("Value", "")
        
        return cls(
            snapshot_id=snapshot["SnapshotId"],
            volume_id=snapshot.get("VolumeId", ""),
            volume_size=snapshot.get("VolumeSize", 0),
            state=snapshot.get("State", "completed"),
            description=snapshot.get("Description", ""),
            encrypted=snapshot.get("Encrypted", False),
            tags=tags
        )