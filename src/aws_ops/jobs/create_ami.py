#!/usr/bin/env python3

import datetime
from typing import Dict, List, Any, Optional
from .base import BaseJob
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY
from aws_ops.utils.ec2_utils import (
    find_instances_by_state,
    get_instance_tags,
)


class CreateAMIJob(BaseJob):
    """Job to create AMIs from EC2 instances"""

    def __init__(self):
        super().__init__(job_name="create_ami", default_role="provision")

    def execute(self, zone_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Create AMI from EC2 instances by server name"""
        try:
            # Extract parameters
            server_name = kwargs.get("server_name")
            no_reboot = kwargs.get("no_reboot", True)
            managed_by = kwargs.get("managed_by", "CMS")

            # Validate parameters
            if not server_name:
                return {
                    "status": "error",
                    "message": "server_name must be provided",
                }

            # Create EC2 client
            session = self.create_aws_session(zone_info)
            ec2_client = session.client("ec2")

            # Find instances by server name
            instances = self._find_instances_by_name(
                ec2_client, server_name, managed_by
            )

            if not instances:
                return {
                    "status": "error",
                    "message": f"No instances found with server name: {server_name}",
                }

            # Process each instance
            results = []
            for instance in instances:
                result = self._create_ami_for_instance(
                    ec2_client, instance, no_reboot, zone_info
                )
                results.append(result)

            # Summarize results
            successful = [r for r in results if r["status"] == "success"]
            failed = [r for r in results if r["status"] == "error"]

            return {
                "status": (
                    "success" if not failed else "partial" if successful else "error"
                ),
                "message": f"Processed {len(instances)} instance(s): {len(successful)} successful, {len(failed)} failed",
                "total_instances": len(instances),
                "successful_count": len(successful),
                "failed_count": len(failed),
                "results": results,
            }

        except Exception as e:
            self.logger.error(f"Failed to create AMI: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to create AMI: {str(e)}",
                "error": str(e),
            }

    def _find_instances_by_name(
        self, ec2_client, server_name: str, managed_by: str
    ) -> List[Dict]:
        """Find instances by server name pattern"""
        return find_instances_by_state(
            ec2_client=ec2_client,
            instance_state="running",
            server_name=server_name,
            operation_all=False,
            managed_by=managed_by,
        )

    def _get_instance_name(self, instance: Dict) -> str:
        tags = get_instance_tags(instance)
        return tags.get("Name", f"Instance-{instance.get('InstanceId', 'Unknown')}")

    def _create_ami_for_instance(
        self, ec2_client, instance: Dict, no_reboot: bool, zone_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create AMI for a specific instance"""
        try:
            instance_id = instance.get("InstanceId")
            instance_name = self._get_instance_name(instance)

            # Validate instance state
            instance_state = instance.get("State", {}).get("Name")
            if instance_state not in ["running", "stopped"]:
                return {
                    "status": "error",
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "message": f"Instance is in '{instance_state}' state. Only 'running' or 'stopped' instances can be used for AMI creation.",
                }

            # Generate AMI name
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            ami_name = f"{instance_name}-{timestamp}"

            # Generate description
            description = f"AMI created from {instance_name} ({instance_id}) on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # Create the AMI
            self.logger.info(
                f"Creating AMI '{ami_name}' from instance {instance_name} ({instance_id})"
            )

            response = ec2_client.create_image(
                InstanceId=instance_id,
                Name=ami_name,
                Description=description,
                NoReboot=no_reboot,
            )

            ami_id = response["ImageId"]

            # Apply basic tags
            tags = {
                "Name": ami_name,
                "SourceInstanceId": instance_id,
                "SourceInstanceName": instance_name,
                "managed_by": CMS_MANAGED,
                "CreatedDate": datetime.datetime.now().strftime("%Y-%m-%d"),
            }

            ec2_client.create_tags(
                Resources=[ami_id],
                Tags=[{"Key": k, "Value": v} for k, v in tags.items()],
            )

            self.logger.info(
                f"Successfully created AMI {ami_id} from instance {instance_name} ({instance_id})"
            )

            return {
                "status": "success",
                "instance_id": instance_id,
                "instance_name": instance_name,
                "ami_id": ami_id,
                "ami_name": ami_name,
                "message": f"Successfully created AMI {ami_id} from instance {instance_name} ({instance_id})",
            }

        except Exception as e:
            error_msg = f"Failed to create AMI for instance {instance.get('InstanceId', 'Unknown')}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "instance_id": instance.get("InstanceId"),
                "instance_name": self._get_instance_name(instance),
                "message": error_msg,
                "error": str(e),
            }
