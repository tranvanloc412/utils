#!/usr/bin/env python3
"""
Example script demonstrating the ConfigManager class usage.

This script shows various features of the ConfigManager including:
- Basic configuration loading
- Dot notation access for nested values
- Environment variable overrides
- Multiple configuration file handling
- Error handling

To run this example:
1. Install the package in development mode: pip install -e .
2. Run: python examples/config_manager_example.py

Alternatively, run from project root: python -m examples.config_manager_example
"""

import os
from utils.config import ConfigManager, config_manager


def example_basic_usage():
    """Example 1: Basic configuration access."""
    print("=== Basic Configuration Access ===")
    
    # Using the global instance (backward compatible)
    region = config_manager.get_aws_region()
    provision_role = config_manager.get_provision_role()
    zones_url = config_manager.get_zones_url()
    
    print(f"AWS Region: {region}")
    print(f"Provision Role: {provision_role}")
    print(f"Zones URL: {zones_url}")
    
    # Get entire AWS config section
    aws_config = config_manager.get_aws_config()
    print(f"AWS Config: {aws_config}")


def example_dot_notation():
    """Example 2: Using dot notation for nested values."""
    print("\n=== Dot Notation Access ===")
    
    # Access nested configuration values
    region = config_manager.get_value('aws.region', 'default-region')
    test_account_id = config_manager.get_value('aws.test_account.id', 'no-test-account')
    custom_setting = config_manager.get_value('custom.nested.setting', 'default-value')
    
    print(f"Region (dot notation): {region}")
    print(f"Test Account ID: {test_account_id}")
    print(f"Custom Setting: {custom_setting}")


def example_environment_overrides():
    """Example 3: Environment variable overrides."""
    print("\n=== Environment Variable Overrides ===")
    
    # Set some environment variables for demonstration
    os.environ['AWS_REGION'] = 'us-west-2'
    os.environ['ZONES_URL'] = 'https://example.com/zones'
    
    # These will use environment variables if set
    region = config_manager.get_aws_region()
    zones_url = config_manager.get_zones_url()
    
    print(f"Region (with env override): {region}")
    print(f"Zones URL (with env override): {zones_url}")
    
    # Direct usage with custom env var
    custom_value = config_manager.get_value('aws.custom_setting', 'default', env_var='CUSTOM_AWS_SETTING')
    print(f"Custom setting: {custom_value}")
    
    # Clean up
    del os.environ['AWS_REGION']
    del os.environ['ZONES_URL']


def example_simple_loading():
    """Example 4: Simple configuration loading."""
    print("\n=== Simple Configuration Loading ===")
    
    # Load all settings
    settings = config_manager.load_settings()
    print(f"Loaded settings keys: {list(settings.keys())}")
    
    # Check if config file exists
    config_exists = config_manager.settings_file.exists()
    print(f"Config file exists: {config_exists}")


def example_config_paths():
    """Example 5: Configuration file paths."""
    print("\n=== Configuration File Paths ===")
    
    print(f"Config file: {config_manager.settings_file}")
    print(f"Config directory: {config_manager.config_dir}")
    print(f"Project root: {config_manager.project_root}")


def example_custom_config_manager():
    """Example 6: Creating custom ConfigManager instance."""
    print("\n=== Custom ConfigManager Instance ===")
    
    # Create a custom config manager with different config directory
    from pathlib import Path
    custom_config_dir = Path("/tmp/custom_config")
    
    # This would use a different config directory
    # custom_manager = ConfigManager(config_dir=custom_config_dir)
    # print(f"Custom config dir: {custom_manager.config_dir}")
    
    print("Custom ConfigManager can be created with different config directories")
    print("Useful for testing or multi-environment setups")


def example_multiple_loads():
    """Example 7: Multiple configuration loads."""
    print("\n=== Multiple Configuration Loads ===")
    
    # Each load reads from file (no caching)
    print("First load:")
    config1 = config_manager.load_settings()
    
    print("Second load:")
    config2 = config_manager.load_settings()
    
    print(f"Configs are identical: {config1 == config2}")
    print("Each load reads fresh from file (no caching)")


def example_backward_compatibility():
    """Example 8: Backward compatibility with old functions."""
    print("\n=== Backward Compatibility ===")
    
    # These functions still work exactly as before
    from utils.config import (
        get_aws_region, get_provision_role, get_zones_url,
        get_aws_config, load_settings
    )
    
    region = get_aws_region()
    role = get_provision_role()
    url = get_zones_url()
    aws_config = get_aws_config()
    settings = load_settings()
    
    print(f"Old function - AWS Region: {region}")
    print(f"Old function - Provision Role: {role}")
    print(f"Old function - Zones URL: {url}")
    print("All old functions work without any code changes!")


def main():
    """Run all examples."""
    print("ConfigManager Examples\n")
    
    example_basic_usage()
    example_dot_notation()
    example_environment_overrides()
    example_simple_loading()
    example_config_paths()
    example_custom_config_manager()
    example_multiple_loads()
    example_backward_compatibility()
    
    print("\n=== Summary ===")
    print("The simplified ConfigManager provides:")
    print("✓ Simple YAML configuration loading")
    print("✓ Environment variable overrides")
    print("✓ Dot notation for nested values")
    print("✓ Clean error handling")
    print("✓ 100% backward compatibility")
    print("✓ Lightweight and fast")


if __name__ == "__main__":
    main()