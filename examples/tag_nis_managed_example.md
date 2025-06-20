# NIS Managed Tagging Feature

This document demonstrates how to use the new `--tag-nis-managed` feature in the `scan_tagged_resources.py` script.

## Overview

The `--tag-nis-managed` flag automatically adds the tag `nis_managed=true` to all resources that match the scanning criteria.

## Usage Examples

### Test Mode with Tagging

```bash
# Scan test account and tag matched resources
python3 jobs/scan_tagged_resources.py --test --tag-nis-managed

# With debug logging to see detailed tagging process
python3 jobs/scan_tagged_resources.py --test --tag-nis-managed --debug
```

### Production Mode with Tagging

```bash
# Scan specific landing zones and tag matched resources
python3 jobs/scan_tagged_resources.py --landing-zones cmsnonprod appanonprod --tag-nis-managed

# Scan all nonprod zones and tag matched resources
python3 jobs/scan_tagged_resources.py --environment nonprod --tag-nis-managed
```

## Features

- **Smart Duplicate Detection**: The script checks if `nis_managed` tag already exists and skips re-tagging
- **Error Handling**: Comprehensive error handling with detailed logging for failed tagging operations
- **Statistics Tracking**: Reports success/failure counts for tagging operations
- **Batch Processing**: Efficiently tags resources across multiple landing zones

## Output

When using `--tag-nis-managed`, you'll see additional logging:

```plain
🏷️ Starting to tag 5 resources with nis_managed=true
🏷️ Tagging completed - Success: 5, Failed: 0
🏷️ Tagging results - Success: 5, Failed: 0
```

## Safety Features

1. **Idempotent**: Running the command multiple times won't create duplicate tags
2. **Error Recovery**: Individual tagging failures don't stop the entire process
3. **Detailed Logging**: All tagging operations are logged for audit purposes
4. **Dry Run**: You can run without `--tag-nis-managed` to see what would be tagged first
