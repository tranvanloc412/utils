#!/usr/bin/env python3
import time
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from .base import BaseJob
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY
from aws_ops.utils.ec2_utils import find_instances_by_state, get_instance_name


@dataclass
class StopMetrics:
    """Metrics tracking for stop servers operation"""

    total_instances_found: int = 0
    instances_stopped: int = 0
    operation_duration: float = 0.0
    dry_run_mode: bool = False


class StopServersJob(BaseJob):
    """
    Stop EC2 instances Job:

    Features:
    - Filtering with managed_by=CMS/ all support
    - Dry-run capabilities for safe operations
    """

    def __init__(self, config_manager=None):
        super().__init__(
            config_manager=config_manager,
            job_name="stop_servers",
            default_role="provision",
        )

    def execute(self, zone_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Stop EC2 instances in the specified zone"""
        operation_start = time.time()
        metrics = StopMetrics()

        try:
            # Get parameters
            server_name = kwargs.get("server_name")
            stop_all = kwargs.get("stop_all", False)
            dry_run = kwargs.get("dry_run", False)
            managed_by = kwargs.get("managed_by")
            metrics.dry_run_mode = dry_run

            zone_name = zone_info.get("zone_name", "Unknown")
            account_id = zone_info.get("account_id", "Unknown")

            # Enhanced logging with operation context
            self.logger.info(
                f"[{self.correlation_id}] Starting stop servers operation - "
                f"Zone: {zone_name}, Account: {account_id}, "
                f"Managed By: {managed_by or 'CMS'}, Dry Run: {dry_run}"
            )

            # Create EC2 client
            session = self.create_aws_session(zone_info)
            ec2 = session.client("ec2")

            # Find instances to stop
            instances = self._find_instances(ec2, server_name, stop_all, managed_by)
            metrics.total_instances_found = len(instances)

            if not instances:
                metrics.operation_duration = time.time() - operation_start
                self.logger.info(
                    f"[{self.correlation_id}] No instances found to stop - "
                    f"Operation completed in {metrics.operation_duration:.2f}s"
                )
                return {
                    "status": "success",
                    "message": "No instances found to stop",
                    "instances_stopped": 0,
                    "correlation_id": self.correlation_id,
                    "metrics": metrics,
                }

            # Stop instances
            if dry_run:
                instance_ids = [inst["InstanceId"] for inst in instances]
                self.logger.info(
                    f"[{self.correlation_id}] DRY RUN: Would stop {len(instances)} instances: {instance_ids}"
                )
                for instance_id in instance_ids:
                    instance_name = self._get_instance_name(instances, instance_id)
                    self.logger.info(
                        f"[{self.correlation_id}] DRY RUN: Would stop instance {instance_id} ({instance_name})"
                    )

                metrics.operation_duration = time.time() - operation_start
                self.logger.info(
                    f"[{self.correlation_id}] DRY RUN simulation completed in {metrics.operation_duration:.2f}s"
                )

                return {
                    "status": "success",
                    "message": f"DRY RUN: Would stop {len(instances)} instances",
                    "instances_found": len(instances),
                    "instances": instance_ids,
                    "correlation_id": self.correlation_id,
                    "metrics": metrics,
                }

            instance_ids = [inst["InstanceId"] for inst in instances]
            self.logger.info(
                f"[{self.correlation_id}] Stopping {len(instance_ids)} instances: {instance_ids}"
            )

            # Log individual instance details
            for instance_id in instance_ids:
                instance_name = self._get_instance_name(instances, instance_id)
                self.logger.info(
                    f"[{self.correlation_id}] Stopping instance: {instance_id} ({instance_name})"
                )

            # Time the stop operation
            stop_operation_start = time.time()
            response = ec2.stop_instances(InstanceIds=instance_ids)
            stop_duration = time.time() - stop_operation_start

            # Update metrics
            metrics.instances_stopped = len(instance_ids)
            metrics.operation_duration = time.time() - operation_start

            # Log successful stop operations
            self.logger.info(
                f"[{self.correlation_id}] Successfully stopped {len(instance_ids)} instances "
                f"in {stop_duration:.2f}s (Total operation: {metrics.operation_duration:.2f}s)"
            )
            if "StoppingInstances" in response:
                for stopping_instance in response["StoppingInstances"]:
                    instance_id = stopping_instance["InstanceId"]
                    current_state = stopping_instance["CurrentState"]["Name"]
                    previous_state = stopping_instance["PreviousState"]["Name"]
                    instance_name = self._get_instance_name(instances, instance_id)
                    self.logger.info(
                        f"[{self.correlation_id}] Instance {instance_id} ({instance_name}): {previous_state} -> {current_state}"
                    )

            return {
                "status": "success",
                "message": f"Stopped {len(instance_ids)} instances",
                "instances_stopped": len(instance_ids),
                "instances": instance_ids,
                "aws_response": response,
                "correlation_id": self.correlation_id,
                "metrics": metrics,
            }

        except Exception as e:
            # Calculate operation duration even in error cases
            metrics.operation_duration = time.time() - operation_start

            # Enhanced error logging with context
            zone_name = zone_info.get("zone_name", "Unknown")
            server_name = kwargs.get("server_name", "N/A")
            dry_run = kwargs.get("dry_run", False)
            managed_by = kwargs.get("managed_by", "CMS")

            self.logger.error(
                f"[{self.correlation_id}] Failed to stop servers - "
                f"Zone: {zone_name}, Server: {server_name}, "
                f"Dry Run: {dry_run}, Managed By: {managed_by}, "
                f"Duration: {metrics.operation_duration:.2f}s, Error: {str(e)}"
            )
            return {
                "status": "error",
                "message": f"Failed to stop servers: {str(e)}",
                "error": str(e),
                "correlation_id": self.correlation_id,
                "metrics": metrics,
            }

    def _find_instances(
        self,
        ec2_client,
        server_name: Optional[str],
        stop_all: bool,
        managed_by: Optional[str] = None,
    ) -> List[Dict]:
        """Find EC2 instances to stop using shared utility function."""
        return find_instances_by_state(
            ec2_client=ec2_client,
            instance_state="running",
            server_name=server_name,
            operation_all=stop_all,
            managed_by=managed_by,
        )

    def _get_instance_name(self, instances: List[Dict], instance_id: str) -> str:
        """Get the Name tag value for an instance using shared utility function."""
        return get_instance_name(instances, instance_id)
