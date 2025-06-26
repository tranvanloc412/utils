"""Manage AWS Backups - Snapshots and AMIs

Manages EBS snapshots and AMIs across AWS landing zones with capabilities for:
- Scanning snapshots and AMIs based on age
- Generating reports
- Deleting old snapshots and AMIs
- Creating AMIs for EC2 instances with managed_by=CMS tag
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import boto3
import logging
from botocore.exceptions import ClientError, BotoCoreError

from aws_ops.core.processors.zone_processor import ZoneProcessor
from aws_ops.core.processors.report_generator import CSVReportGenerator, ReportConfig
from aws_ops.utils.logger import setup_logger
from aws_ops.core.aws.ec2 import EC2Manager
from aws_ops.core.models.ami import AMIInfo
from aws_ops.core.models.snapshot import SnapshotInfo
from aws_ops.jobs.base import BaseJob

logger = setup_logger(__name__, "manage_backups.log")


@dataclass
class BackupParameters:
    """Parameters for backup management operations."""
    
    region: str = "ap-southeast-2"
    action: str = "scan"  # scan, delete, create
    resource_type: str = "both"  # snapshots, amis, both
    age_days: int = 30  # Age threshold for operations
    output: Optional[str] = None
    dry_run: bool = True
    
    def get_operation_description(self) -> str:
        """Get human-readable operation description."""
        action_desc = {
            "scan": "Scanning",
            "delete": "Deleting",
            "create": "Creating AMIs for"
        }.get(self.action, "Processing")
        
        resource_desc = {
            "snapshots": "snapshots",
            "amis": "AMIs", 
            "both": "snapshots and AMIs"
        }.get(self.resource_type, "resources")
        
        if self.action == "create":
            return f"{action_desc} EC2 instances with managed_by=CMS tag"
        else:
            return f"{action_desc} {resource_desc} older than {self.age_days} days"


class BackupManager:
    """Manager for AWS backup operations (snapshots and AMIs)."""
    
    def __init__(self, session: boto3.Session, region: str = "ap-southeast-2"):
        """Initialize BackupManager."""
        self.session = session
        self.region = region
        self.ec2_client = session.client("ec2", region_name=region)
        self.ec2_manager = EC2Manager(session, region)
        self.logger = logging.getLogger(__name__)
    
    def scan_snapshots(self, age_days: int = 30) -> List[Dict[str, Any]]:
        """Scan EBS snapshots based on age."""
        try:
            cutoff_date = datetime.now() - timedelta(days=age_days)
            
            response = self.ec2_client.describe_snapshots(
                OwnerIds=['self'],
                Filters=[
                    {'Name': 'status', 'Values': ['completed']}
                ]
            )
            
            old_snapshots = []
            for snapshot in response['Snapshots']:
                start_time = snapshot['StartTime'].replace(tzinfo=None)
                if start_time < cutoff_date:
                    snapshot_info = SnapshotInfo(
                        snapshot_id=snapshot['SnapshotId'],
                        volume_id=snapshot['VolumeId'],
                        volume_size=snapshot['VolumeSize'],
                        state=snapshot['State'],
                        account_id=snapshot.get('OwnerId', ''),
                        description=snapshot.get('Description', ''),
                        start_time=start_time,
                        encrypted=snapshot.get('Encrypted', False),
                        tags={tag['Key']: tag['Value'] for tag in snapshot.get('Tags', [])}
                    )
                    old_snapshots.append(snapshot_info.to_dict())
            
            return old_snapshots
            
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error scanning snapshots: {e}")
            return []
    
    def scan_amis(self, age_days: int = 30) -> List[Dict[str, Any]]:
        """Scan AMIs based on age."""
        try:
            cutoff_date = datetime.now() - timedelta(days=age_days)
            
            response = self.ec2_client.describe_images(
                Owners=['self'],
                Filters=[
                    {'Name': 'state', 'Values': ['available']}
                ]
            )
            
            old_amis = []
            for image in response['Images']:
                creation_date = datetime.strptime(
                    image['CreationDate'], 
                    '%Y-%m-%dT%H:%M:%S.%fZ'
                )
                
                if creation_date < cutoff_date:
                    ami_info = AMIInfo(
                        image_id=image['ImageId'],
                        name=image['Name'],
                        state=image['State'],
                        creation_date=creation_date,
                        platform=image.get('Platform', 'linux'),
                        tags={tag['Key']: tag['Value'] for tag in image.get('Tags', [])}
                    )
                    old_amis.append(ami_info.to_dict())
            
            return old_amis
            
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error scanning AMIs: {e}")
            return []
    
    def delete_snapshots(self, snapshot_ids: List[str], dry_run: bool = True) -> Dict[str, Any]:
        """Delete EBS snapshots."""
        results = {'deleted': [], 'failed': [], 'dry_run': dry_run}
        
        for snapshot_id in snapshot_ids:
            try:
                if not dry_run:
                    self.ec2_client.delete_snapshot(SnapshotId=snapshot_id)
                    results['deleted'].append(snapshot_id)
                    self.logger.info(f"Deleted snapshot: {snapshot_id}")
                else:
                    results['deleted'].append(snapshot_id)
                    self.logger.info(f"[DRY RUN] Would delete snapshot: {snapshot_id}")
                    
            except (ClientError, BotoCoreError) as e:
                error_msg = f"Failed to delete snapshot {snapshot_id}: {e}"
                results['failed'].append({'snapshot_id': snapshot_id, 'error': str(e)})
                self.logger.error(error_msg)
        
        return results
    
    def delete_amis(self, image_ids: List[str], dry_run: bool = True) -> Dict[str, Any]:
        """Delete AMIs and associated snapshots."""
        results = {'deleted': [], 'failed': [], 'dry_run': dry_run}
        
        for image_id in image_ids:
            try:
                # Get AMI details to find associated snapshots
                if not dry_run:
                    response = self.ec2_client.describe_images(ImageIds=[image_id])
                    if response['Images']:
                        image = response['Images'][0]
                        
                        # Deregister AMI
                        self.ec2_client.deregister_image(ImageId=image_id)
                        
                        # Delete associated snapshots
                        for block_device in image.get('BlockDeviceMappings', []):
                            if 'Ebs' in block_device and 'SnapshotId' in block_device['Ebs']:
                                snapshot_id = block_device['Ebs']['SnapshotId']
                                try:
                                    self.ec2_client.delete_snapshot(SnapshotId=snapshot_id)
                                    self.logger.info(f"Deleted associated snapshot: {snapshot_id}")
                                except Exception as snap_error:
                                    self.logger.warning(f"Failed to delete snapshot {snapshot_id}: {snap_error}")
                    
                    results['deleted'].append(image_id)
                    self.logger.info(f"Deleted AMI: {image_id}")
                else:
                    results['deleted'].append(image_id)
                    self.logger.info(f"[DRY RUN] Would delete AMI: {image_id}")
                    
            except (ClientError, BotoCoreError) as e:
                error_msg = f"Failed to delete AMI {image_id}: {e}"
                results['failed'].append({'image_id': image_id, 'error': str(e)})
                self.logger.error(error_msg)
        
        return results
    
    def create_amis_for_cms_instances(self, dry_run: bool = True) -> Dict[str, Any]:
        """Create AMIs for EC2 instances with managed_by=CMS tag."""
        results = {'created': [], 'failed': [], 'dry_run': dry_run}
        
        try:
            # Find instances with managed_by=CMS tag
            instances = self.ec2_manager.get_instances_by_filter(
                'tag:managed_by', ['CMS']
            )
            
            for instance in instances:
                instance_id = instance['InstanceId']
                instance_name = ''
                
                # Get instance name from tags
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                ami_name = f"cms-backup-{instance_name or instance_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                
                try:
                    if not dry_run:
                        response = self.ec2_client.create_image(
                            InstanceId=instance_id,
                            Name=ami_name,
                            Description=f"Automated backup of {instance_name or instance_id} created by CMS backup job",
                            NoReboot=True,
                            TagSpecifications=[
                                {
                                    'ResourceType': 'image',
                                    'Tags': [
                                        {'Key': 'Name', 'Value': ami_name},
                                        {'Key': 'CreatedBy', 'Value': 'CMS-BackupJob'},
                                        {'Key': 'SourceInstance', 'Value': instance_id},
                                        {'Key': 'CreationDate', 'Value': datetime.now().isoformat()}
                                    ]
                                }
                            ]
                        )
                        
                        ami_id = response['ImageId']
                        results['created'].append({
                            'instance_id': instance_id,
                            'instance_name': instance_name,
                            'ami_id': ami_id,
                            'ami_name': ami_name
                        })
                        self.logger.info(f"Created AMI {ami_id} for instance {instance_id}")
                    else:
                        results['created'].append({
                            'instance_id': instance_id,
                            'instance_name': instance_name,
                            'ami_id': 'dry-run',
                            'ami_name': ami_name
                        })
                        self.logger.info(f"[DRY RUN] Would create AMI {ami_name} for instance {instance_id}")
                        
                except (ClientError, BotoCoreError) as e:
                    error_msg = f"Failed to create AMI for instance {instance_id}: {e}"
                    results['failed'].append({
                        'instance_id': instance_id,
                        'instance_name': instance_name,
                        'error': str(e)
                    })
                    self.logger.error(error_msg)
            
            return results
            
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error finding CMS instances: {e}")
            return results


def manage_backups(session, zone_name: str, account_id: str, **kwargs) -> Dict[str, Any]:
    """Main function to manage backups in a specific landing zone."""
    
    # Extract parameters
    region = kwargs.get('region', 'ap-southeast-2')
    action = kwargs.get('action', 'scan')
    resource_type = kwargs.get('resource_type', 'both')
    age_days = kwargs.get('age_days', 30)
    snapshot_age_days = kwargs.get('snapshot_age_days', 30)
    ami_age_days = kwargs.get('ami_age_days', 90)
    delete_old_snapshots = kwargs.get('delete_old_snapshots', False)
    delete_old_amis = kwargs.get('delete_old_amis', False)
    create_amis = kwargs.get('create_amis', False)
    output = kwargs.get('output')
    dry_run = kwargs.get('dry_run', True)
    
    backup_manager = BackupManager(session, region)
    results = {
        'zone_name': zone_name,
        'account_id': account_id,
        'action': action,
        'resource_type': resource_type,
        'snapshot_age_days': snapshot_age_days,
        'ami_age_days': ami_age_days,
        'dry_run': dry_run,
        'snapshots': [],
        'amis': [],
        'operations': {}
    }
    
    try:
        # Handle snapshot operations
        if delete_old_snapshots or (action == 'scan' and resource_type in ['snapshots', 'both']):
            results['snapshots'] = backup_manager.scan_snapshots(snapshot_age_days)
            logger.info(f"Found {len(results['snapshots'])} old snapshots in {zone_name}")
            
            if delete_old_snapshots:
                snapshot_ids = [s['snapshot_id'] for s in results['snapshots']]
                if snapshot_ids:
                    results['operations']['snapshots'] = backup_manager.delete_snapshots(
                        snapshot_ids, dry_run
                    )
        
        # Handle AMI operations
        if delete_old_amis or (action == 'scan' and resource_type in ['amis', 'both']):
            results['amis'] = backup_manager.scan_amis(ami_age_days)
            logger.info(f"Found {len(results['amis'])} old AMIs in {zone_name}")
            
            if delete_old_amis:
                image_ids = [a['image_id'] for a in results['amis']]
                if image_ids:
                    results['operations']['amis'] = backup_manager.delete_amis(
                        image_ids, dry_run
                    )
        
        # Handle AMI creation
        if create_amis:
            results['operations']['create_amis'] = backup_manager.create_amis_for_cms_instances(
                dry_run
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Error managing backups in {zone_name}: {e}")
        results['error'] = str(e)
        return results


def write_backup_report(data: List[Dict[str, Any]], output_file: str, report_type: str):
    """Write backup scan results to CSV report."""
    if not data:
        logger.info("No data to write to report")
        return
    
    try:
        output_path = Path(output_file)
        
        # Determine fields based on report type
        if report_type == 'snapshots':
            fields = [
                'zone_name', 'account_id', 'snapshot_id', 'volume_id', 
                'volume_size', 'state', 'start_time', 'age_days', 
                'encrypted', 'description'
            ]
        elif report_type == 'amis':
            fields = [
                'zone_name', 'account_id', 'image_id', 'name', 
                'state', 'creation_date', 'platform'
            ]
        else:  # combined report
            fields = [
                'zone_name', 'account_id', 'resource_type', 'resource_id', 
                'name', 'state', 'creation_date', 'age_days'
            ]
        
        config = ReportConfig(
            output_file=str(output_path),
            fields=fields,
            title=f"AWS Backup {report_type.title()} Report"
        )
        
        generator = CSVReportGenerator(config)
        generator.write_report(data)
        
        logger.info(f"Backup report written to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error writing backup report: {e}")


class ManageBackups(BaseJob):
    """Job class for managing AWS backups (snapshots and AMIs)."""
    
    def execute(
        self,
        landing_zones: Optional[List[str]] = None,
        region: str = "ap-southeast-2",
        action: str = "scan",
        resource_type: str = "both",
        age_days: int = 30,
        output: Optional[str] = None,
        dry_run: bool = True,
        snapshot_age_days: int = 30,
        ami_age_days: int = 90,
        delete_old_snapshots: bool = False,
        delete_old_amis: bool = False,
        create_amis: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute backup management job."""
        
        # Determine action and resource type based on flags
        if delete_old_snapshots and delete_old_amis:
            action = "delete"
            resource_type = "both"
            age_days = min(snapshot_age_days, ami_age_days)
        elif delete_old_snapshots:
            action = "delete"
            resource_type = "snapshots"
            age_days = snapshot_age_days
        elif delete_old_amis:
            action = "delete"
            resource_type = "amis"
            age_days = ami_age_days
        elif create_amis:
            action = "create"
            resource_type = "amis"
        else:
            action = "scan"
            resource_type = "both"
            age_days = min(snapshot_age_days, ami_age_days)
        
        params = BackupParameters(
            region=region,
            action=action,
            resource_type=resource_type,
            age_days=age_days,
            output=output,
            dry_run=dry_run
        )
        
        processor = ZoneProcessor(
            script_name="manage_backups",
            description=f"Manage AWS backups: {params.get_operation_description()}"
        )
        
        try:
            all_results, summary = processor.process_zones_with_aggregation(
                process_function=manage_backups,
                landing_zones=landing_zones,
                environment=None,  # Add missing environment parameter
                session_purpose="backup-management",
                region=params.region,
                action=params.action,
                resource_type=params.resource_type,
                age_days=params.age_days,
                output=params.output,
                dry_run=params.dry_run,
                snapshot_age_days=snapshot_age_days,
                ami_age_days=ami_age_days,
                delete_old_snapshots=delete_old_snapshots,
                delete_old_amis=delete_old_amis,
                create_amis=create_amis
            )
            
            # Aggregate results
            total_snapshots = sum(len(result.get('snapshots', [])) for result in all_results)
            total_amis = sum(len(result.get('amis', [])) for result in all_results)
            
            # Write report if requested and data exists
            if params.output and (total_snapshots > 0 or total_amis > 0):
                # Flatten results for reporting
                report_data = []
                for result in all_results:
                    zone_name = result.get('zone_name', '')
                    account_id = result.get('account_id', '')
                    
                    # Add snapshots to report
                    for snapshot in result.get('snapshots', []):
                        snapshot['zone_name'] = zone_name
                        snapshot['account_id'] = account_id
                        snapshot['resource_type'] = 'snapshot'
                        snapshot['resource_id'] = snapshot['snapshot_id']
                        report_data.append(snapshot)
                    
                    # Add AMIs to report
                    for ami in result.get('amis', []):
                        ami['zone_name'] = zone_name
                        ami['account_id'] = account_id
                        ami['resource_type'] = 'ami'
                        ami['resource_id'] = ami['image_id']
                        report_data.append(ami)
                
                write_backup_report(report_data, params.output, params.resource_type)
            
            # Print summary
            operation_summary = {
                "Operation": params.get_operation_description(),
                "Resource type": params.resource_type,
                "Age threshold": f"{params.age_days} days",
                "Dry run": "Yes" if params.dry_run else "No",
                "Total snapshots found": total_snapshots,
                "Total AMIs found": total_amis,
                "Output file": params.output if params.output and (total_snapshots > 0 or total_amis > 0) else "None"
            }
            
            processor.print_summary(summary, operation_summary)
            
            return {
                "success": True,
                "operation": params.get_operation_description(),
                "snapshots_found": total_snapshots,
                "amis_found": total_amis,
                "output_file": params.output if params.output and (total_snapshots > 0 or total_amis > 0) else None,
                "dry_run": params.dry_run,
                "summary": summary,
                "results": all_results
            }
            
        except Exception as e:
            logger.error(f"Error executing backup management job: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": params.get_operation_description(),
                "snapshots_found": 0,
                "amis_found": 0,
                "output_file": None
            }