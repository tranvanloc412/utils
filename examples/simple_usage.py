#!/usr/bin/env python3
"""
Simple usage examples for AWS Ops toolkit.

This script demonstrates basic usage patterns for the AWS operations toolkit.
It shows how to:
- Load configuration
- Scan servers
- Start/stop servers
- Handle errors
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from aws_ops.utils.config import ConfigManager
    from aws_ops.core.processors.zone_processor import ZoneProcessor
    from aws_ops.jobs.scan_servers import ScanServersJob
    from aws_ops.jobs.start_servers import StartServersJob
    from aws_ops.jobs.stop_servers import StopServersJob
    from aws_ops.utils.logger import setup_logger
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure the aws_ops package is properly installed")
    sys.exit(1)

# Setup logger
logger = setup_logger(__name__, "simple_usage.log")


def demonstrate_configuration():
    """Show how to load and use configuration."""
    logger.info("=== Configuration Example ===")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.config
        
        # Access configuration values
        aws_region = config.get('aws.region', 'ap-southeast-2')
        viewer_role = config.get('aws.viewer_role', 'ViewerRole')
        logger.info(f"AWS Region: {aws_region}")
        logger.info(f"Viewer Role: {viewer_role}")
        logger.info(f"MFA Required: {config.get('security.require_mfa', False)}")
        
        return config_manager
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return None








def demonstrate_error_handling():
    """Show error handling patterns."""
    logger.info("\n=== Error Handling Example ===")
    
    try:
        # Test configuration loading
        config_manager = ConfigManager()
        config = config_manager.config
        
        # Validate required settings
        required_settings = [
            'aws.region',
            'aws.viewer_role',
            'zones'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not config.get(setting):
                missing_settings.append(setting)
        
        if missing_settings:
            logger.warning(f"Missing required settings: {missing_settings}")
            return False
        
        logger.info("Configuration validation passed")
        return True
        
    except FileNotFoundError:
        logger.error("Configuration file not found")
        return False
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return False


def main():
    """Run all examples"""
    logger.info("AWS Ops - Simple Usage Examples")
    logger.info("=" * 40)
    
    # Run examples
    config_manager = demonstrate_configuration()
    
    # Only run other examples if configuration is valid
    if config_manager and demonstrate_error_handling():
        demonstrate_scan_servers(config_manager)
        demonstrate_server_management(config_manager)
    else:
        logger.warning("\nSkipping other examples due to configuration issues")
        logger.warning("Please check your configuration file and AWS credentials")
    
    logger.info("\n=== Examples Complete ===")


if __name__ == '__main__':
    main()