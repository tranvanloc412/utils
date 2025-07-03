"""Simple data models for AWS resources."""

# Server models
from .server import (
    InstanceState,
    Platform,
    ServerInfo,
)

# Snapshot models
from .snapshot import (
    SnapshotState,
    SnapshotInfo,
)

# AMI models
from .ami import (
    AMIState,
    AMIInfo,
)

# Tag models
from .tags import (
    TagInfo,
)

__all__ = [
    # Server models
    "InstanceState",
    "Platform",
    "ServerInfo",
    # Snapshot models
    "SnapshotState",
    "SnapshotInfo",
    # AMI models
    "AMIState",
    "AMIInfo",
    # Tag models
    "TagInfo",
]