# Enhanced Logging Documentation

## Overview

The AWS Operations toolkit now includes enterprise-grade logging capabilities designed for banking and financial services environments. This enhanced logging system provides comprehensive audit trails, structured logging, correlation tracking, and compliance-ready features.

## Key Features

### 1. Dual Logging Strategy

- **Console Output**: Real-time feedback for operators
- **File Logging**: Persistent audit trails with rotation
- **Operations Log**: Centralized operation tracking in `operations.log`
- **Job-Specific Logs**: Individual logs per job type (e.g., `start_servers.log`, `stop_servers.log`)

### 2. Structured Logging (JSON)

- Enable with `logging.structured: true` in `settings.yml`
- Machine-readable format for log aggregation systems
- Includes metadata: correlation_id, account_id, operation, timestamps
- Compatible with ELK stack, Splunk, CloudWatch Insights

### 3. Correlation ID Tracking

- Unique 8-character correlation ID per operation
- Tracks requests across multiple AWS accounts and services
- Enables end-to-end operation tracing
- Facilitates troubleshooting and audit compliance

### 4. Log Rotation and Retention

- Automatic log rotation (default: 10MB per file)
- Configurable backup count (default: 5 files)
- Prevents disk space issues in production
- Maintains historical data for compliance

## Configuration

### Basic Configuration (`configs/settings.yml`)

```yaml
logging:
  level: "INFO" # Log level: DEBUG, INFO, WARN, ERROR
  console: true # Enable console output
  file: true # Enable file logging
  path: "logs" # Log directory
  result_logging: true # Log operation results
  verbose_console: false # Detailed console output
  structured: false # Enable JSON structured logging
  rotation:
    enabled: true # Enable log rotation
    max_bytes: 10485760 # 10MB per log file
    backup_count: 5 # Keep 5 backup files
```

### Enterprise Configuration (Recommended)

```yaml
logging:
  level: "INFO"
  console: true
  file: true
  path: "logs"
  result_logging: true
  verbose_console: false
  structured: true # Enable for enterprise environments
  rotation:
    enabled: true
    max_bytes: 52428800 # 50MB for high-volume environments
    backup_count: 10 # Extended retention
```

## Log Formats

### Standard Format

```bash
2024-01-15 10:30:45,123 - INFO - aws_ops.jobs.start_servers - [abc12345] Creating AWS session for account cmsnonprod (954976297051) with role HIPCMSProvisionSpokeRole in ap-southeast-2
2024-01-15 10:30:46,456 - INFO - aws_ops.jobs.start_servers - [abc12345] Starting 3 instances: ['i-1234567890abcdef0', 'i-0987654321fedcba0', 'i-abcdef1234567890']
```

### Structured Format (JSON)

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "aws_ops.jobs.start_servers",
  "message": "Creating AWS session for account cmsnonprod (954976297051) with role HIPCMSProvisionSpokeRole",
  "correlation_id": "abc12345",
  "account_id": "954976297051",
  "account_name": "cmsnonprod",
  "role_name": "HIPCMSProvisionSpokeRole",
  "operation": "start_servers",
  "region": "ap-southeast-2"
}
```

## Log Files

### Operations Log (`logs/operations.log`)

Centralized log for all operations with high-level summaries:

- Operation completion status
- Success rates and execution times
- Error summaries
- File save operations

### Job-Specific Logs

- `logs/start_servers.log` - EC2 instance start operations
- `logs/stop_servers.log` - EC2 instance stop operations
- `logs/[job_name].log` - Individual job execution details

## Enterprise Benefits

### 1. Compliance and Audit

- **SOX Compliance**: Complete audit trail of all operations
- **PCI-DSS**: Secure logging without sensitive data exposure
- **Change Tracking**: Detailed before/after state logging
- **User Attribution**: Operation tracking with correlation IDs

### 2. Monitoring and Alerting

- **Structured Data**: Easy integration with monitoring systems
- **Error Detection**: Automated error pattern recognition
- **Performance Metrics**: Execution time and success rate tracking
- **Capacity Planning**: Resource usage and operation frequency data

### 3. Troubleshooting

- **Correlation Tracking**: Follow operations across multiple systems
- **Detailed Context**: Account, region, and resource information
- **State Transitions**: Before/after instance states
- **Error Context**: Comprehensive error information with stack traces

### 4. Security

- **No Sensitive Data**: Credentials and secrets are never logged
- **Access Patterns**: Track unusual access or operation patterns
- **Role Usage**: Monitor role assumption and usage
- **Geographic Tracking**: Region-based operation monitoring

## Integration Examples

### CloudWatch Integration

```bash
# Send structured logs to CloudWatch
aws logs create-log-group --log-group-name /aws/ops/structured
aws logs put-log-events --log-group-name /aws/ops/structured --log-stream-name operations --log-events file://structured.json
```

### Splunk Integration

```bash
# Configure Splunk Universal Forwarder
[monitor:///path/to/logs/*.log]
index = aws_ops
sourcetype = aws_ops_json
```

### ELK Stack Integration

```yaml
# Filebeat configuration
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /path/to/logs/*.log
    json.keys_under_root: true
    json.add_error_key: true
```

## Best Practices

### 1. Production Deployment

- Enable structured logging (`structured: true`)
- Set appropriate log levels (INFO for production)
- Configure log rotation for disk management
- Implement centralized log collection

### 2. Security Considerations

- Never log credentials or sensitive data
- Implement log access controls
- Consider log encryption at rest
- Regular log retention policy reviews

### 3. Performance Optimization

- Use appropriate log levels to control volume
- Configure rotation to prevent disk issues
- Consider asynchronous logging for high-volume environments
- Monitor log processing performance

### 4. Monitoring Setup

- Set up alerts for ERROR level messages
- Monitor correlation ID patterns for anomalies
- Track operation success rates and execution times
- Implement log-based dashboards for operational visibility

## Troubleshooting

### Common Issues

1. **Log Files Not Created**

   - Check directory permissions for `logs/` folder
   - Verify `logging.file: true` in settings
   - Ensure sufficient disk space

2. **Structured Logging Not Working**

   - Verify `logging.structured: true` in settings
   - Check JSON format validity
   - Ensure logger setup includes `json_format=True`

3. **Missing Correlation IDs**

   - Verify BaseJob initialization
   - Check correlation ID propagation in decorators
   - Ensure proper job inheritance

4. **Log Rotation Issues**
   - Check file permissions
   - Verify rotation configuration
   - Monitor disk space usage

### Debug Commands

```bash
# Check log file permissions
ls -la logs/

# Monitor log file growth
watch -n 1 'ls -lh logs/'

# Validate JSON structure
jq . logs/operations.log

# Search for correlation ID
grep "abc12345" logs/*.log
```

## Migration Guide

### From Basic to Enhanced Logging

1. **Update Configuration**

   ```yaml
   # Add to settings.yml
   logging:
     structured: true
     rotation:
       enabled: true
       max_bytes: 10485760
       backup_count: 5
   ```

2. **Update Log Processing**

   - Modify log parsing scripts for JSON format
   - Update monitoring dashboards
   - Configure new log aggregation rules

3. **Test and Validate**
   - Run operations in test environment
   - Verify log format and content
   - Test log rotation functionality
   - Validate monitoring integration

This enhanced logging system provides enterprise-grade capabilities while maintaining simplicity for development and testing environments.
