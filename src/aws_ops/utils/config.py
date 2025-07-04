#!/usr/bin/env python3
"""
utils/config.py

Simple configuration management utilities.
Provides centralized configuration loading.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from aws_ops.utils.logger import setup_logger

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

        # Try both .yml and .yaml extensions
        yml_file = self.config_dir / "settings.yml"
        yaml_file = self.config_dir / "settings.yaml"

        if yml_file.exists():
            self.settings_file = yml_file
        elif yaml_file.exists():
            self.settings_file = yaml_file
        else:
            self.settings_file = yaml_file  # Default to .yaml for error messages

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
        return self.get_value("aws.region", "ap-southeast-2")

    def get_viewer_role(self) -> str:
        """Get viewer role ARN."""
        return self.get_value("aws.roles.viewer", "")

    def get_provision_role(self) -> str:
        """Get provision role name."""
        return self.get_value("aws.roles.provision", "")

    def get_zones_url(self) -> str:
        """Get zones URL."""
        return self.get_value("services.zones_url", "")

    def get_test_account_id(self) -> str:
        """Get test account ID."""
        return self.get_value("aws.test_account.id", "")

    def get_test_account_name(self) -> str:
        """Get test account name."""
        return self.get_value("aws.test_account.name", "")

    def get_test_account(self) -> Dict[str, str]:
        """Get test account configuration."""
        return {"id": self.get_test_account_id(), "name": self.get_test_account_name()}

    def get_asg_stateless_config(self) -> list:
        """Get asg_stateless configuration."""
        return self.get_value("asg_stateless", [])

    def get_ami_url(self, ami_key: str) -> str:
        """Get AMI URL by key (e.g., 'rhel9_ami', 'rhel8_ami')."""
        return self.get_value(f"ami_sources.{ami_key}", "")

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration section."""
        return self.get_value(
            "logging",
            {"level": "INFO", "console": True, "file": True, "path": "logs/aws-ops"},
        )

    def get_logging_level(self) -> str:
        """Get logging level."""
        return self.get_value("logging.level", "INFO", env_var="LOG_LEVEL")

    def get_logging_path(self) -> str:
        """Get logging file path."""
        return self.get_value("logging.path", "logs/aws-ops", env_var="LOG_PATH")

    def get_services_config(self) -> Dict[str, Any]:
        """Get external services configuration section."""
        return self.get_value("services", {})

    def get_ami_sources_config(self) -> Dict[str, Any]:
        """Get AMI sources configuration section."""
        return self.get_value("ami_sources", {})

    def get_report_config(self) -> Dict[str, Any]:
        """Get report configuration section."""
        return self.get_value("report", {"path": "results"})

    def get_report_path(self) -> str:
        """Get report output path."""
        return self.get_value("report.path", "results")

    def get_account_mapping(self) -> Dict[str, str]:
        """Get account mapping configuration."""
        return self.get_value("account_mapping", {})

    def get_zones(self, zone_names: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Get zones with individual fallback logic.
        
        Args:
            zone_names: Optional list of specific zone names to resolve.
                       If None, returns all zones from account_mapping or zones_url.
        
        Returns:
            List of zone dictionaries with fallback resolution
        """
        # If specific zones requested, use individual fallback logic
        if zone_names:
            from aws_ops.core.processors.zone_processor import ZoneProcessor
            processor = ZoneProcessor(name="config_zone_resolver")
            return processor.resolve_zones(zone_names)
        
        # Legacy behavior: get all zones from account_mapping first, then fall back to zones_url
        account_mapping = self.get_account_mapping()
        
        if account_mapping:
            logger.info(f"Using zones from account_mapping in settings.yml: {len(account_mapping)} zones")
            zones = []
            for zone_name, account_id in account_mapping.items():
                zones.append({
                    'account_id': str(account_id),  # Ensure account_id is always a string
                    'name': zone_name,
                    'environment': zone_name,
                    'source': 'local_config'
                })
            return zones
        
        # Priority 2: Fall back to fetching from external zones_url
        logger.info("No account_mapping found in settings.yml, falling back to zones_url")
        from .lz import fetch_zones_from_url
        
        zones_url = self.get_zones_url()
        if not zones_url:
            logger.warning("No zones_url configured and no account_mapping available")
            return []
        
        try:
            zone_lines = fetch_zones_from_url(zones_url)
            zones = []
            for line in zone_lines:
                parts = line.split()
                if len(parts) >= 2:
                    account_id = parts[0]
                    zone_name = parts[1]
                    zones.append({
                        'account_id': account_id,
                        'name': zone_name,
                        'environment': zone_name,
                        'source': 'external_url'
                    })
            logger.info(f"Fetched zones from external URL: {len(zones)} zones")
            return zones
        except Exception as e:
            logger.error(f"Failed to fetch zones from {zones_url}: {e}")
            return []

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration as a cached property."""
        if not hasattr(self, "_cached_config"):
            self._cached_config = self.load_settings()
        return self._cached_config

    def reload_config(self) -> None:
        """Force reload of configuration from file."""
        if hasattr(self, "_cached_config"):
            delattr(self, "_cached_config")
