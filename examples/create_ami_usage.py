#!/usr/bin/env python3
"""
Example usage of CreateAMIJob

This example demonstrates how to use the simplified CreateAMIJob class to create AMIs
from EC2 instances by server name with no-reboot option.
"""

from aws_ops.jobs import CreateAMIJob
from aws_ops.utils import ConfigManager


def example_create_ami_by_server_name():
    """
    Example: Create AMI from instances matching a server name pattern
    """
    print("=== Creating AMI from Server Name Pattern ===")
    
    job = CreateAMIJob()
    
    zone_info = {
        "account_id": "123456789012",
        "name": "prod-zone",
        "environment": "prod"
    }
    
    # Execute with server name pattern
    result = job.execute(
        zone_info=zone_info,
        server_name="web-server",  # Will match instances with names containing "web-server"
        no_reboot=True,            # Don't reboot the instance
        managed_by="CMS"          # Only CMS-managed instances
    )
    
    print(f"Result: {result}")
    return result


def example_create_ami_all_servers():
    """
    Example: Create AMI from all servers matching a name pattern
    """
    print("\n=== Creating AMI from All Servers ===")
    
    job = CreateAMIJob()
    
    zone_info = {
        "account_id": "123456789012",
        "name": "nonprod-zone",
        "environment": "nonprod"
    }
    
    # Execute with server name pattern for ALL servers
    result = job.execute(
        zone_info=zone_info,
        server_name="app-server",   # Will match instances with names containing "app-server"
        no_reboot=True,            # Don't reboot the instance
        managed_by="ALL"           # Include all servers, not just CMS-managed
    )
    
    print(f"Result: {result}")
    return result


def example_with_config_manager():
    """
    Example: Using ConfigManager to get zone information
    """
    print("\n=== Using ConfigManager for Zone Information ===")
    
    try:
        # Initialize ConfigManager
        config = ConfigManager()
        
        # Get zones from configuration
        zones = config.get_zones()
        
        if not zones:
            print("No zones found in configuration")
            return
        
        # Use the first zone for this example
        zone_info = zones[0]
        print(f"Using zone: {zone_info}")
        
        # Initialize job with config manager
        job = CreateAMIJob()
        
        # Execute AMI creation
        result = job.execute(
            zone_info=zone_info,
            server_name="app-server",
            no_reboot=True,
            managed_by="CMS"
        )
        
        print(f"Result: {result}")
        return result
        
    except Exception as e:
        print(f"Error using ConfigManager: {e}")
        return None


if __name__ == "__main__":
    print("CreateAMIJob Usage Examples")
    print("===========================\n")
    
    # Run examples
    example_create_ami_by_server_name()
    example_create_ami_all_servers()
    example_with_config_manager()
    
    print("\n=== Key Features ===")
    print("✅ Simple AMI creation by server name")
    print("✅ No-reboot option for production safety")
    print("✅ Managed_by filtering (CMS or ALL)")
    print("✅ Basic tagging with source information")
    print("✅ Error handling and logging")
    print("✅ Integration with existing EC2 utilities")