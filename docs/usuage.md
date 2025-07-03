# Default CMS filtering (new behavior)

aws-ops scan-backups --days 7 --dry-run
aws-ops scan-servers --dry-run

# Explicit CMS filtering

aws-ops scan-backups --days 7 --managed-by cms --dry-run
aws-ops scan-servers --managed-by cms --dry-run

# All resources (no filtering)

aws-ops scan-backups --days 7 --managed-by all --dry-run
aws-ops scan-servers --managed-by all --dry-run
