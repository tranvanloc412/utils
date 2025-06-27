#!/usr/bin/env python3
"""Server Models Usage Examples

This script demonstrates how to use the server data models for AWS EC2 management.
"""

import json
from datetime import datetime
from pathlib import Path

# Import server models
from aws_ops.core.models import (
    ServerInfo,
    DetailedServerInfo,
    ServerCollection,
    InstanceState,
    Platform,
    InstanceType,
    ServerTag,
    NetworkInterface,
    BlockDevice,
    create_server_info,
    create_server_collection,
)


def example_basic_server_info():
    """Example: Creating basic server information."""
    print("\n=== Basic Server Info Example ===")
    
    # Create a server info object
    server = ServerInfo(
        instance_id="i-1234567890abcdef0",
        instance_name="web-server-01",
        landing_zone="production",
        environment="prod",
        instance_type="t3.medium",
        state=InstanceState.RUNNING,
        platform=Platform.LINUX,
        platform_details="Amazon Linux 2",
        private_ip="10.0.1.100",
        public_ip="54.123.45.67",
        vpc_id="vpc-12345678",
        subnet_id="subnet-87654321",
        launch_time=datetime.now(),
        tags={
            "Name": "web-server-01",
            "Environment": "prod",
            "Team": "backend",
            "Project": "ecommerce"
        },
        security_groups=["sg-12345678", "sg-87654321"]
    )
    
    # Display server information
    print(f"Server: {server.display_name}")
    print(f"Instance ID: {server.instance_id}")
    print(f"State: {server.state.value}")
    print(f"Platform: {server.platform.value}")
    print(f"Running: {server.is_running}")
    print(f"Linux: {server.is_linux}")
    print(f"Environment: {server.environment}")
    print(f"Team: {server.get_tag('Team')}")
    print(f"Has Project tag: {server.has_tag('Project')}")
    
    return server


def example_detailed_server_info():
    """Example: Creating detailed server information."""
    print("\n=== Detailed Server Info Example ===")
    
    # Create network interfaces
    primary_interface = NetworkInterface(
        interface_id="eni-12345678",
        private_ip="10.0.1.100",
        public_ip="54.123.45.67",
        subnet_id="subnet-87654321",
        vpc_id="vpc-12345678",
        security_groups=["sg-12345678", "sg-87654321"]
    )
    
    secondary_interface = NetworkInterface(
        interface_id="eni-87654321",
        private_ip="10.0.1.101",
        subnet_id="subnet-87654321",
        vpc_id="vpc-12345678",
        security_groups=["sg-12345678"]
    )
    
    # Create block devices
    root_device = BlockDevice(
        device_name="/dev/sda1",
        volume_id="vol-12345678",
        volume_size=20,
        volume_type="gp3",
        encrypted=True,
        delete_on_termination=True
    )
    
    data_device = BlockDevice(
        device_name="/dev/sdf",
        volume_id="vol-87654321",
        volume_size=100,
        volume_type="gp3",
        encrypted=True,
        delete_on_termination=False,
        iops=3000,
        throughput=125
    )
    
    # Create detailed server info
    detailed_server = DetailedServerInfo(
        instance_id="i-1234567890abcdef0",
        instance_name="database-server-01",
        landing_zone="production",
        environment="prod",
        instance_type="r5.xlarge",
        state=InstanceState.RUNNING,
        platform=Platform.LINUX,
        platform_details="Amazon Linux 2",
        private_ip="10.0.1.100",
        public_ip="54.123.45.67",
        vpc_id="vpc-12345678",
        subnet_id="subnet-87654321",
        launch_time=datetime.now(),
        tags={
            "Name": "database-server-01",
            "Environment": "prod",
            "Role": "database",
            "Backup": "daily"
        },
        security_groups=["sg-12345678", "sg-87654321"],
        
        # Detailed information
        network_interfaces=[primary_interface, secondary_interface],
        block_devices=[root_device, data_device],
        architecture="x86_64",
        hypervisor="xen",
        virtualization_type="hvm",
        monitoring_enabled=True,
        iam_instance_profile="DatabaseInstanceProfile",
        key_name="prod-keypair",
        availability_zone="us-east-1a",
        tenancy="default"
    )
    
    # Display detailed information
    print(f"Server: {detailed_server.display_name}")
    print(f"Total Storage: {detailed_server.total_storage_gb} GB")
    print(f"Has Public IP: {detailed_server.has_public_ip}")
    print(f"All Private IPs: {detailed_server.all_private_ips}")
    print(f"All Public IPs: {detailed_server.all_public_ips}")
    print(f"Architecture: {detailed_server.architecture}")
    print(f"Monitoring: {detailed_server.monitoring_enabled}")
    print(f"Key Pair: {detailed_server.key_name}")
    print(f"AZ: {detailed_server.availability_zone}")
    
    return detailed_server


def example_server_collection():
    """Example: Working with server collections."""
    print("\n=== Server Collection Example ===")
    
    # Create multiple servers
    servers = [
        ServerInfo(
            instance_id="i-web01",
            instance_name="web-server-01",
            landing_zone="production",
            environment="prod",
            instance_type="t3.medium",
            state=InstanceState.RUNNING,
            platform=Platform.LINUX,
            platform_details="Amazon Linux 2",
            tags={"Role": "web", "Environment": "prod"}
        ),
        ServerInfo(
            instance_id="i-web02",
            instance_name="web-server-02",
            landing_zone="production",
            environment="prod",
            instance_type="t3.medium",
            state=InstanceState.STOPPED,
            platform=Platform.LINUX,
            platform_details="Amazon Linux 2",
            tags={"Role": "web", "Environment": "prod"}
        ),
        ServerInfo(
            instance_id="i-db01",
            instance_name="database-server-01",
            landing_zone="production",
            environment="prod",
            instance_type="r5.xlarge",
            state=InstanceState.RUNNING,
            platform=Platform.LINUX,
            platform_details="Amazon Linux 2",
            tags={"Role": "database", "Environment": "prod"}
        ),
        ServerInfo(
            instance_id="i-win01",
            instance_name="windows-server-01",
            landing_zone="development",
            environment="dev",
            instance_type="t3.large",
            state=InstanceState.RUNNING,
            platform=Platform.WINDOWS,
            platform_details="Windows Server 2019",
            tags={"Role": "app", "Environment": "dev"}
        )
    ]
    
    # Create collection
    collection = ServerCollection(
        servers=servers,
        metadata={
            "scan_time": datetime.now().isoformat(),
            "region": "us-east-1",
            "account_id": "123456789012"
        }
    )
    
    print(f"Total servers: {len(collection)}")
    print(f"Summary: {json.dumps(collection.summary, indent=2)}")
    
    # Filter examples
    running_servers = collection.running_servers
    print(f"\nRunning servers: {len(running_servers)}")
    for server in running_servers:
        print(f"  - {server.display_name} ({server.instance_id})")
    
    windows_servers = collection.windows_servers
    print(f"\nWindows servers: {len(windows_servers)}")
    for server in windows_servers:
        print(f"  - {server.display_name} ({server.platform.value})")
    
    web_servers = collection.filter_by_tag("Role", "web")
    print(f"\nWeb servers: {len(web_servers)}")
    for server in web_servers:
        print(f"  - {server.display_name} (Role: {server.get_tag('Role')})")
    
    prod_servers = collection.filter_by_environment("prod")
    print(f"\nProduction servers: {len(prod_servers)}")
    
    return collection


def example_aws_integration():
    """Example: Creating servers from AWS instance data."""
    print("\n=== AWS Integration Example ===")
    
    # Simulate AWS EC2 instance data
    aws_instance_data = {
        'InstanceId': 'i-0123456789abcdef0',
        'InstanceType': 't3.medium',
        'State': {'Name': 'running'},
        'Platform': 'windows',
        'PlatformDetails': 'Windows Server 2019 Base',
        'PrivateIpAddress': '10.0.1.50',
        'PublicIpAddress': '54.123.45.89',
        'VpcId': 'vpc-12345678',
        'SubnetId': 'subnet-87654321',
        'LaunchTime': '2024-01-15T10:30:00Z',
        'Tags': [
            {'Key': 'Name', 'Value': 'app-server-01'},
            {'Key': 'Environment', 'Value': 'staging'},
            {'Key': 'Team', 'Value': 'frontend'},
            {'Key': 'Project', 'Value': 'webapp'}
        ],
        'SecurityGroups': [
            {'GroupId': 'sg-12345678'},
            {'GroupId': 'sg-87654321'}
        ]
    }
    
    # Create server from AWS data
    server = create_server_info(aws_instance_data, landing_zone="staging")
    
    print(f"Created server from AWS data:")
    print(f"  Name: {server.display_name}")
    print(f"  ID: {server.instance_id}")
    print(f"  Type: {server.instance_type}")
    print(f"  State: {server.state.value}")
    print(f"  Platform: {server.platform.value}")
    print(f"  Environment: {server.environment}")
    print(f"  Team: {server.get_tag('Team')}")
    
    # Create collection from multiple AWS instances
    aws_instances = [aws_instance_data]  # In real usage, this would be a list from boto3
    collection = create_server_collection(
        aws_instances,
        landing_zone="staging",
        metadata={"source": "aws_ec2", "region": "us-east-1"}
    )
    
    print(f"\nCreated collection with {len(collection)} servers")
    
    return server, collection


def example_serialization():
    """Example: Serializing and deserializing server data."""
    print("\n=== Serialization Example ===")
    
    # Create a server
    server = ServerInfo(
        instance_id="i-serialize-test",
        instance_name="test-server",
        landing_zone="test",
        environment="test",
        instance_type="t3.micro",
        state=InstanceState.RUNNING,
        platform=Platform.LINUX,
        platform_details="Amazon Linux 2",
        tags={"Purpose": "testing"}
    )
    
    # Convert to dictionary
    server_dict = server.to_dict()
    print(f"Server as dict: {json.dumps(server_dict, indent=2, default=str)}")
    
    # Recreate from dictionary
    recreated_server = ServerInfo.from_dict(server_dict)
    print(f"\nRecreated server: {recreated_server.display_name}")
    print(f"States match: {server.state == recreated_server.state}")
    print(f"Platforms match: {server.platform == recreated_server.platform}")
    
    # Create collection and save to JSON
    collection = ServerCollection(servers=[server, recreated_server])
    
    # Save to file (commented out to avoid creating files in example)
    # output_file = Path("/tmp/servers.json")
    # collection.save_to_json(output_file)
    # print(f"\nSaved collection to {output_file}")
    
    # Load from file (commented out)
    # loaded_collection = ServerCollection.load_from_json(output_file)
    # print(f"Loaded collection with {len(loaded_collection)} servers")
    
    return server_dict


def main():
    """Run all examples."""
    print("Server Models Usage Examples")
    print("=============================")
    
    try:
        # Run examples
        basic_server = example_basic_server_info()
        detailed_server = example_detailed_server_info()
        collection = example_server_collection()
        aws_server, aws_collection = example_aws_integration()
        server_dict = example_serialization()
        
        print("\n=== All Examples Completed Successfully ===")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        raise


if __name__ == "__main__":
    main()