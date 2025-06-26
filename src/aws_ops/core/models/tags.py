"""AWS Resource Tag Models.

Simplified data models for AWS resource tag management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any


@dataclass
class TagInfo:
    """AWS resource tag information model."""

    # Mandatory tags
    name: str
    environment: str
    cost_centre: str
    application_id: str

    # Optional tags
    power_mgt: Optional[str] = None
    support_group: Optional[str] = None
    app_category: Optional[str] = None

    # Additional custom tags
    custom_tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate mandatory tags are not empty."""
        if not self.name.strip():
            raise ValueError("Name tag cannot be empty")
        if not self.environment.strip():
            raise ValueError("Environment tag cannot be empty")
        if not self.cost_centre.strip():
            raise ValueError("CostCentre tag cannot be empty")
        if not self.application_id.strip():
            raise ValueError("ApplicationID tag cannot be empty")

    @property
    def mandatory_tags(self) -> Dict[str, str]:
        """Get mandatory tags as dictionary."""
        return {
            "Name": self.name,
            "Environment": self.environment,
            "CostCentre": self.cost_centre,
            "ApplicationID": self.application_id,
        }

    @property
    def optional_tags(self) -> Dict[str, str]:
        """Get optional tags as dictionary (excluding None values)."""
        tags = {}
        if self.power_mgt:
            tags["PowerMgt"] = self.power_mgt
        if self.support_group:
            tags["SupportGroup"] = self.support_group
        if self.app_category:
            tags["AppCategory"] = self.app_category
        return tags

    @property
    def all_tags(self) -> Dict[str, str]:
        """Get all tags combined."""
        tags = self.mandatory_tags.copy()
        tags.update(self.optional_tags)
        tags.update(self.custom_tags)
        return tags

    def has_mandatory_tags(self) -> bool:
        """Check if all mandatory tags are present and non-empty."""
        return all(
            [
                self.name.strip(),
                self.environment.strip(),
                self.cost_centre.strip(),
                self.application_id.strip(),
            ]
        )

    def get_missing_mandatory_tags(self) -> List[str]:
        """Get list of missing mandatory tags."""
        missing = []
        if not self.name.strip():
            missing.append("Name")
        if not self.environment.strip():
            missing.append("Environment")
        if not self.cost_centre.strip():
            missing.append("CostCentre")
        if not self.application_id.strip():
            missing.append("ApplicationID")
        return missing

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "environment": self.environment,
            "cost_centre": self.cost_centre,
            "application_id": self.application_id,
            "power_mgt": self.power_mgt,
            "support_group": self.support_group,
            "app_category": self.app_category,
            "custom_tags": self.custom_tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagInfo":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            environment=data.get("environment", ""),
            cost_centre=data.get("cost_centre", ""),
            application_id=data.get("application_id", ""),
            power_mgt=data.get("power_mgt"),
            support_group=data.get("support_group"),
            app_category=data.get("app_category"),
            custom_tags=data.get("custom_tags", {}),
        )

    @classmethod
    def from_aws_tags(cls, tags: List[Dict[str, str]]) -> "TagInfo":
        """Create from AWS tag format."""
        tag_dict = {}
        for tag in tags:
            key = tag.get("Key", "")
            value = tag.get("Value", "")
            if key:
                tag_dict[key] = value

        # Extract known tags
        name = tag_dict.pop("Name", "")
        environment = tag_dict.pop("Environment", "")
        cost_centre = tag_dict.pop("CostCentre", "")
        application_id = tag_dict.pop("ApplicationID", "")
        power_mgt = tag_dict.pop("PowerMgt", None)
        support_group = tag_dict.pop("SupportGroup", None)
        app_category = tag_dict.pop("AppCategory", None)

        # Remaining tags are custom
        custom_tags = tag_dict

        return cls(
            name=name,
            environment=environment,
            cost_centre=cost_centre,
            application_id=application_id,
            power_mgt=power_mgt,
            support_group=support_group,
            app_category=app_category,
            custom_tags=custom_tags,
        )


def create_tag_info(tag_data: Dict[str, Any]) -> TagInfo:
    """Create TagInfo from tag data."""
    return TagInfo.from_dict(tag_data)


def validate_mandatory_tags(tags: Dict[str, str]) -> List[str]:
    """Validate mandatory tags and return missing ones."""
    mandatory = {"Name", "Environment", "CostCentre", "ApplicationID"}
    present = set(tags.keys())
    missing = mandatory - present

    # Also check for empty values
    empty_values = [key for key in mandatory & present if not tags[key].strip()]

    return list(missing) + empty_values


def get_tag_template() -> Dict[str, str]:
    """Get a template for all possible tags."""
    return {
        "Name": "",
        "Environment": "",
        "CostCentre": "",
        "ApplicationID": "",
        "PowerMgt": "",
        "SupportGroup": "",
        "AppCategory": "",
    }
