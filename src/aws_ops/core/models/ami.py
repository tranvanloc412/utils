"""AWS AMI Data Models.

Simplified data models for AWS AMI management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

class AMIState(Enum):
    """AMI states."""  # Fix docstring
    PENDING = "pending"
    AVAILABLE = "available"  # Use 'available' instead of 'completed'
    INVALID = "invalid"
    DEREGISTERED = "deregistered"
    FAILED = "failed"
    ERROR = "error"

@dataclass
class AMIInfo:
    """Simple AMI information model."""
    image_id: str
    name: str
    state: str = "available"  # Consider using AMIState enum
    creation_date: Optional[datetime] = None
    platform: str = "linux"
    tags: Dict[str, str] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.state == AMIState.AVAILABLE.value  # Use enum value

    @property
    def is_windows(self) -> bool:
        return self.platform.lower() == "windows"

    def get_tag(self, key: str, default: str = "") -> str:
        return self.tags.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'image_id': self.image_id,
            'name': self.name,
            'state': self.state,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'platform': self.platform,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AMIInfo':
        creation_date = None
        if data.get('creation_date'):
            creation_date = datetime.fromisoformat(data['creation_date'])

        return cls(
            image_id=data['image_id'],
            name=data.get('name', ''),
            state=data.get('state', 'available'),
            creation_date=creation_date,
            platform=data.get('platform', 'linux'),
            tags=data.get('tags', {})
        )

    @classmethod
    def from_aws_image(cls, image: Dict[str, Any]) -> 'AMIInfo':
        # Extract tags
        tags = {}
        for tag in image.get('Tags', []):
            if tag.get('Key'):
                tags[tag['Key']] = tag.get('Value', '')

        # Handle creation date
        creation_date = image.get('CreationDate')
        if isinstance(creation_date, str):
            creation_date = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))

        return cls(
            image_id=image['ImageId'],
            name=image.get('Name', ''),
            state=image.get('State', 'available'),
            creation_date=creation_date,
            platform=image.get('Platform', 'linux'),
            tags=tags
        )


def create_ami_info(image_data: Dict[str, Any]) -> AMIInfo:
    """Create AMIInfo from AWS image data."""
    return AMIInfo.from_aws_image(image_data)


def create_ami_list(images: List[Dict[str, Any]]) -> List[AMIInfo]:
    """Create list of AMIInfo from AWS images."""
    return [create_ami_info(image) for image in images]