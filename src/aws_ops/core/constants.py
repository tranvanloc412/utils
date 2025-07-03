#!/usr/bin/env python3
"""Core constants for AWS operations."""

# Server Management Constants
CMS_MANAGED = "CMS"
MANAGED_BY_KEY = "managed_by"

# Report Format Constants
REPORT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
SCAN_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# AWS Service Constants
DEFAULT_AWS_REGION = "ap-southeast-2"
MAX_INSTANCES_PER_SCAN = 1000

# File and Directory Constants
DEFAULT_REPORT_EXTENSION = ".csv"
LOG_ROTATION_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
