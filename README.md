# AWS Ops - Simplified Version

> Enterprise AWS operations toolkit - streamlined for easier deployment and maintenance

## Overview

AWS Ops provides essential cloud operations capabilities for enterprise environments, with a focus on simplicity and reliability.

### Key Features

- **Server Management**: Start/stop EC2 instances across multiple accounts
- **Backup Operations**: Scan and cleanup old snapshots and AMIs
- **Infrastructure Updates**: Update launch templates with latest AMIs
- **Multi-Account Support**: Operate across landing zones and accounts
- **Safety Features**: Dry-run mode and confirmation prompts
- **Audit Logging**: Track all operations for compliance

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd ops

# Install dependencies
pip install -e .
```

### 2. Configuration

Copy and customize the configuration:

```bash
cp configs/settings.yml.example configs/settings.yml
```

Edit `configs/settings.yml` with your AWS settings:

```yaml
aws:
  region: "your-region"
  roles:
    viewer: "YourViewerRole"
    provision: "YourProvisionRole"
```

### 3. AWS Credentials

Set up AWS credentials using one of these methods:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=ap-southeast-2

# Option 3: IAM roles (recommended for EC2)
# Use instance profiles or assume roles
```

## Usage

### Using CLI

```bash
# Use the CLI
aws-ops --help

# Or use the module directly
python -m aws_ops.cli --help
```

### Common Operations

#### Server Management

```bash
# Scan servers
aws-ops scan-servers --landing-zones prod:123456789

# Start servers (with confirmation)
aws-ops start-servers --name "web-*" --landing-zones prod:123456789

# Stop servers (dry run first)
aws-ops stop-servers --name "web-*" --dry-run
```

#### Backup Operations

```bash
# Scan backup status
aws-ops scan-backups --days 30 --output backup-report.csv

# Cleanup old snapshots (dry run first)
aws-ops cleanup-snapshots --days 90 --dry-run

# Execute cleanup
aws-ops cleanup-snapshots --days 90 --force
```

#### Infrastructure Updates

```bash
# Update launch template AMI
aws-ops update-ami --template "web-template" --dry-run
```

### Safety Features

- **Dry Run**: Use `--dry-run` to preview changes
- **Confirmation**: Interactive prompts for destructive operations
- **Force**: Use `--force` to skip confirmations (automation)
- **Verbose**: Use `--verbose` for detailed output

## Configuration

### Configuration Settings

The `settings.yml` includes essential configurations:

```yaml
# Basic AWS settings
aws:
  region: "ap-southeast-2"
  roles:
    viewer: "ViewerRole"
    provision: "ProvisionRole"

# Security essentials
security:
  require_mfa: true
  audit_logging: true

# Performance limits
performance:
  batch_size: 50
  timeout: 300
  retry_attempts: 3

# Feature flags
features:
  dry_run: true
  confirmation_prompts: true
```

### Environment Variables

```bash
# Override configuration
export AWS_OPS_CONFIG=/path/to/custom/settings.yml
export AWS_OPS_REGION=us-west-2
export AWS_OPS_DRY_RUN=true
```

## Security

### Best Practices

1. **Use IAM Roles**: Prefer IAM roles over access keys
2. **Least Privilege**: Grant minimum required permissions
3. **MFA**: Enable multi-factor authentication
4. **Audit Logs**: Monitor all operations
5. **Dry Run**: Always test with `--dry-run` first

### Required Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:DescribeSnapshots",
        "ec2:DeleteSnapshot",
        "ec2:DescribeLaunchTemplates",
        "ec2:ModifyLaunchTemplate"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **Configuration Error**
   ```bash
   # Check configuration
   python -c "from aws_ops.utils.config import ConfigManager; print(ConfigManager().config)"
   ```

2. **AWS Credentials**
   ```bash
   # Test AWS access
   aws sts get-caller-identity
   ```

3. **Permission Denied**
   - Verify IAM roles and policies
   - Check assume role permissions

4. **Timeout Issues**
   - Increase timeout in configuration
   - Check network connectivity

### Debug Mode

```bash
# Enable verbose logging
aws-ops scan-servers --verbose

# Check logs
tail -f /var/log/aws-ops/aws-ops.log
```

## Migration Guide

If migrating from previous versions:

1. **Configuration**: Update `settings.yml` with new format
2. **CLI**: Use `aws-ops` command or `python -m aws_ops.cli`
3. **Dependencies**: Install with updated Python 3.12+ requirements
4. **Logging**: Updated logging format

### Feature Comparison

| Feature | Status |
|---------|--------|
| Server Management | ✅ |
| Backup Operations | ✅ |
| AMI Updates | ✅ |
| Audit Logging | ✅ |
| Multi-Account Support | ✅ |
| Enterprise Config | ✅ |
| Safety Features | ✅ |
| Compliance Features | ✅ |

## Support

### Getting Help

```bash
# Command help
aws-ops --help
aws-ops scan-servers --help

# Version info
aws-ops --version
```

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## License

Enterprise License - See LICENSE file for details.
