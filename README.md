# AWS Operations Utility Suite

A Python toolkit for managing AWS operations including snapshot cleanup, landing zone management, and approval workflows.

## Requirements

- AWS credentials configured (Jump Viewer or Provision role)

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Available Tools

### delete_old_backups.py

Delete old AMIs and snapshots across landing zones.

```bash
python jobs/delete_old_backups.py --days 31 --dry-run
python jobs/delete_old_backups.py --environment prod --days 45
```

### list_old_snapshots.py

Generate reports of old snapshots.

```bash
python jobs/list_old_snapshots.py --days 30
python jobs/list_old_snapshots.py --environment prod --days 45
```

### review_approved_lzs.py

Review approved landing zones against snapshot reports.

```bash
python jobs/review_approved_lzs.py --approved approved_lzs.csv --report snapshot_report.csv
python jobs/review_approved_lzs.py --approved approved_lzs.csv --report snapshot_report.csv --days 45 --csv
```

## Output

- Console output with progress and summary
- CSV reports saved to `results/` directory
- Detailed logging for audit trails

## Safety Features

- Dry-run mode available for testing
- Comprehensive logging
- Input validation and error handling
