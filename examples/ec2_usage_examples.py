#!/usr/bin/env python3
"""EC2Manager Usage Examples

This file demonstrates how to use the EC2Manager class for common AWS EC2 operations.
"""

import boto3
from datetime import datetime
from aws_ops.core.aws import EC2Manager, create_ec2_manager


def example_basic_usage():
    """Basic EC2Manager usage example."""
    print("=== Basic EC2Manager Usage ===")
    
    # Create a session (you would typically use your actual AWS credentials)
    session = boto3.Session()
    
    # Create EC2Manager instance
    ec2_manager = create_ec2_manager(session, region='ap-southeast-2')
    
    # Get all Windows instances
    print("\n1. Getting Windows instances...")
    windows_instances = ec2_manager.get_windows_instances()
    print(f"Found {len(windows_instances)} Windows instances")
    
    # Get all running instances
    print("\n2. Getting running instances...")
    running_instances = ec2_manager.get_running_instances()
    print(f"Found {len(running_instances)} running instances")
    
    # Format instance information for reporting
    if running_instances:
        print("\n3. Formatted instance information:")
        for instance in running_instances[:3]:  # Show first 3
            formatted = ec2_manager.format_instance_info(instance, 'example-zone')
            print(f"  - {formatted['InstanceName']} ({formatted['InstanceId']}) - {formatted['State']}")


def example_snapshot_management():
    """Snapshot management example."""
    print("\n=== Snapshot Management ===")
    
    session = boto3.Session()
    ec2_manager = create_ec2_manager(session)
    
    # Get all snapshots
    print("\n1. Getting all snapshots...")
    snapshots = ec2_manager.describe_snapshots()
    print(f"Found {len(snapshots)} snapshots")
    
    # Get old snapshots (older than 30 days)
    print("\n2. Getting old snapshots...")
    old_snapshots = ec2_manager.get_old_snapshots(days_old=30)
    print(f"Found {len(old_snapshots)} snapshots older than 30 days")
    
    # Format snapshot information
    if old_snapshots:
        print("\n3. Old snapshots details:")
        for snapshot in old_snapshots[:3]:  # Show first 3
            formatted = ec2_manager.format_snapshot_info(
                snapshot, 
                zone_name='example-zone',
                account_id='123456789012'
            )
            print(f"  - {formatted['SnapshotId']} - {formatted['StartTime']} - {formatted['VolumeSize']}GB")


def example_volume_management():
    """Volume management example."""
    print("\n=== Volume Management ===")
    
    session = boto3.Session()
    ec2_manager = create_ec2_manager(session)
    
    # Get all volumes
    print("\n1. Getting all volumes...")
    volumes = ec2_manager.describe_volumes()
    print(f"Found {len(volumes)} volumes")
    
    # Get unattached volumes
    print("\n2. Getting unattached volumes...")
    unattached_volumes = ec2_manager.get_unattached_volumes()
    print(f"Found {len(unattached_volumes)} unattached volumes")
    
    if unattached_volumes:
        print("\n3. Unattached volumes details:")
        for volume in unattached_volumes[:3]:  # Show first 3
            print(f"  - {volume['VolumeId']} - {volume['Size']}GB - {volume['State']}")


def example_instance_operations():
    """Instance operations example (start/stop/reboot)."""
    print("\n=== Instance Operations ===")
    
    session = boto3.Session()
    ec2_manager = create_ec2_manager(session)
    
    # Find instance by name (example)
    print("\n1. Finding instance by name...")
    instance = ec2_manager.get_instance_by_name('example-server')
    
    if instance:
        instance_id = instance['InstanceId']
        print(f"Found instance: {instance_id}")
        
        # Get instance tags
        print("\n2. Getting instance tags...")
        tags = ec2_manager.get_instance_tags(instance_id)
        print(f"Tags: {tags}")
        
        # Note: Uncomment these operations only if you want to actually manage instances
        # print("\n3. Instance operations (commented out for safety):")
        # print("   # Start instance:")
        # # response = ec2_manager.start_instances([instance_id])
        # print("   # Stop instance:")
        # # response = ec2_manager.stop_instances([instance_id])
        # print("   # Reboot instance:")
        # # response = ec2_manager.reboot_instances([instance_id])
    else:
        print("No instance found with name 'example-server'")


def example_custom_filtering():
    """Custom filtering example."""
    print("\n=== Custom Filtering ===")
    
    session = boto3.Session()
    ec2_manager = create_ec2_manager(session)
    
    # Custom filters for specific instance types
    print("\n1. Getting t3.micro instances...")
    filters = [{'Name': 'instance-type', 'Values': ['t3.micro']}]
    micro_instances = ec2_manager.describe_instances(filters=filters)
    print(f"Found {len(micro_instances)} t3.micro instances")
    
    # Custom filters for specific VPC
    print("\n2. Getting instances in specific VPC...")
    filters = [{'Name': 'vpc-id', 'Values': ['vpc-12345678']}]  # Replace with actual VPC ID
    vpc_instances = ec2_manager.describe_instances(filters=filters)
    print(f"Found {len(vpc_instances)} instances in specified VPC")
    
    # Custom filters for instances with specific tags
    print("\n3. Getting instances with Environment=prod tag...")
    filters = [{'Name': 'tag:Environment', 'Values': ['prod']}]
    prod_instances = ec2_manager.describe_instances(filters=filters)
    print(f"Found {len(prod_instances)} production instances")


def example_error_handling():
    """Error handling example."""
    print("\n=== Error Handling ===")
    
    try:
        # Create session with invalid credentials (for demonstration)
        session = boto3.Session(
            aws_access_key_id='invalid',
            aws_secret_access_key='invalid',
            region_name='ap-southeast-2'
        )
        
        ec2_manager = create_ec2_manager(session)
        
        # This will fail gracefully and return empty list
        print("\n1. Attempting operation with invalid credentials...")
        instances = ec2_manager.describe_instances()
        print(f"Result: {len(instances)} instances (should be 0 due to error)")
        
    except Exception as e:
        print(f"Caught exception: {e}")
    
    print("\nEC2Manager handles AWS errors gracefully and logs them.")


def main():
    """Run all examples."""
    print("EC2Manager Usage Examples")
    print("=" * 50)
    
    try:
        example_basic_usage()
        example_snapshot_management()
        example_volume_management()
        example_instance_operations()
        example_custom_filtering()
        example_error_handling()
        
    except Exception as e:
        print(f"\nExample execution failed: {e}")
        print("Note: These examples require valid AWS credentials and permissions.")
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use EC2Manager in your own code:")
    print("1. Import: from aws_ops.core.aws import EC2Manager, create_ec2_manager")
    print("2. Create: ec2_manager = create_ec2_manager(session, region)")
    print("3. Use: instances = ec2_manager.get_windows_instances()")


if __name__ == '__main__':
    main()