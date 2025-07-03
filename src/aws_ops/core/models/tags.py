"""Simple data models for AWS resource tag management."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass
class TagInfo:
    """Simple AWS resource tag information model."""
    name: str
    environment: str = "dev"
    cost_centre: str = ""
    application_id: str = ""
    custom_tags: Dict[str, str] = field(default_factory=dict)

    @property
    def all_tags(self) -> Dict[str, str]:
        """Get all tags combined."""
        tags = {
            "Name": self.name,
            "Environment": self.environment,
        }
        if self.cost_centre:
            tags["CostCentre"] = self.cost_centre
        if self.application_id:
            tags["ApplicationID"] = self.application_id
        tags.update(self.custom_tags)
        return tags

    @classmethod
    def from_aws_tags(cls, tags: Dict[str, str]) -> "TagInfo":
        """Create from AWS tags dictionary."""
        # Extract known tags
        known_tags = {"Name", "Environment", "CostCentre", "ApplicationID"}
        custom_tags = {
            k: v for k, v in tags.items() if k not in known_tags
        }
        
        return cls(
            name=tags.get("Name", ""),
            environment=tags.get("Environment", "dev"),
            cost_centre=tags.get("CostCentre", ""),
            application_id=tags.get("ApplicationID", ""),
            custom_tags=custom_tags
        )
