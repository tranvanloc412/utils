# Supported AWS Services

This document lists all AWS services supported by the `manage_resource_tags.py` script, including their ARN formats and tagging rules.

## Service Mappings

| Service Key | AWS Service | Resource Type | ARN Format |
|-------------|-------------|---------------|------------|
| `ec2` | EC2 Instances | `ec2:instance` | `arn:aws:ec2:region:account:instance/instance-id` |
| `ebs` | EBS Volumes | `ec2:volume` | `arn:aws:ec2:region:account:volume/volume-id` |
| `asg` | Auto Scaling Groups | `autoscaling:autoScalingGroup` | `arn:aws:autoscaling:region:account:autoScalingGroup:uuid:autoScalingGroupName/name` |
| `s3` | S3 Buckets | `s3` | `arn:aws:s3:::bucket-name` |
| `sns` | SNS Topics | `sns` | `arn:aws:sns:region:account:topic-name` |
| `sqs` | SQS Queues | `sqs` | `arn:aws:sqs:region:account:queue-name` |
| `dynamodb` | DynamoDB Tables | `dynamodb:table` | `arn:aws:dynamodb:region:account:table/table-name` |
| `cloudwatch` | CloudWatch Alarms | `cloudwatch:alarm` | `arn:aws:cloudwatch:region:account:alarm:alarm-name` |
| `events` | EventBridge Rules | `events:rule` | `arn:aws:events:region:account:rule/rule-name` |
| `lb` | Load Balancers | `elasticloadbalancing:loadbalancer` | `arn:aws:elasticloadbalancing:region:account:loadbalancer/type/name/id` |
| `tg` | Target Groups | `elasticloadbalancing:targetgroup` | `arn:aws:elasticloadbalancing:region:account:targetgroup/name/id` |
| `efs` | EFS File Systems | `elasticfilesystem:file-system` | `arn:aws:elasticfilesystem:region:account:file-system/fs-id` |
| `fsx` | FSx Volumes | `fsx:volume` | `arn:aws:fsx:region:account:volume/volume-id` |
| `sg` | Security Groups | `ec2:security-group` | `arn:aws:ec2:region:account:security-group/sg-id` |
| `kms` | KMS Keys | `kms:key` | `arn:aws:kms:region:account:key/key-id` |
| `rds` | RDS Databases | `rds:db` | `arn:aws:rds:region:account:db:db-instance-id` |
| `lambda` | Lambda Functions | `lambda:function` | `arn:aws:lambda:region:account:function:function-name` |

## ARN Parsing Logic

The script handles different ARN formats based on the service:

### Simplified ARN Formats
These services have non-standard ARN formats:
- **S3**: `arn:aws:s3:::bucket-name` (no region/account)
- **SNS**: `arn:aws:sns:region:account:topic-name` (direct topic name)
- **SQS**: `arn:aws:sqs:region:account:queue-name` (direct queue name)

### Service-Specific ARN Formats
These services have specific resource type patterns:
- **DynamoDB**: `arn:aws:dynamodb:region:account:table/table-name`
- **CloudWatch**: `arn:aws:cloudwatch:region:account:alarm:alarm-name`
- **EventBridge**: `arn:aws:events:region:account:rule/rule-name`

### Standard ARN Formats
Most other services follow the standard pattern:
`arn:aws:service:region:account:resource-type/resource-id`

## Default Tagging Rules

### Exclude Rules by Service

| Service | Excluded Tag Presets | Description |
|---------|---------------------|-------------|
| `ec2` | `managed_by_cms`, `asg` | Excludes CMS-managed and ASG resources |
| `ebs` | `asg`, `nabserv` | Excludes ASG and NAB service resources |
| `asg` | `nabserv` | Excludes NAB service resources |
| `s3` | `nabserv` | Excludes NAB service resources |
| `lb`, `tg`, `efs` | `nef2` | Excludes NEF2 resources |
| `sg` | `nef2`, `cps`, `nabserv` | Excludes NEF2, CPS, and NAB service resources |
| `kms` | `nef2`, `wiz`, `nabserv` | Excludes NEF2, Wiz, and NAB service resources |
| `sns`, `sqs`, `dynamodb`, `events`, `lambda` | `nef2`, `cps` | Excludes NEF2 and CPS resources |
| `cloudwatch` | `nef2`, `nabserv` | Excludes NEF2 and NAB service resources |
| `rds`, `fsx` | None | No default exclusions |

## Usage Examples

### Scan specific services
```bash
# Scan only DynamoDB tables
python3 manage_resource_tags.py --include dynamodb

# Scan CloudWatch alarms and EventBridge rules
python3 manage_resource_tags.py --include cloudwatch,events

# Scan all supported services
python3 manage_resource_tags.py
```

### Test mode
```bash
# Test DynamoDB scanning
python3 manage_resource_tags.py --test --include dynamodb --debug
```

## Adding New Services

To add support for a new AWS service:

1. **Add to SERVICES mapping**:
   ```python
   "service_key": "service:resource-type"
   ```

2. **Update ARN parsing logic** (if needed):
   Add special handling in the ARN parsing section for non-standard formats.

3. **Add to SERVICE_TAG_RULES**:
   ```python
   "service_key": {"exclude": [relevant_presets]}
   ```

4. **Test the implementation**:
   ```bash
   python3 manage_resource_tags.py --test --include service_key --debug
   ```