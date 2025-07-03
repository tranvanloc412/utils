"""Core AWS Operations Module - Simplified for testing."""

from .aws import EC2Manager, create_ec2_manager
from .models import (
    ServerInfo,
    SnapshotInfo,
    AMIInfo,
    TagInfo,
    InstanceState,
    Platform,
    SnapshotState,
    AMIState,
)
from .processors import CSVReportGenerator, ZoneProcessor, ProcessingResult

__all__ = [
    # AWS Managers
    "EC2Manager",
    "create_ec2_manager",
    # Models
    "ServerInfo",
    "SnapshotInfo",
    "AMIInfo",
    "TagInfo",
    # Enums
    "InstanceState",
    "Platform",
    "SnapshotState",
    "AMIState",
    # Processors
    "CSVReportGenerator",
    "ZoneProcessor",
    "ProcessingResult",
    
    # Constants
    "SELF_MANAGED",
    "CMS_MANAGED",
    "MANAGED_BY_KEY",
    "REPORT_TIMESTAMP_FORMAT",
    "SCAN_TIME_FORMAT",
]