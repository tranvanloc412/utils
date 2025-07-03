#!/usr/bin/env python3
"""
Update AMI Job - Simplified Version

This module provides functionality to update AMIs in launch templates across multiple AWS accounts.
Simplified version focusing on core functionality with clean, maintainable code.
"""

from typing import Dict, List, Any, Optional
from .base import BaseJob
from aws_ops.core.constants import CMS_MANAGED, MANAGED_BY_KEY
from aws_ops.utils.config import ConfigManager


class UpdateAMIJob(BaseJob):
    """Job to update AMIs in launch templates"""

    def __init__(self):
        super().__init__(job_name="update_ami", default_role="provision")
        self.config_manager = ConfigManager()

    def execute(self, zone_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Update AMI in launch templates for the specified zone
        """
        try:
            # Get parameters
            ami_id = kwargs.get("ami_id")
            template_name = kwargs.get("template_name")
            dry_run = kwargs.get("dry_run", True)
            managed_by = kwargs.get("managed_by")

            # Validate required parameters
            if not ami_id:
                return {"status": "error", "message": "AMI ID is required"}

            if not self._is_valid_ami_id(ami_id):
                return {
                    "status": "error",
                    "message": f"Invalid AMI ID format: {ami_id}",
                }

            # Create AWS session and client
            session = self.create_aws_session(zone_info)
            ec2 = session.client("ec2")

            # Verify AMI exists and is available
            if not self._verify_ami(ec2, ami_id):
                return {
                    "status": "error",
                    "message": f"AMI {ami_id} not found or not available",
                }

            # Find launch templates to update
            templates = self._find_launch_templates(ec2, template_name, managed_by)

            if not templates:
                return {
                    "status": "success",
                    "message": "No launch templates found to update",
                    "templates_updated": 0,
                }

            # Handle dry run
            if dry_run:
                return {
                    "status": "success",
                    "message": f"DRY RUN: Would update {len(templates)} launch templates with AMI {ami_id}",
                    "templates_found": len(templates),
                    "templates": [t["LaunchTemplateName"] for t in templates],
                    "ami_id": ami_id,
                }

            # Update launch templates
            zone_name = zone_info.get("name", "")
            results = self._update_launch_templates(ec2, templates, ami_id, zone_name)

            return {
                "status": "success",
                "message": f"Updated {len(results['updated'])} launch templates with AMI {ami_id}",
                "templates_updated": len(results["updated"]),
                "updated_templates": results["updated"],
                "failed_templates": results["failed"],
                "ami_id": ami_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to update AMI: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"Failed to update AMI: {str(e)}"}

    def _is_valid_ami_id(self, ami_id: str) -> bool:
        """
        Validate AMI ID format
        """
        return ami_id.startswith("ami-") and len(ami_id) == 21

    def _verify_ami(self, ec2_client, ami_id: str) -> bool:
        """
        Verify AMI exists and is available
        """
        try:
            response = ec2_client.describe_images(ImageIds=[ami_id])
            images = response["Images"]

            if not images:
                return False

            return images[0]["State"] == "available"

        except Exception as e:
            self.logger.error(f"Error verifying AMI {ami_id}: {e}")
            return False

    def _get_kms_key_for_zone(
        self, zone_name: str, template_name: str
    ) -> Optional[str]:
        """
        Get KMS key for encryption from settings configuration

        Args:
            zone_name: Landing zone name
            template_name: Launch template name

        Returns:
            KMS key ID or None if not found
        """
        try:
            asg_config = self.config_manager.get_value("asg_stateless", {})

            if zone_name in asg_config:
                for asg_item in asg_config[zone_name]:
                    if asg_item.get("launch_template") == template_name:
                        return asg_item.get("kms_key")

            # Fallback: look for any KMS key in the zone configuration
            if zone_name in asg_config and asg_config[zone_name]:
                return asg_config[zone_name][0].get("kms_key")

            return None

        except Exception as e:
            self.logger.warning(
                f"Error getting KMS key for zone {zone_name}, template {template_name}: {e}"
            )
            return None

    def _add_ebs_encryption(
        self, launch_template_data: Dict[str, Any], kms_key: str
    ) -> None:
        """
        Add EBS encryption settings to launch template data
        """
        try:
            # Ensure BlockDeviceMappings exists
            if "BlockDeviceMappings" not in launch_template_data:
                launch_template_data["BlockDeviceMappings"] = []

            # If no block device mappings exist, create a default root volume mapping
            if not launch_template_data["BlockDeviceMappings"]:
                launch_template_data["BlockDeviceMappings"] = [
                    {
                        "DeviceName": "/dev/sda1",  # Default root device for most AMIs
                        "Ebs": {
                            "VolumeType": "gp3",
                            "VolumeSize": 20,
                            "DeleteOnTermination": True,
                            "Encrypted": True,
                            "KmsKeyId": kms_key,
                        },
                    }
                ]
            else:
                # Update existing block device mappings to add encryption
                for bdm in launch_template_data["BlockDeviceMappings"]:
                    if "Ebs" in bdm:
                        bdm["Ebs"]["Encrypted"] = True
                        bdm["Ebs"]["KmsKeyId"] = kms_key

            self.logger.info(f"Added EBS encryption with KMS key: {kms_key}")

        except Exception as e:
            self.logger.error(f"Error adding EBS encryption: {e}")

    def _find_launch_templates(
        self, ec2_client, template_name: Optional[str], managed_by: Optional[str] = None
    ) -> List[Dict]:
        """
        Find launch templates to update
        """
        try:
            # Build filters
            filters = []
            if not managed_by or managed_by.upper() != "ALL":
                filters.append(
                    {"Name": f"tag:{MANAGED_BY_KEY}", "Values": [CMS_MANAGED]}
                )

            # Get templates
            if template_name:
                if filters:
                    response = ec2_client.describe_launch_templates(
                        LaunchTemplateNames=[template_name], Filters=filters
                    )
                else:
                    response = ec2_client.describe_launch_templates(
                        LaunchTemplateNames=[template_name]
                    )
            else:
                if filters:
                    response = ec2_client.describe_launch_templates(Filters=filters)
                else:
                    response = ec2_client.describe_launch_templates()

            return response["LaunchTemplates"]

        except Exception as e:
            self.logger.error(f"Error finding launch templates: {e}")
            return []

    def _update_launch_templates(
        self, ec2_client, templates: List[Dict], ami_id: str, zone_name: str = None
    ) -> Dict[str, List[str]]:
        """
        Update launch templates with new AMI

        Args:
            ec2_client: EC2 client
            templates: List of launch template dictionaries
            ami_id: New AMI ID

        Returns:
            Dictionary with updated and failed template names
        """
        updated = []
        failed = []

        for template in templates:
            try:
                template_id = template["LaunchTemplateId"]
                template_name = template["LaunchTemplateName"]

                # Get current template version
                response = ec2_client.describe_launch_template_versions(
                    LaunchTemplateId=template_id, Versions=["$Latest"]
                )

                if not response["LaunchTemplateVersions"]:
                    failed.append(template_name)
                    continue

                current_version = response["LaunchTemplateVersions"][0]
                launch_template_data = current_version["LaunchTemplateData"].copy()
                old_ami_id = launch_template_data.get("ImageId")

                # Skip if AMI is already the same
                if old_ami_id == ami_id:
                    self.logger.info(
                        f"Template {template_name} already uses AMI {ami_id}"
                    )
                    continue

                # Update AMI ID
                launch_template_data["ImageId"] = ami_id

                # Add EBS encryption if KMS key is configured
                kms_key = self._get_kms_key_for_zone(zone_name or "", template_name)
                if kms_key:
                    self._add_ebs_encryption(launch_template_data, kms_key)

                # Create new version
                ec2_client.create_launch_template_version(
                    LaunchTemplateId=template_id,
                    LaunchTemplateData=launch_template_data,
                    VersionDescription=f"Updated AMI from {old_ami_id} to {ami_id}",
                )

                # Set new version as default
                ec2_client.modify_launch_template(
                    LaunchTemplateId=template_id, DefaultVersion="$Latest"
                )

                updated.append(template_name)
                self.logger.info(
                    f"Updated template {template_name}: {old_ami_id} -> {ami_id}"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to update template {template.get('LaunchTemplateName', 'unknown')}: {e}"
                )
                failed.append(template.get("LaunchTemplateName", "unknown"))

        return {"updated": updated, "failed": failed}
