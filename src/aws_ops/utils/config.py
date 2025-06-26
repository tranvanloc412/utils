#!/usr/bin/env python3
"""
utils/config.py

Simple configuration management utilities.
Provides centralized configuration loading.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .logger import setup_logger

logger = setup_logger(__name__, "config.log")


class ConfigManager:
    """
    Simple configuration manager.

    Features:
    - YAML configuration loading
    - Environment variable override support
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize ConfigManager.

        Args:
            config_dir: Custom config directory path (defaults to PROJECT_ROOT/configs)
        """
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.config_dir = config_dir or (self.project_root / "configs")
        self.settings_file = self.config_dir / "settings.yaml"

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a YAML file safely.
        """
        if not file_path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content or {}
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}

    def load_settings(self) -> Dict[str, Any]:
        """
        Load application settings.
        """
        return self._load_yaml_file(self.settings_file)

    def get_value(
        self, key_path: str, default: Any = None, env_var: Optional[str] = None
    ) -> Any:
        """
        Get configuration value with dot notation support and environment variable override.
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            return os.environ[env_var]

        # Navigate through nested dictionary
        settings = self.load_settings()
        keys = key_path.split(".")
        current = settings

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS-specific configuration section."""
        return self.get_value("aws", {})

    def get_aws_region(self) -> str:
        """Get AWS region with environment variable override support."""
        return self.get_value("aws.region", "ap-southeast-2", env_var="AWS_REGION")

    def get_viewer_role(self) -> str:
        """Get viewer role ARN."""
        return self.get_value("aws.viewer_role", "", env_var="AWS_VIEWER_ROLE")

    def get_provision_role(self) -> str:
        """Get provision role name."""
        return self.get_value("aws.provision_role", "", env_var="AWS_PROVISION_ROLE")

    def get_zones_url(self) -> str:
        """Get zones URL."""
        return self.get_value("zones_url", "", env_var="ZONES_URL")

    def get_test_account_id(self) -> str:
        """Get test account ID."""
        return self.get_value("aws.test_account.id", "", env_var="TEST_ACCOUNT_ID")

    def get_test_account_name(self) -> str:
        """Get test account name."""
        return self.get_value("aws.test_account.name", "", env_var="TEST_ACCOUNT_NAME")


# Backward compatibility functions
_default_config = None


def _get_default_config() -> ConfigManager:
    """Get or create default config manager instance."""
    global _default_config
    if _default_config is None:
        _default_config = ConfigManager()
    return _default_config


def get_zones_url() -> str:
    """Get zones URL from configuration."""
    return _get_default_config().get_zones_url()


def get_aws_region() -> str:
    """Get AWS region from configuration."""
    return _get_default_config().get_aws_region()


def get_viewer_role() -> str:
    """Get viewer role from configuration."""
    return _get_default_config().get_viewer_role()


def get_provision_role() -> str:
    """Get provision role from configuration."""
    return _get_default_config().get_provision_role()


def get_test_account_id() -> str:
    """Get test account ID from configuration."""
    return _get_default_config().get_test_account_id()


def get_test_account_name() -> str:
    """Get test account name from configuration."""
    return _get_default_config().get_test_account_name()
