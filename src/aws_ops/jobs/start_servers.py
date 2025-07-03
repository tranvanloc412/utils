#!/usr/bin/env python3

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .base import BaseJob
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY
from aws_ops.utils.ec2_utils import find_instances_by_state, get_instance_name


@dataclass
class StartMetrics:
    """Metrics for start server operation tracking."""

    total_instances_found: int = 0
    instances_started: int = 0
    operation_duration: float = 0.0
    dry_run_mode: bool = False


class StartServersJob(BaseJob):
    """Starting EC2 instances Job:

    Features:
    - Filtering with managed_by=CMS/ all support
    - Dry-run capabilities for safe operations
    """

    def __init__(self, config_manager=None):
        super().__init__(
            config_manager=config_manager,
            job_name="start_servers",
            default_role="provision",
        )

    def execute(self, zone_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Start EC2 instances in the specified zone with comprehensive monitoring.
        """
        operation_start = time.time()
        metrics = StartMetrics()

        try:
            # Get parameters with enhanced validation
            server_name = kwargs.get("server_name")
            start_all = kwargs.get("start_all", False)
            dry_run = kwargs.get("dry_run", False)
            managed_by = kwargs.get("managed_by")

            metrics.dry_run_mode = dry_run

            # Enhanced logging for operation start
            zone_name = zone_info.get("name", "unknown")
            account_id = zone_info.get("account_id", "unknown")

            self.logger.info(
                f"[{self.correlation_id}] Starting EC2 server start operation for zone: {zone_name} "
                f"(Account: {account_id}, Managed By: {managed_by or 'CMS'}, Dry Run: {dry_run})"
            )

            # Create EC2 client
            session = self.create_aws_session(zone_info)
            ec2 = session.client("ec2")

            # Find instances to start with metrics tracking
            instances = self._find_instances(ec2, server_name, start_all, managed_by)
            metrics.total_instances_found = len(instances)

            self.logger.info(
                f"[{self.correlation_id}] Found {len(instances)} stopped instances matching criteria"
            )

            if not instances:
                metrics.operation_duration = time.time() - operation_start
                self.logger.info(
                    f"[{self.correlation_id}] No instances found to start "
                    f"(operation completed in {round(metrics.operation_duration, 2)}s)"
                )
                return {
                    "status": "success",
                    "message": "No instances found to start",
                    "instances_started": 0,
                    "metrics": metrics,
                    "correlation_id": self.correlation_id,
                }

            # Process instances (dry run or actual start)
            instance_ids = [inst["InstanceId"] for inst in instances]

            if dry_run:
                # Dry run mode - simulate operation
                metrics.operation_duration = time.time() - operation_start

                self.logger.info(
                    f"[{self.correlation_id}] DRY RUN: Would start {len(instances)} instances: {instance_ids} "
                    f"(simulation completed in {round(metrics.operation_duration, 2)}s)"
                )

                # Log individual instance details for dry run
                for instance_id in instance_ids:
                    instance_name = self._get_instance_name(instances, instance_id)
                    self.logger.info(
                        f"[{self.correlation_id}] DRY RUN: Would start instance {instance_id} ({instance_name})"
                    )

                return {
                    "status": "success",
                    "message": f"DRY RUN: Would start {len(instances)} instances",
                    "instances_found": len(instances),
                    "instances": instance_ids,
                    "metrics": metrics,
                    "correlation_id": self.correlation_id,
                }

            # Actual start operation
            start_operation_time = time.time()

            self.logger.info(
                f"[{self.correlation_id}] Starting {len(instance_ids)} instances: {instance_ids}"
            )

            # Log individual instance details before starting
            for instance_id in instance_ids:
                instance_name = self._get_instance_name(instances, instance_id)
                self.logger.info(
                    f"[{self.correlation_id}] Initiating start for instance: {instance_id} ({instance_name})"
                )

            # Execute start operation
            response = ec2.start_instances(InstanceIds=instance_ids)
            start_duration = time.time() - start_operation_time

            # Update metrics
            metrics.instances_started = len(instance_ids)
            metrics.operation_duration = time.time() - operation_start

            # Log successful start operations with detailed state transitions
            self.logger.info(
                f"[{self.correlation_id}] Successfully initiated start for {len(instance_ids)} instances "
                f"(AWS API call took {round(start_duration, 2)}s)"
            )

            if "StartingInstances" in response:
                for starting_instance in response["StartingInstances"]:
                    instance_id = starting_instance["InstanceId"]
                    current_state = starting_instance["CurrentState"]["Name"]
                    previous_state = starting_instance["PreviousState"]["Name"]
                    instance_name = self._get_instance_name(instances, instance_id)
                    self.logger.info(
                        f"[{self.correlation_id}] Instance {instance_id} ({instance_name}): "
                        f"{previous_state} -> {current_state}"
                    )

            self.logger.info(
                f"[{self.correlation_id}] Start operation completed successfully "
                f"(total operation time: {round(metrics.operation_duration, 2)}s)"
            )

            return {
                "status": "success",
                "message": f"Started {len(instance_ids)} instances",
                "instances_started": len(instance_ids),
                "instances": instance_ids,
                "metrics": metrics,
                "aws_response": response,
                "correlation_id": self.correlation_id,
            }

        except Exception as e:
            # Calculate operation duration even in error cases
            metrics.operation_duration = time.time() - operation_start

            # Enhanced error logging with context
            error_msg = str(e)
            zone_name = zone_info.get("name", "unknown")

            self.logger.error(
                f"[{self.correlation_id}] Failed to start servers in zone {zone_name}: {error_msg} "
                f"(operation failed after {round(metrics.operation_duration, 2)}s)"
            )

            # Log additional context for debugging
            self.logger.error(
                f"[{self.correlation_id}] Error context - Zone: {zone_name}, "
                f"Server Name: {kwargs.get('server_name', 'N/A')}, "
                f"Start All: {kwargs.get('start_all', False)}, "
                f"Dry Run: {kwargs.get('dry_run', False)}, "
                f"Managed By: {kwargs.get('managed_by', 'CMS')}"
            )

            return {
                "status": "error",
                "message": f"Failed to start servers: {error_msg}",
                "error": error_msg,
                "metrics": metrics,
                "correlation_id": self.correlation_id,
            }

    def _find_instances(
        self,
        ec2_client,
        server_name: Optional[str],
        start_all: bool,
        managed_by: Optional[str] = None,
    ) -> List[Dict]:
        """
        Find EC2 instances to start using shared utility function.
        """
        return find_instances_by_state(
            ec2_client=ec2_client,
            instance_state="stopped",
            server_name=server_name,
            operation_all=start_all,
            managed_by=managed_by,
        )

    def _get_instance_name(self, instances: List[Dict], instance_id: str) -> str:
        """
        Get the Name tag value for an instance using shared utility function.
        """
        return get_instance_name(instances, instance_id)
