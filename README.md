# AWS Ops

A Python toolkit for managing AWS operations including snapshot cleanup, landing zone management, and approval workflows.

## Requirements

- Python 3.8 or higher
- AWS credentials configured (Jump Viewer or Provision role)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd aws-ops

# Run the installation script
./scripts/install.sh
```

The installation script will:

- Create a virtual environment automatically
- Install the aws-ops package and dependencies
- Optionally install development dependencies
- Verify the installation

After installation, activate the virtual environment:

```bash
source venv/bin/activate
```

## Available Tools

AWS Ops provides multiple ways to run commands, from simple unified CLI to individual scripts:

### 🚀 Unified CLI (Recommended)

#### Option 1: Simple Wrapper (No Installation Required)

```bash
# macOS/Linux
./aws-ops scan-servers --environment prod
./aws-ops list-snapshots --days 30
./aws-ops delete-backups --days 45 --dry-run

# Windows
aws-ops scan-servers --environment prod
aws-ops list-snapshots --days 30
aws-ops delete-backups --days 45 --dry-run
```

#### Option 2: Python CLI (No Installation Required)

```bash
python3 aws_ops.py scan-servers --environment prod
python3 aws_ops.py list-snapshots --days 30
python3 aws_ops.py delete-backups --days 45 --dry-run
```

#### Option 3: Console Scripts (After Installation)

```bash
# Available after pip install -e .
aws-ops scan-servers --environment prod
awsops list-snapshots --days 30  # Short alias

# Legacy individual commands still work
scan-windows-servers --help
list-old-snapshots --days 30
```

### 📋 Traditional Methods

#### Module Execution

```bash
# Run from project root
python -m jobs.delete_old_backups --days 31 --dry-run
python -m jobs.list_old_snapshots --days 30
python -m jobs.scan_windows_servers --environment prod
```

#### Direct Script Execution

```bash
# After installation or with PYTHONPATH
python jobs/delete_old_backups.py --days 31 --dry-run
python jobs/list_old_snapshots.py --environment prod --days 45
python jobs/review_approved_lzs.py --approved approved_lzs.csv --report snapshot_report.csv
```

### 📖 Command Reference

| Command          | Description                                        | Example                                          |
| ---------------- | -------------------------------------------------- | ------------------------------------------------ |
| `scan-servers`   | Scan Windows servers across landing zones          | `./aws-ops scan-servers --environment prod`      |
| `list-snapshots` | Generate reports of old snapshots with CSV output  | `./aws-ops list-snapshots --days 30 --csv`       |
| `delete-backups` | Delete old AMIs and snapshots across landing zones | `./aws-ops delete-backups --days 45 --dry-run`   |
| `run-ssm`        | Execute SSM commands across multiple landing zones | `./aws-ops run-ssm --command "systemctl status"` |
| `manage-tags`    | Manage resource tags across AWS                    | `./aws-ops manage-tags --action add --key Env`   |
| `review-lzs`     | Review approved landing zones against reports      | `./aws-ops review-lzs --approved lzs.csv`        |

### 🆘 Getting Help

```bash
# General help
./aws-ops
./aws-ops --help

# Command-specific help
./aws-ops scan-servers --help
./aws-ops list-snapshots --help
./aws-ops delete-backups --help
```

## Utilities and Examples

### ZoneProcessor Utility

Standardized utility for processing AWS landing zones with built-in error handling, logging, and result aggregation.

```bash
# See examples
python examples/zone_processor_example.py

# Documentation
cat utils/README_zone_processor.md
```

### ConfigManager

Simplified configuration management with environment variable overrides and dot notation access.

```bash
# See examples
python examples/config_manager_example.py

# Documentation
cat README_config_manager.md
```

### Package Setup

Learn about avoiding sys.path manipulation and proper Python packaging:

```bash
cat README_package_setup.md
```

## Development

### Code Quality Tools (if installed with dev dependencies)

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .

# Run tests
pytest tests/
```

### Project Structure

```plain
aws-ops/
├── src/
│   └── aws_ops/       # Main package
│       ├── cli/       # CLI interface
│       ├── core/      # Core business logic
│       ├── jobs/      # Job implementations
│       └── utils/     # Utilities
├── tests/             # Test suite
├── docs/              # Documentation
├── scripts/           # Installation and utility scripts
└── pyproject.toml     # Modern Python packaging
```

## Output

- Console output with progress and summary
- CSV reports saved to `results/` directory
- Detailed logging for audit trails

## Safety Features

- Dry-run mode available for testing
- Comprehensive logging
- Input validation and error handling
