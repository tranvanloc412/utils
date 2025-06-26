"""AWS EBS Snapshot Data Models.

Simplified data models for AWS EBS snapshot management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


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
    account_id: str = ""
    description: str = ""
    start_time: Optional[datetime] = None
    encrypted: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
    
    @property
    def is_completed(self) -> bool:
        return self.state == "completed"
    
    @property
    def age_days(self) -> int:
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).days
    
    def get_tag(self, key: str, default: str = "") -> str:
        return self.tags.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'snapshot_id': self.snapshot_id,
            'volume_id': self.volume_id,
            'volume_size': self.volume_size,
            'state': self.state,
            'account_id': self.account_id,
            'description': self.description,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'encrypted': self.encrypted,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SnapshotInfo':
        start_time = None
        if data.get('start_time'):
            if isinstance(data['start_time'], str):
                start_time = datetime.fromisoformat(data['start_time'])
            elif isinstance(data['start_time'], datetime):
                start_time = data['start_time']
        
        return cls(
            snapshot_id=data['snapshot_id'],
            volume_id=data.get('volume_id', ''),
            volume_size=data.get('volume_size', 0),
            state=data.get('state', 'completed'),
            account_id=data.get('account_id', ''),
            description=data.get('description', ''),
            start_time=start_time,
            encrypted=data.get('encrypted', False),
            tags=data.get('tags', {})
        )
    
    @classmethod
    def from_aws_snapshot(cls, snapshot: Dict[str, Any]) -> 'SnapshotInfo':
        # Extract tags
        tags = {}
        for tag in snapshot.get('Tags', []):
            key = tag.get('Key', '')
            value = tag.get('Value', '')
            if key:
                tags[key] = value
        
        # Handle start time
        start_time = snapshot.get('StartTime')
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        elif hasattr(start_time, 'replace'):
            start_time = start_time.replace(tzinfo=None)
        
        return cls(
            snapshot_id=snapshot['SnapshotId'],
            volume_id=snapshot.get('VolumeId', ''),
            volume_size=snapshot.get('VolumeSize', 0),
            state=snapshot.get('State', 'completed'),
            account_id=snapshot.get('OwnerId', ''),
            description=snapshot.get('Description', ''),
            start_time=start_time,
            encrypted=snapshot.get('Encrypted', False),
            tags=tags
        )


def create_snapshot_info(snapshot_data: Dict[str, Any]) -> SnapshotInfo:
    """Factory function to create SnapshotInfo from AWS snapshot data."""
    return SnapshotInfo.from_aws_snapshot(snapshot_data)


def filter_old_snapshots(
    snapshots: List[SnapshotInfo], days: int = 30
) -> List[SnapshotInfo]:
    """Filter snapshots older than specified days."""
    return [snapshot for snapshot in snapshots if snapshot.age_days >= days]