# Start Servers Usage

The AWS Ops toolkit provides server management commands for starting and stopping EC2 instances.

## Basic Usage

### Starting Servers

```bash
# Start servers by name pattern
aws-ops start-servers --name "web-*" --landing-zones "prod:123456789"

# Dry run first (recommended)
aws-ops start-servers --name "web-*" --landing-zones "prod:123456789" --dry-run

# Force without confirmation (for automation)
aws-ops start-servers --name "web-*" --landing-zones "prod:123456789" --force
```

### Stopping Servers

```bash
# Stop servers by name pattern
aws-ops stop-servers --name "web-*" --landing-zones "prod:123456789"

# Dry run first (recommended)
aws-ops stop-servers --name "web-*" --landing-zones "prod:123456789" --dry-run

# Force without confirmation (for automation)
aws-ops stop-servers --name "web-*" --landing-zones "prod:123456789" --force
```

## Command Options

### Common Options

| Option | Description |
|--------|-------------|
| `--name TEXT` | Server name pattern (supports wildcards) |
| `--landing-zones TEXT` | Landing zones in format `env:account_id` |
| `--dry-run` | Preview changes without executing |
| `--verbose` | Enable verbose output |
| `--force` | Skip confirmation prompts |

### Landing Zone Format

Specify landing zones using the format `environment:account_id`:

```bash
# Single landing zone
--landing-zones "prod:123456789"

# Multiple landing zones
--landing-zones "prod:123456789,staging:987654321"
```

## Safety Features

### Dry Run Mode

Always test with `--dry-run` first:

```bash
aws-ops start-servers --name "web-*" --landing-zones "prod:123456789" --dry-run
```

### Confirmation Prompts

By default, the tool will ask for confirmation before making changes:

```
Start servers matching 'web-*'? [y/N]: y
```

### Force Mode

For automation, use `--force` to skip confirmations:

```bash
aws-ops start-servers --name "web-*" --landing-zones "prod:123456789" --force
```

## Examples

### Development Workflow

```bash
# 1. First, scan to see what servers exist
aws-ops scan-servers --landing-zones "dev:123456789"

# 2. Test the operation with dry-run
aws-ops start-servers --name "app-*" --landing-zones "dev:123456789" --dry-run

# 3. Execute the operation
aws-ops start-servers --name "app-*" --landing-zones "dev:123456789"
```

### Production Workflow

```bash
# Always use dry-run first in production
aws-ops stop-servers --name "batch-*" --landing-zones "prod:123456789" --dry-run

# Execute with verbose logging
aws-ops stop-servers --name "batch-*" --landing-zones "prod:123456789" --verbose
```

### Automation Scripts

```bash
#!/bin/bash
# Automated server management script

set -e

# Stop batch servers for maintenance
aws-ops stop-servers \
  --name "batch-*" \
  --landing-zones "prod:123456789" \
  --force \
  --verbose

# Perform maintenance here...
sleep 300

# Start batch servers
aws-ops start-servers \
  --name "batch-*" \
  --landing-zones "prod:123456789" \
  --force \
  --verbose
```

## Error Handling

### Common Errors

1. **Invalid server name pattern**
   ```
   Error: Invalid server name pattern
   ```
   - Check that the name pattern is valid
   - Ensure it's not empty and within length limits

2. **Permission denied**
   ```
   Error starting servers: Access denied
   ```
   - Verify AWS credentials are configured
   - Check IAM permissions for EC2 operations

3. **Invalid landing zone format**
   ```
   Error: Invalid landing zone format
   ```
   - Use format `environment:account_id`
   - Separate multiple zones with commas

### Troubleshooting

```bash
# Enable verbose logging for debugging
aws-ops start-servers --name "web-*" --landing-zones "prod:123456789" --verbose

# Check AWS credentials
aws sts get-caller-identity

# Verify configuration
python -c "from aws_ops.utils.config import ConfigManager; print(ConfigManager().config)"
```
