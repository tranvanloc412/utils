"""Base job class for AWS operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseJob(ABC):
    """Base class for all AWS operations jobs."""

    def __init__(self, config_manager):
        """Initialize the job with configuration."""
        self.config = config_manager

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the job with given parameters."""
        pass
