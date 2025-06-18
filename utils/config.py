#!/usr/bin/env python3
"""
utils/config.py

Configuration management utilities for loading and accessing settings.
Loads configuration from config/settings.yaml file.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "configs" / "settings.yaml"


def load_yaml(
    file_path: Path, default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Load a YAML file safely with error handling.
    """
    if default is None:
        default = {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or default
    except FileNotFoundError:
        logger.warning(f"Config file not found: {file_path}")
        return default
    except yaml.YAMLError as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Unexpected error loading {file_path}: {e}")
        return default


def load_settings(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load application settings from config/settings.yaml.
    """
    configs = load_yaml(CONFIG_FILE)

    logger.info(f"Loaded configuration from {CONFIG_FILE}")

    return configs


def get_aws_config() -> Dict[str, Any]:
    """Get AWS-specific configuration."""
    settings = load_settings()
    return settings.get("aws", {})


def get_aws_region() -> str:
    """Get the default AWS region."""
    aws_config = get_aws_config()
    return aws_config.get("region", "ap-southeast-2")


def get_viewer_role() -> str:
    """Get the viewer role ARN."""
    aws_config = get_aws_config()
    return aws_config.get("viewer_role", "")


def get_provision_role() -> str:
    """Get the provision role name."""
    aws_config = get_aws_config()
    return aws_config.get("provision_role", "")


def get_zones_url() -> str:
    """Get the zones URL."""
    settings = load_settings()
    return settings.get("zones_url", "")
