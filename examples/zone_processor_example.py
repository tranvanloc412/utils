#!/usr/bin/env python3
"""
Example: Using ZoneProcessor Utility

This example demonstrates how to refactor existing scripts to use the ZoneProcessor utility.
It shows both simple processing and aggregated processing patterns.
"""

import csv
from pathlib import Path
from typing import List, Dict, Any

from utils.zone_processor import ZoneProcessor


def scan_ec2_instances(session, zone_name: str, account_id: str, **kwargs) -> List[Dict[str, Any]]:
    """
    Example function: Scan EC2 instances in a zone.
    
    This function demonstrates the expected signature for zone processing functions.
    
    Args:
        session: AWS session for the zone
        zone_name: Name of the landing zone
        account_id: AWS account ID
        **kwargs: Additional parameters (e.g., instance_types, states)
        
    Returns:
        List of instance information dictionaries
    """
    ec2 = session.client('ec2')
    
    # Get filters from kwargs
    instance_types = kwargs.get('instance_types', [])
    states = kwargs.get('states', ['running', 'stopped'])
    
    # Build filters
    filters = [{'Name': 'instance-state-name', 'Values': states}]
    if instance_types:
        filters.append({'Name': 'instance-type', 'Values': instance_types})
    
    # Scan instances
    response = ec2.describe_instances(Filters=filters)
    
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_info = {
                'LandingZone': zone_name,
                'AccountId': account_id,
                'InstanceId': instance['InstanceId'],
                'InstanceType': instance['InstanceType'],
                'State': instance['State']['Name'],
                'Platform': instance.get('Platform', 'linux'),
                'LaunchTime': instance['LaunchTime'].isoformat()
            }
            instances.append(instance_info)
    
    return instances


def count_resources(session, zone_name: str, account_id: str, **kwargs) -> Dict[str, Any]:
    """
    Example function: Count various AWS resources in a zone.
    
    Returns a single summary dictionary per zone.
    """
    ec2 = session.client('ec2')
    s3 = session.client('s3')
    
    # Count EC2 instances
    instances_response = ec2.describe_instances()
    instance_count = sum(len(r['Instances']) for r in instances_response['Reservations'])
    
    # Count S3 buckets
    buckets_response = s3.list_buckets()
    bucket_count = len(buckets_response['Buckets'])
    
    # Count EBS volumes
    volumes_response = ec2.describe_volumes()
    volume_count = len(volumes_response['Volumes'])
    
    return {
        'LandingZone': zone_name,
        'AccountId': account_id,
        'EC2Instances': instance_count,
        'S3Buckets': bucket_count,
        'EBSVolumes': volume_count
    }


def add_custom_arguments(parser):
    """
    Add script-specific arguments to the parser.
    """
    parser.add_argument(
        '--instance-types',
        nargs='*',
        default=[],
        help='Filter by instance types (e.g., t3.micro t3.small)'
    )
    parser.add_argument(
        '--states',
        nargs='*',
        default=['running', 'stopped'],
        help='Filter by instance states'
    )
    parser.add_argument(
        '--output-file',
        default='ec2_instances.csv',
        help='Output CSV file name'
    )
    return parser


def write_csv_report(data: List[Dict[str, Any]], filename: str):
    """
    Write data to CSV file.
    """
    if not data:
        print(f"No data to write to {filename}")
        return
    
    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Report written to {output_path} ({len(data)} records)")


def main():
    """
    Example 1: Aggregated Processing (collecting items from all zones)
    """
    print("=== Example 1: Scanning EC2 Instances (Aggregated) ===")
    
    # Initialize processor
    processor = ZoneProcessor(
        script_name="scan_ec2_example",
        description="Scan EC2 instances across landing zones"
    )
    
    # Create parser with custom arguments
    parser = processor.create_standard_parser(add_custom_arguments)
    args = parser.parse_args()
    
    # Process zones with aggregation (combines results from all zones)
    all_instances, summary = processor.process_zones_with_aggregation(
        process_function=scan_ec2_instances,
        landing_zones=args.landing_zones,
        environment=args.environment,
        session_purpose="ec2-scanning",
        # Pass additional parameters to the processing function
        instance_types=args.instance_types,
        states=args.states
    )
    
    # Write results to CSV
    if all_instances:
        write_csv_report(all_instances, args.output_file)
    
    # Print summary
    processor.print_summary(summary, {
        'Output file': args.output_file if all_instances else 'None (no data)'
    })


def example_simple_processing():
    """
    Example 2: Simple Processing (one result per zone)
    """
    print("\n=== Example 2: Resource Counting (Simple) ===")
    
    processor = ZoneProcessor(
        script_name="count_resources_example",
        description="Count AWS resources per landing zone"
    )
    
    # Simple processing - gets one result per zone
    result = processor.process_zones(
        process_function=count_resources,
        landing_zones=[],  # All zones
        environment="nonprod",
        session_purpose="resource-counting"
    )
    
    # Write results to CSV
    if result['results']:
        write_csv_report(result['results'], 'resource_counts.csv')
    
    # Print summary
    processor.print_summary({
        'processed_zones': result['processed_zones'],
        'total_zones': result['total_zones'],
        'total_items': len(result['results']),
        'errors': result['errors']
    }, {
        'Output file': 'resource_counts.csv' if result['results'] else 'None (no data)'
    })


if __name__ == "__main__":
    # Run the main example
    main()
    
    # Uncomment to run the simple processing example
    # example_simple_processing()