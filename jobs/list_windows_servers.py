#!/usr/bin/env python3
"""List Windows Servers Script

Lists Windows servers across AWS landing zones and generates a CSV report.
Optionally copies the CSV to a remote Windows server and runs SSM commands.

Usage:
    python list_windows_servers.py                                      # All nonprod zones, scan only
    python list_windows_servers.py -l zone1 zone2                       # Specific zones, scan only
    python list_windows_servers.py --remote-host <host> --username <user> --password <pass>  # With file copy
"""

import argparse
import csv
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

from utils.lz import fetch_zones_from_url, filter_zones, get_managed_landing_zones
from utils.session_manager import SessionManager
from utils.config import get_zones_url, get_aws_region, get_provision_role
from utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__, "list_windows_servers.log")


def scan_windows_servers(ec2_client, zone_name, region):
    """Scan Windows servers in a specific zone and region."""
    try:
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'platform', 'Values': ['windows']},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
            ]
        )
        
        servers = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                server_info = format_server_info(instance, zone_name, region)
                servers.append(server_info)
        
        logger.info(f"Zone {zone_name}, Region {region}: {len(servers)} Windows servers found")
        return servers
        
    except Exception as e:
        logger.error(f"Failed to scan Windows servers in {zone_name}/{region}: {e}")
        return []


def format_server_info(instance, zone_name, region):
    """Format server info for CSV export."""
    # Get instance name from tags
    instance_name = "N/A"
    for tag in instance.get('Tags', []):
        if tag['Key'] == 'Name':
            instance_name = tag['Value']
            break
    
    return {
        'LandingZone': zone_name,
        'Region': region,
        'InstanceName': instance_name,
        'InstanceId': instance['InstanceId'],
        'InstanceType': instance['InstanceType'],
        'State': instance['State']['Name'],
        'Platform': instance.get('Platform', 'windows'),
        'PlatformDetails': instance.get('PlatformDetails', 'N/A'),
        'PrivateIpAddress': instance.get('PrivateIpAddress', 'N/A'),
        'PublicIpAddress': instance.get('PublicIpAddress', 'N/A'),
        'LaunchTime': instance.get('LaunchTime', 'N/A'),
        'VpcId': instance.get('VpcId', 'N/A'),
        'SubnetId': instance.get('SubnetId', 'N/A'),
        'SecurityGroups': ', '.join([sg['GroupName'] for sg in instance.get('SecurityGroups', [])]),
        'KeyName': instance.get('KeyName', 'N/A'),
        'ScanTime': datetime.now().isoformat()
    }


def write_csv_report(servers_data, csv_file):
    """Write server data to CSV file."""
    if not servers_data:
        logger.warning("No Windows servers to export")
        return
    
    Path(csv_file).parent.mkdir(exist_ok=True)
    
    fieldnames = [
        'LandingZone', 'Region', 'InstanceName', 'InstanceId',
        'InstanceType', 'State', 'Platform', 'PlatformDetails', 
        'PrivateIpAddress', 'PublicIpAddress', 'LaunchTime', 
        'VpcId', 'SubnetId', 'SecurityGroups', 'KeyName', 'ScanTime'
    ]
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(servers_data)
    
    logger.info(f"CSV report: {csv_file}")
    
def copy_file_to_remote(local_file, remote_host, username, password, remote_path=None):
    """Copy file to remote Windows server using scp/pscp."""
    if not remote_path:
        filename = os.path.basename(local_file)
        remote_path = f"C:\\temp\\{filename}"
    
    logger.info(f"Copying {local_file} to {remote_host}:{remote_path}")
    
    # Try pscp first, then scp with sshpass
    commands_to_try = [
        ['pscp', '-pw', password, local_file, f"{username}@{remote_host}:{remote_path}"],
        ['sshpass', '-p', password, 'scp', local_file, f"{username}@{remote_host}:{remote_path}"]
    ]
    
    for cmd in commands_to_try:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"Successfully copied file to {remote_host}")
                return remote_path
            else:
                logger.warning(f"Command failed: {' '.join(cmd)} - {result.stderr}")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Command {cmd[0]} failed: {e}")
            continue
    
    raise Exception("All file copy methods failed")


def run_ssm_command(ssm_client, instance_id, remote_file_path):
    """Run SSM command to echo the copied file contents."""
    logger.info(f"Running SSM command on instance {instance_id}")
    
    command = f"Get-Content '{remote_file_path}' | Write-Host"
    
    response = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunPowerShellScript',
        Parameters={'commands': [command]},
        Comment=f'Echo contents of {remote_file_path}'
    )
    
    command_id = response['Command']['CommandId']
    logger.info(f"SSM command sent. Command ID: {command_id}")
    
    # Wait for command completion
    max_wait = 60
    wait_time = 0
    
    while wait_time < max_wait:
        try:
            output_response = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            
            status = output_response['Status']
            if status in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
                logger.info(f"SSM command completed with status: {status}")
                if status == 'Success':
                    output = output_response.get('StandardOutputContent', '')
                    logger.info(f"Command output:\n{output}")
                return output_response
            
            time.sleep(5)
            wait_time += 5
            
        except ssm_client.exceptions.InvocationDoesNotExist:
            time.sleep(5)
            wait_time += 5
            continue
    
    logger.warning(f"SSM command timed out after {max_wait} seconds")
    return {'Status': 'TimedOut', 'CommandId': command_id}


def main():
    parser = argparse.ArgumentParser(
        description="List Windows servers for specified landing zones."
    )
    parser.add_argument(
        "--landing-zones",
        "-l",
        nargs="*",
        default=[],
        help="Landing zone names (e.g., cmsnonprod appnonprod). Leave blank for all zones in the environment.",
    )
    parser.add_argument(
        "--environment",
        "-e",
        default="nonprod",
        choices=["prod", "nonprod"],
        help="Environment suffix to filter zones if landing-zones not specified.",
    )
    parser.add_argument(
        "--remote-host",
        help="Remote Windows server hostname/IP for file copy"
    )
    parser.add_argument(
        "--username",
        help="Username for remote server"
    )
    parser.add_argument(
        "--password",
        help="Password for remote server"
    )
    parser.add_argument(
        "--instance-id",
        help="EC2 instance ID to run SSM command on"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region for SSM command"
    )

    args = parser.parse_args()

    landing_zones = args.landing_zones
    environment = args.environment

    # Generate CSV filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"results/windows_servers_{environment}_{timestamp}.csv"

    zones_url = get_zones_url()
    region = get_aws_region()
    role = get_provision_role()
    sm = SessionManager()

    all_servers_data = []
    total_servers = 0
    processed_zones = 0

    # Get zones to process
    zones = fetch_zones_from_url(zones_url)
    if landing_zones:
        zones = [ln for ln in zones if any(ln.split()[1] == lz for lz in landing_zones)]
    else:
        zones = filter_zones(zones, environment=environment)

    if not zones:
        print("No zones found matching criteria")
        return

    logger.info(f"Processing {len(zones)} zones")

    for line in zones:
        account_id, zone_name = line.split()

        try:
            session = sm.get_session(
                account_id, zone_name, role, region, "scan-windows-servers"
            )
            
            # Get all regions for this account
            ec2_client = session.client('ec2')
            regions_response = ec2_client.describe_regions()
            regions = [r['RegionName'] for r in regions_response['Regions']]
            
            for aws_region in regions:
                regional_ec2 = session.client('ec2', region_name=aws_region)
                servers = scan_windows_servers(regional_ec2, zone_name, aws_region)
                all_servers_data.extend(servers)
                total_servers += len(servers)

            processed_zones += 1

        except Exception as e:
            logger.error(f"Error processing {zone_name}: {e}")

    # Write CSV report
    write_csv_report(all_servers_data, csv_file)

    # Optional file copy
    if args.remote_host and args.username and args.password:
        try:
            remote_path = copy_file_to_remote(
                csv_file, args.remote_host, args.username, args.password
            )
            print(f"File copied to: {args.remote_host}:{remote_path}")
            
            # Optional SSM command
            if args.instance_id:
                # Get SSM client for the specified region
                ssm_session = sm.get_session(
                    account_id, zone_name, role, args.region, "ssm-command"
                )
                ssm_client = ssm_session.client('ssm', region_name=args.region)
                
                result = run_ssm_command(ssm_client, args.instance_id, remote_path)
                print(f"SSM command status: {result.get('Status', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"Error with file copy/SSM: {e}")

    # Show summary
    print(f"\nSummary:")
    print(f"  Zones processed: {processed_zones}")
    print(f"  Windows servers found: {total_servers}")
    print(f"  CSV report: {csv_file}")

    logger.info(f"Completed: {processed_zones} zones, {total_servers} Windows servers")


if __name__ == "__main__":
    # Ensure results directory exists
    os.makedirs("results", exist_ok=True)
    main()