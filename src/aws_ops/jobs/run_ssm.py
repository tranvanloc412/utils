#!/usr/bin/env python3
"""Run SSM Command Script

Executes SSM commands on specific Windows servers across AWS landing zones.
Focused on remote command execution and management.

Usage:
    python run_ssm_command.py --instance-id i-1234567890abcdef0 --command "Get-Process"
    python run_ssm_command.py --instance-id i-1234567890abcdef0 --command "Get-Service" --zone appnonprod
    python run_ssm_command.py --instance-id i-1234567890abcdef0 --document AWS-RunPowerShellScript --parameters '{"commands":["Get-ComputerInfo"]}'
"""

import argparse
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional

from utils.session import SessionManager
from utils.config import get_aws_region, get_provision_role
from utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__, "run_ssm_command.log")


def run_ssm_command(ssm_client, instance_id, command=None, document_name="AWS-RunPowerShellScript", parameters=None, comment=None):
    """Run SSM command on a specific instance."""
    logger.info(f"Running SSM command on instance {instance_id}")
    
    # Prepare parameters
    if parameters is None:
        if command:
            parameters = {'commands': [command]}
        else:
            raise ValueError("Either 'command' or 'parameters' must be provided")
    
    if comment is None:
        comment = f"SSM command executed at {datetime.now().isoformat()}"
    
    try:
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName=document_name,
            Parameters=parameters,
            Comment=comment
        )
        
        command_id = response['Command']['CommandId']
        logger.info(f"SSM command sent. Command ID: {command_id}")
        
        return wait_for_command_completion(ssm_client, command_id, instance_id)
        
    except Exception as e:
        logger.error(f"Failed to run SSM command on {instance_id}: {e}")
        return {'Status': 'Failed', 'Error': str(e)}


def wait_for_command_completion(ssm_client, command_id, instance_id, max_wait=300):
    """Wait for SSM command completion and return results."""
    logger.info(f"Waiting for command {command_id} to complete...")
    
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
                
                result = {
                    'CommandId': command_id,
                    'InstanceId': instance_id,
                    'Status': status,
                    'ExecutionStartTime': output_response.get('ExecutionStartTime'),
                    'ExecutionEndTime': output_response.get('ExecutionEndTime'),
                    'StandardOutputContent': output_response.get('StandardOutputContent', ''),
                    'StandardErrorContent': output_response.get('StandardErrorContent', '')
                }
                
                if status == 'Success':
                    output = result['StandardOutputContent']
                    if output:
                        logger.info(f"Command output:\n{output}")
                        print(f"\nCommand Output:\n{output}")
                    else:
                        logger.info("Command completed successfully with no output")
                        print("\nCommand completed successfully with no output")
                elif status == 'Failed':
                    error = result['StandardErrorContent']
                    logger.error(f"Command failed with error:\n{error}")
                    print(f"\nCommand Error:\n{error}")
                
                return result
            
            time.sleep(5)
            wait_time += 5
            
        except ssm_client.exceptions.InvocationDoesNotExist:
            time.sleep(5)
            wait_time += 5
            continue
        except Exception as e:
            logger.error(f"Error checking command status: {e}")
            return {'Status': 'Error', 'Error': str(e)}
    
    logger.warning(f"SSM command timed out after {max_wait} seconds")
    return {'Status': 'TimedOut', 'CommandId': command_id, 'MaxWaitTime': max_wait}


def get_ssm_session(account_id, zone_name, region):
    """Get SSM session for the specified account and zone."""
    role = get_provision_role()
    sm = SessionManager()
    
    session = sm.get_session(
        account_id, zone_name, role, region, "ssm-command"
    )
    
    return session.client('ssm', region_name=region)


def main():
    parser = argparse.ArgumentParser(
        description="Run SSM commands on specific Windows servers."
    )
    parser.add_argument(
        "--instance-id",
        required=True,
        help="EC2 instance ID to run SSM command on"
    )
    parser.add_argument(
        "--command",
        help="PowerShell command to execute (for simple commands)"
    )
    parser.add_argument(
        "--document",
        default="AWS-RunPowerShellScript",
        help="SSM document name (default: AWS-RunPowerShellScript)"
    )
    parser.add_argument(
        "--parameters",
        help="JSON string of parameters for the SSM document"
    )
    parser.add_argument(
        "--comment",
        help="Comment for the SSM command execution"
    )
    parser.add_argument(
        "--account-id",
        required=True,
        help="AWS account ID where the instance is located"
    )
    parser.add_argument(
        "--zone-name",
        required=True,
        help="Landing zone name where the instance is located"
    )
    parser.add_argument(
        "--region",
        default="ap-southeast-2",
        help="AWS region (default: ap-southeast-2)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum wait time for command completion in seconds (default: 300)"
    )

    args = parser.parse_args()

    # Validate input
    if not args.command and not args.parameters:
        parser.error("Either --command or --parameters must be provided")
    
    # Parse parameters if provided
    parameters = None
    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in parameters: {e}")
            print(f"Error: Invalid JSON in parameters: {e}")
            return 1

    try:
        # Get SSM client
        ssm_client = get_ssm_session(args.account_id, args.zone_name, args.region)
        
        # Run the command
        result = run_ssm_command(
            ssm_client=ssm_client,
            instance_id=args.instance_id,
            command=args.command,
            document_name=args.document,
            parameters=parameters,
            comment=args.comment
        )
        
        # Show summary
        print(f"\nSummary:")
        print(f"  Instance ID: {args.instance_id}")
        print(f"  Command ID: {result.get('CommandId', 'N/A')}")
        print(f"  Status: {result.get('Status', 'Unknown')}")
        print(f"  Region: {args.region}")
        print(f"  Zone: {args.zone_name}")
        
        if result.get('Status') == 'Success':
            logger.info(f"SSM command completed successfully")
            return 0
        else:
            logger.error(f"SSM command failed with status: {result.get('Status')}")
            return 1
            
    except Exception as e:
        logger.error(f"Error executing SSM command: {e}")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())