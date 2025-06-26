#!/usr/bin/env python3
"""Start/Stop EC2 Servers

Starts or stops EC2 servers across AWS landing zones with flexible filtering options.
Supports starting/stopping specific servers by name or all servers in a landing zone.
"""

from typing import Dict, List, Any, Optional
from aws_ops.core.processors.zone_processor import ZoneProcessor
from aws_ops.utils.logger import setup_logger
from aws_ops.core.aws.ec2 import create_ec2_manager
from aws_ops.core.models.server import create_server_info
from aws_ops.jobs.base import BaseJob

logger = setup_logger(__name__, "start_servers.log")


def manage_ec2_servers(session, zone_name: str, account_id: str, **kwargs) -> List[Dict[str, Any]]:
    """Start or stop EC2 servers with flexible filtering options."""
    region = kwargs.get("region", "ap-southeast-2")
    server_name = kwargs.get("server_name")
    action = kwargs.get("action", "start")
    process_all = kwargs.get("process_all", False)
    dry_run = kwargs.get("dry_run", False)
    
    try:
        ec2_manager = create_ec2_manager(session, region)
        
        # Build filters
        target_state = "stopped" if action == "start" else "running"
        filters = [{"Name": "instance-state-name", "Values": [target_state]}]
        
        if server_name:
            filters.append({"Name": "tag:Name", "Values": [server_name]})
        
        instances = ec2_manager.describe_instances(filters=filters)
        instances_to_process = []
        results = []
        
        for instance in instances:
            server = create_server_info(instance)
            server_dict = server.to_dict()
            
            # Simple filtering logic
            should_process = False
            if server_name:
                should_process = server_dict.get("instance_name", "").lower() == server_name.lower()
            elif process_all:
                should_process = True
            else:
                # If no specific server name and not process_all, still process all found instances
                # since they already match the state filter (running/stopped)
                should_process = True
            
            if should_process:
                instances_to_process.append(server_dict["instance_id"])
                results.append({
                    "instance_id": server_dict["instance_id"],
                    "instance_name": server_dict["instance_name"],
                    "landing_zone": zone_name,
                    "environment": server.tags.get("Environment", "N/A"),
                    "action": action,
                    "status": "pending"
                })
        
        # Execute action
        if instances_to_process:
            if not dry_run:
                try:
                    ec2_manager.manage_instances(instances_to_process, action)
                    action_past_tense = "started" if action == "start" else "stopped"
                    for result in results:
                        result["status"] = action_past_tense
                        result["response"] = "success"
                    logger.info(f"{action.capitalize()}ed {len(instances_to_process)} servers in {zone_name}")
                except Exception as e:
                    logger.error(f"Error {action}ing instances in {zone_name}: {e}")
                    for result in results:
                        result["status"] = "error"
                        result["response"] = str(e)
            else:
                logger.info(f"DRY RUN: Would {action} {len(instances_to_process)} servers in {zone_name}")
                for result in results:
                    result["status"] = "dry-run"
                    result["response"] = f"would {action}"
        else:
            logger.info(f"No {target_state} servers found to {action} in {zone_name}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing servers in {zone_name}: {e}")
        return []


class ManageServers(BaseJob):
    """Job for starting/stopping EC2 servers across AWS landing zones."""

    def execute(
        self,
        environment: Optional[str] = None,
        landing_zones: Optional[List[str]] = None,
        region: str = "ap-southeast-2",
        server_name: Optional[str] = None,
        action: str = "start",
        process_all: bool = False,
        dry_run: bool = False,
        start_all: bool = False,  # Backward compatibility
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute the server management job."""
        # Handle backward compatibility
        if start_all and not process_all:
            process_all = start_all

        # Get operation description
        if server_name:
            operation = f"{action.capitalize()} server: {server_name}"
        elif process_all:
            target_state = "stopped" if action == "start" else "running"
            operation = f"{action.capitalize()} all {target_state} servers"
        else:
            operation = f"{action.capitalize()} servers (no specific filter)"

        processor = ZoneProcessor(
            script_name="manage_ec2_servers",
            description=f"{action.capitalize()} EC2 servers across AWS landing zones",
        )

        try:
            all_results, summary = processor.process_zones_with_aggregation(
                process_function=manage_ec2_servers,
                landing_zones=landing_zones,
                environment=environment,
                session_purpose=f"ec2-server-{action}",
                region=region,
                server_name=server_name,
                action=action,
                process_all=process_all,
                dry_run=dry_run,
            )

            # Count results
            success_status = "started" if action == "start" else "stopped"
            successful_operations = len([r for r in all_results if r.get("status") == success_status])
            dry_run_count = len([r for r in all_results if r.get("status") == "dry-run"])
            error_count = len([r for r in all_results if r.get("status") == "error"])

            # Print summary
            action_label = "started" if action == "start" else "stopped"
            dry_run_label = f"Would {action} (dry-run)"
            
            processor.print_summary(
                summary,
                {
                    "Operation": operation,
                    "Region": region,
                    "Dry run": "Yes" if dry_run else "No",
                    f"Servers {action_label}": successful_operations if not dry_run else 0,
                    dry_run_label: dry_run_count if dry_run else 0,
                    "Errors": error_count,
                    "Total operations": len(all_results),
                },
            )

            return {
                "success": error_count == 0,
                "servers_processed": successful_operations,
                "servers_started": successful_operations if action == "start" else 0,
                "servers_stopped": successful_operations if action == "stop" else 0,
                "dry_run_count": dry_run_count,
                "error_count": error_count,
                "total_operations": len(all_results),
                "operation_description": operation,
                "action": action,
                "summary": summary,
                "results": all_results,
            }

        except Exception as e:
            logger.error(f"Error executing server management job: {e}")
            return {
                "success": False,
                "error": str(e),
                "servers_processed": 0,
                "servers_started": 0,
                "servers_stopped": 0,
                "dry_run_count": 0,
                "error_count": 1,
                "total_operations": 0,
                "action": action,
            }
