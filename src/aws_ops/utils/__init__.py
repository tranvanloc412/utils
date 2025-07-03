# utils/__init__.py

from .config import ConfigManager

# Create a global config instance
_config = ConfigManager()

# Wrapper functions for backward compatibility
def get_zones_url():
    return _config.get_zones_url()

def get_aws_region():
    return _config.get_aws_region()

def get_viewer_role():
    return _config.get_viewer_role()

def get_provision_role():
    return _config.get_provision_role()

def get_test_account_id():
    return _config.get_test_account_id()

def get_test_account_name():
    return _config.get_test_account_name()
from .session import SessionManager, assume_role
from .logger import setup_logger
from .lz import (
    fetch_zones_from_url,
    extract_environment_from_zone
)
from .exceptions import CLIError, ValidationRules

__all__ = [
    "get_zones_url",
    "get_aws_region",
    "get_viewer_role",
    "get_provision_role",
    "get_test_account_id",
    "get_test_account_name",
    "SessionManager",
    "assume_role",
    "setup_logger",
    "fetch_zones_from_url",
    "extract_environment_from_zone",
    "CLIError",
    "ValidationRules",
]
