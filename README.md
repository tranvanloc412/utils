# AWS Operations Utility Suite

A comprehensive Python project for managing AWS operations through various utility scripts. This project provides a unified command-line interface to run different AWS-related jobs including landing zone management, snapshot analysis, and approval workflows.

## Quick Start

### 1. Setup

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Usage

#### List Old Snapshots

Run the script to list EC2 snapshots older than 30 days:

```bash
python3 jobs/list_old_snapshots.py --landing-zones cmsnonprod appnonprod
```

Or list all nonprod landing zones:

```bash
python3 jobs/list_old_snapshots.py --environment nonprod
```

#### Delete Old AMIs and Snapshots

Run the script to delete EC2 AMIs and snapshots older than 30 days:

```bash
python3 jobs/delete_old_backups.py --landing-zones cmsnonprod appnonprod
```

```bash
python3 jobs/delete_old_backups.py --environment nonprod
```
