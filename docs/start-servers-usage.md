# Server Management Job Usage

The `start-servers` and `stop-servers` commands allow you to start or stop EC2 instances across AWS landing zones with flexible filtering options.

## Basic Usage

### Starting Servers

```bash
# Start a specific server by name
aws-ops start-servers --server-name "my-server" --test --dry-run

# Start all stopped servers in a landing zone
aws-ops start-servers --start-all --test --dry-run

# Start all stopped servers in a landing zone
aws-ops start-servers --start-all --test --dry-run

# Start servers in specific landing zones
aws-ops start-servers --landing-zones "zone1:account1" --landing-zones "zone2:account2" --start-all
```

### Stopping Servers

```bash
# Stop a specific server by name
aws-ops stop-servers --server-name "my-server" --test --dry-run

# Stop all running servers in a landing zone
aws-ops stop-servers --stop-all --test --dry-run

# Stop all running servers in a landing zone
aws-ops stop-servers --stop-all --test --dry-run

# Stop servers in specific landing zones
aws-ops stop-servers --landing-zones "zone1:account1" --landing-zones "zone2:account2" --stop-all
```

## Command Options

### start-servers Options

| Option                 | Description                                                    |
| ---------------------- | -------------------------------------------------------------- |
| `--environment TEXT`   | Environment to target                                          |
| `--landing-zones TEXT` | Specific landing zones to process (can be used multiple times) |
| `-r, --region TEXT`    | AWS region to operate in (default: ap-southeast-2)             |
| `--server-name TEXT`   | Specific server name to start                                  |
| `--start-all`          | Start all stopped servers in the landing zone(s)               |

| `--dry-run` | Preview operations without executing them |
| `--test` | Use test account configuration from settings.yaml (overrides --landing-zones) |

### stop-servers Options

| Option                 | Description                                                    |
| ---------------------- | -------------------------------------------------------------- |
| `--environment TEXT`   | Environment to target                                          |
| `--landing-zones TEXT` | Specific landing zones to process (can be used multiple times) |
| `-r, --region TEXT`    | AWS region to operate in (default: ap-southeast-2)             |
| `--server-name TEXT`   | Specific server name to stop                                   |
| `--stop-all`           | Stop all running servers in the landing zone(s)                |

| `--dry-run` | Preview operations without executing them |
| `--test` | Use test account configuration from settings.yaml (overrides --landing-zones) |

## Usage Examples

### 1. Test Mode with Dry Run

```bash
# Preview what servers would be started in test environment
aws-ops start-servers --test --start-all --dry-run

# Preview what servers would be stopped in test environment
aws-ops stop-servers --test --stop-all --dry-run
```

### 2. Start/Stop Specific Server

```bash
# Start a specific server by name
aws-ops start-servers --server-name "web-server-01" --test

# Stop a specific server by name
aws-ops stop-servers --server-name "web-server-01" --test
```

### 3. Start/Stop All Servers in Landing Zone

```bash
# Start all stopped servers in test environment
aws-ops start-servers --start-all --test

# Stop all running servers in test environment
aws-ops stop-servers --stop-all --test
```

### 4. Production Usage

```bash
# Start all servers in specific landing zones
aws-ops start-servers --landing-zones "prod-zone:123456789" --start-all

# Stop all servers in specific landing zones
aws-ops stop-servers --landing-zones "prod-zone:123456789" --stop-all
```

## Safety Features

- **Dry Run Mode**: Use `--dry-run` to preview operations without executing them
- **State-Aware Operations**:
  - `start-servers` only targets instances in 'stopped' state
  - `stop-servers` only targets instances in 'running' state
- **Flexible Filtering**: Multiple filtering options to target specific servers
- **Error Handling**: Comprehensive error reporting and logging
- **Test Mode**: Safe testing with `--test` flag using settings.yaml configuration
- **Backward Compatibility**: Existing scripts continue to work unchanged

## Output

Both commands provide detailed output including:

- Number of zones processed
- Servers started/stopped successfully
- Dry-run operations (when using --dry-run)
- Error count and details
- Operation summary with action-specific metrics

## Notes

- The `--test` flag overrides `--landing-zones` and uses configuration from settings.yaml
- Use `--dry-run` for safe testing before actual operations
- `start-servers` only targets stopped EC2 instances
- `stop-servers` only targets running EC2 instances
- All operations are logged for audit purposes
- Both commands use the same underlying job class for consistency
