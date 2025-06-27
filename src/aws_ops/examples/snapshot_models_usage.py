#!/usr/bin/env python3
"""Snapshot Models Usage Examples

This script demonstrates how to use the snapshot data models for AWS EBS snapshot management.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# Import snapshot models
from core.models.snapshot import (
    SnapshotState,
    VolumeType,
    EncryptionStatus,
    SnapshotInfo,
    DetailedSnapshotInfo,
    SnapshotCollection,
    VolumeInfo,
    create_snapshot_info,
    create_snapshot_collection,
    filter_old_snapshots
)


def example_basic_snapshot_info():
    """Example: Creating basic snapshot information."""
    print("\n=== Basic Snapshot Information ===")
    
    # Create a basic snapshot info
    snapshot = SnapshotInfo(
        snapshot_id="snap-1234567890abcdef0",
        landing_zone="Production",
        account_id="123456789012",
        volume_id="vol-1234567890abcdef0",
        volume_size=100,
        state=SnapshotState.COMPLETED,
        description="Daily backup of production database",
        start_time=datetime.now() - timedelta(days=5),
        encrypted=True,
        kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        tags={
            "Name": "prod-db-backup",
            "Environment": "production",
            "BackupType": "daily",
            "Application": "database"
        }
    )
    
    print(f"Snapshot ID: {snapshot.snapshot_id}")
    print(f"Display Name: {snapshot.display_name}")
    print(f"State: {snapshot.state.value}")
    print(f"Size: {snapshot.size_gb} GB")
    print(f"Age: {snapshot.age_days} days")
    print(f"Encrypted: {snapshot.is_encrypted}")
    print(f"Environment: {snapshot.get_tag('Environment')}")
    
    # Check properties
    print(f"\nSnapshot Properties:")
    print(f"  Is Completed: {snapshot.is_completed}")
    print(f"  Is Pending: {snapshot.is_pending}")
    print(f"  Has Error: {snapshot.has_error}")
    print(f"  Is Older than 3 days: {snapshot.is_older_than(3)}")
    print(f"  Has 'Environment' tag: {snapshot.has_tag('Environment')}")
    print(f"  Has 'Environment=production' tag: {snapshot.has_tag('Environment', 'production')}")
    
    return snapshot


def example_detailed_snapshot_info():
    """Example: Creating detailed snapshot information."""
    print("\n=== Detailed Snapshot Information ===")
    
    # Create volume info
    volume_info = VolumeInfo(
        volume_id="vol-1234567890abcdef0",
        volume_size=100,
        volume_type=VolumeType.GP3,
        availability_zone="us-east-1a",
        encrypted=True,
        kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        iops=3000,
        throughput=125
    )
    
    # Create detailed snapshot info
    detailed_snapshot = DetailedSnapshotInfo(
        snapshot_id="snap-1234567890abcdef0",
        landing_zone="Production",
        account_id="123456789012",
        volume_id="vol-1234567890abcdef0",
        volume_size=100,
        state=SnapshotState.COMPLETED,
        description="Daily backup of production database",
        start_time=datetime.now() - timedelta(days=5),
        encrypted=True,
        kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        tags={
            "Name": "prod-db-backup",
            "Environment": "production",
            "BackupType": "daily"
        },
        # Detailed fields
        volume_info=volume_info,
        storage_tier="standard",
        public=False,
        shared_accounts=["987654321098"],
        estimated_cost_per_month=5.0
    )
    
    print(f"Detailed Snapshot: {detailed_snapshot.snapshot_id}")
    print(f"Volume Type: {detailed_snapshot.volume_info.volume_type.value}")
    print(f"IOPS: {detailed_snapshot.volume_info.iops}")
    print(f"Throughput: {detailed_snapshot.volume_info.throughput} MB/s")
    print(f"Storage Tier: {detailed_snapshot.storage_tier}")
    print(f"Is Public: {detailed_snapshot.is_public}")
    print(f"Is Shared: {detailed_snapshot.is_shared}")
    print(f"Shared Accounts: {detailed_snapshot.shared_accounts}")
    print(f"Estimated Monthly Cost: ${detailed_snapshot.estimated_monthly_cost:.2f}")
    
    return detailed_snapshot


def example_snapshot_collection():
    """Example: Working with snapshot collections."""
    print("\n=== Snapshot Collection ===")
    
    # Create multiple snapshots
    snapshots_data = [
        {
            "snapshot_id": "snap-1111111111111111",
            "landing_zone": "Production",
            "account_id": "123456789012",
            "volume_id": "vol-1111111111111111",
            "volume_size": 50,
            "state": "completed",
            "description": "Web server backup",
            "start_time": datetime.now() - timedelta(days=2),
            "encrypted": True,
            "tags": {"Name": "web-backup", "Environment": "production"}
        },
        {
            "snapshot_id": "snap-2222222222222222",
            "landing_zone": "Development",
            "account_id": "123456789012",
            "volume_id": "vol-2222222222222222",
            "volume_size": 20,
            "state": "completed",
            "description": "Dev database backup",
            "start_time": datetime.now() - timedelta(days=10),
            "encrypted": False,
            "tags": {"Name": "dev-db-backup", "Environment": "development"}
        },
        {
            "snapshot_id": "snap-3333333333333333",
            "landing_zone": "Production",
            "account_id": "123456789012",
            "volume_id": "vol-3333333333333333",
            "volume_size": 200,
            "state": "pending",
            "description": "Large data backup",
            "start_time": datetime.now() - timedelta(hours=2),
            "encrypted": True,
            "tags": {"Name": "data-backup", "Environment": "production"}
        }
    ]
    
    # Create snapshots from data
    snapshots = [SnapshotInfo.from_dict(data) for data in snapshots_data]
    
    # Create collection
    collection = SnapshotCollection(
        snapshots=snapshots,
        metadata={"scan_time": datetime.now().isoformat(), "region": "us-east-1"}
    )
    
    print(f"Total snapshots: {len(collection)}")
    print(f"Total size: {collection.total_size_gb} GB")
    print(f"Estimated monthly cost: ${collection.estimated_monthly_cost:.2f}")
    
    # Filter examples
    print("\nFiltering Examples:")
    
    # Filter by state
    completed = collection.completed_snapshots
    pending = collection.pending_snapshots
    print(f"  Completed snapshots: {len(completed)}")
    print(f"  Pending snapshots: {len(pending)}")
    
    # Filter by landing zone
    prod_snapshots = collection.filter_by_landing_zone("Production")
    dev_snapshots = collection.filter_by_landing_zone("Development")
    print(f"  Production snapshots: {len(prod_snapshots)}")
    print(f"  Development snapshots: {len(dev_snapshots)}")
    
    # Filter by encryption
    encrypted = collection.encrypted_snapshots
    unencrypted = collection.unencrypted_snapshots
    print(f"  Encrypted snapshots: {len(encrypted)}")
    print(f"  Unencrypted snapshots: {len(unencrypted)}")
    
    # Filter by age
    old_snapshots = collection.get_old_snapshots(7)  # Older than 7 days
    recent_snapshots = collection.get_recent_snapshots(3)  # Newer than 3 days
    print(f"  Old snapshots (>7 days): {len(old_snapshots)}")
    print(f"  Recent snapshots (<3 days): {len(recent_snapshots)}")
    
    # Filter by size
    large_snapshots = collection.filter_by_size(min_gb=100)
    small_snapshots = collection.filter_by_size(max_gb=50)
    print(f"  Large snapshots (>=100 GB): {len(large_snapshots)}")
    print(f"  Small snapshots (<=50 GB): {len(small_snapshots)}")
    
    # Filter by tag
    prod_env = collection.filter_by_tag("Environment", "production")
    print(f"  Production environment snapshots: {len(prod_env)}")
    
    # Collection summary
    print("\nCollection Summary:")
    summary = collection.summary
    print(json.dumps(summary, indent=2, default=str))
    
    return collection


def example_aws_integration():
    """Example: Integration with AWS snapshot data."""
    print("\n=== AWS Integration ===")
    
    # Simulate AWS EBS snapshot data
    aws_snapshots = [
        {
            "SnapshotId": "snap-aws1111111111111",
            "VolumeId": "vol-aws1111111111111",
            "VolumeSize": 80,
            "State": "completed",
            "Description": "Created by CreateImage(i-1234567890abcdef0) for ami-1234567890abcdef0",
            "StartTime": "2024-01-15T10:30:00.000Z",
            "Encrypted": True,
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
            "Progress": "100%",
            "OwnerId": "123456789012",
            "Tags": [
                {"Key": "Name", "Value": "ami-backup"},
                {"Key": "Environment", "Value": "production"},
                {"Key": "CreatedBy", "Value": "AMI"}
            ]
        },
        {
            "SnapshotId": "snap-aws2222222222222",
            "VolumeId": "vol-aws2222222222222",
            "VolumeSize": 30,
            "State": "completed",
            "Description": "Manual backup",
            "StartTime": "2024-01-10T14:20:00.000Z",
            "Encrypted": False,
            "Progress": "100%",
            "OwnerId": "123456789012",
            "Tags": [
                {"Key": "Name", "Value": "manual-backup"},
                {"Key": "Environment", "Value": "development"}
            ]
        }
    ]
    
    # Create snapshots from AWS data
    print("Creating snapshots from AWS data:")
    for aws_snapshot in aws_snapshots:
        snapshot = SnapshotInfo.from_aws_snapshot(
            aws_snapshot, 
            landing_zone="Production", 
            account_id="123456789012"
        )
        print(f"  {snapshot.snapshot_id}: {snapshot.display_name} ({snapshot.size_gb} GB)")
    
    # Create collection using factory function
    collection = create_snapshot_collection(
        aws_snapshots,
        landing_zone="Production",
        account_id="123456789012",
        metadata={"source": "aws_api", "region": "us-east-1"}
    )
    
    print(f"\nCreated collection with {len(collection)} snapshots")
    
    # Filter old snapshots using utility function
    old_snapshots = filter_old_snapshots(
        aws_snapshots,
        days_old=7,
        landing_zone="Production",
        account_id="123456789012"
    )
    
    print(f"Found {len(old_snapshots)} old snapshots (>7 days)")
    
    return collection


def example_serialization():
    """Example: Serializing and deserializing snapshot data."""
    print("\n=== Serialization Examples ===")
    
    # Create a snapshot
    snapshot = SnapshotInfo(
        snapshot_id="snap-serialize-test",
        landing_zone="Test",
        account_id="123456789012",
        volume_id="vol-serialize-test",
        volume_size=50,
        state=SnapshotState.COMPLETED,
        description="Test snapshot for serialization",
        start_time=datetime.now() - timedelta(days=1),
        encrypted=True,
        tags={"Name": "test-snapshot", "Purpose": "serialization-test"}
    )
    
    # Convert to dictionary
    snapshot_dict = snapshot.to_dict()
    print("Snapshot as dictionary:")
    print(json.dumps(snapshot_dict, indent=2, default=str))
    
    # Create from dictionary
    restored_snapshot = SnapshotInfo.from_dict(snapshot_dict)
    print(f"\nRestored snapshot: {restored_snapshot.snapshot_id}")
    print(f"Original age: {snapshot.age_days} days")
    print(f"Restored age: {restored_snapshot.age_days} days")
    
    # Create collection and save to files
    collection = SnapshotCollection(
        snapshots=[snapshot, restored_snapshot],
        metadata={"test": "serialization", "timestamp": datetime.now().isoformat()}
    )
    
    # Save to JSON
    json_file = Path("/tmp/snapshots.json")
    collection.save_to_json(json_file)
    print(f"\nSaved collection to {json_file}")
    
    # Save to CSV
    csv_file = Path("/tmp/snapshots.csv")
    collection.save_to_csv(csv_file)
    print(f"Saved collection to {csv_file}")
    
    # Load from JSON
    loaded_collection = SnapshotCollection.load_from_json(json_file)
    print(f"\nLoaded collection with {len(loaded_collection)} snapshots")
    print(f"Metadata: {loaded_collection.metadata}")
    
    return collection


def example_cost_analysis():
    """Example: Cost analysis and reporting."""
    print("\n=== Cost Analysis ===")
    
    # Create snapshots with different sizes
    snapshots = [
        SnapshotInfo(
            snapshot_id=f"snap-cost-{i}",
            landing_zone="Production",
            account_id="123456789012",
            volume_id=f"vol-cost-{i}",
            volume_size=size,
            state=SnapshotState.COMPLETED,
            description=f"Cost analysis snapshot {i}",
            start_time=datetime.now() - timedelta(days=i),
            encrypted=True,
            tags={"Name": f"cost-snapshot-{i}", "CostCenter": "IT"}
        )
        for i, size in enumerate([10, 50, 100, 200, 500], 1)
    ]
    
    collection = SnapshotCollection(snapshots=snapshots)
    
    print(f"Total snapshots: {len(collection)}")
    print(f"Total storage: {collection.total_size_gb} GB")
    print(f"Estimated monthly cost: ${collection.estimated_monthly_cost:.2f}")
    
    # Cost breakdown by size categories
    small_snapshots = collection.filter_by_size(max_gb=50)
    medium_snapshots = collection.filter_by_size(min_gb=51, max_gb=200)
    large_snapshots = collection.filter_by_size(min_gb=201)
    
    print("\nCost breakdown by size:")
    print(f"  Small (<=50 GB): {len(small_snapshots)} snapshots, ${small_snapshots.estimated_monthly_cost:.2f}/month")
    print(f"  Medium (51-200 GB): {len(medium_snapshots)} snapshots, ${medium_snapshots.estimated_monthly_cost:.2f}/month")
    print(f"  Large (>200 GB): {len(large_snapshots)} snapshots, ${large_snapshots.estimated_monthly_cost:.2f}/month")
    
    # Old snapshots cost analysis
    old_snapshots = collection.get_old_snapshots(30)
    if old_snapshots:
        print(f"\nOld snapshots (>30 days): {len(old_snapshots)} snapshots")
        print(f"Potential savings from cleanup: ${old_snapshots.estimated_monthly_cost:.2f}/month")
    
    return collection


def main():
    """Run all examples."""
    print("AWS EBS Snapshot Models Usage Examples")
    print("=" * 50)
    
    try:
        # Run examples
        example_basic_snapshot_info()
        example_detailed_snapshot_info()
        example_snapshot_collection()
        example_aws_integration()
        example_serialization()
        example_cost_analysis()
        
        print("\n=== All Examples Completed Successfully ===")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()