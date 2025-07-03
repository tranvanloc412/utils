"""Simplified decorator patterns for AWS operations."""

import click
import importlib
from functools import wraps
from typing import Any, Callable, Optional, Type

from aws_ops.core.processors.zone_processor import ZoneProcessor
from aws_ops.utils.config import ConfigManager
from aws_ops.utils.logger import setup_logger
from aws_ops.jobs.base import BaseJob
from aws_ops.utils.exceptions import CLIError

# Centralized job registry for eliminating redundant mapping logic
JOB_REGISTRY = {
    "server": {
        "scan": "aws_ops.jobs.scan_servers.ScanServers",
        "start": "aws_ops.jobs.start_servers.StartServersJob",
        "stop": "aws_ops.jobs.stop_servers.StopServersJob",
    },
    "backup": {
        "scan": "aws_ops.jobs.scan_backups.ScanBackups",
        "cleanup": "aws_ops.jobs.cleanup_snapshots.CleanupSnapshotsJob",
    },
    "ami": {
        "create": "aws_ops.jobs.create_ami.CreateAMIJob",
        "update": "aws_ops.jobs.update_ami.UpdateAMIJob",
    },
}


def get_job_class(operation_type: str, func_name: str) -> Type[BaseJob]:
    """Dynamically resolve job class based on operation type and function name.

    Args:
        operation_type: Type of operation (server, backup, ami)
        func_name: Function name to determine specific job

    Returns:
        Job class for the operation

    Raises:
        ValueError: If operation type or function name is not recognized
    """
    registry = JOB_REGISTRY.get(operation_type, {})

    for keyword, job_path in registry.items():
        if keyword in func_name:
            module_path, class_name = job_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)

    raise ValueError(f"Unknown {operation_type} operation: {func_name}")


def _get_zone_name(zone) -> str:
    """Extract zone name for display purposes.

    Args:
        zone: Zone identifier (string or dict)

    Returns:
        str: Zone name for display
    """
    if isinstance(zone, dict):
        return zone.get("name", zone.get("account_id", str(zone)))
    return str(zone)


def handle_operation_error(operation_name: str, error: Exception) -> None:
    """Centralized error handling for operations.

    Args:
        operation_name: Name of the operation that failed
        error: Exception that occurred
    """
    error_msg = f"Error in {operation_name}: {str(error)}"
    click.echo(error_msg, err=True)

    # Add structured logging for enterprise environments
    logger = setup_logger("aws_ops.errors")
    logger.error(
        error_msg,
        extra={"operation": operation_name, "error_type": type(error).__name__},
    )


def handle_output(
    results,
    output_path: Optional[str] = None,
    output_handler: Optional[Callable] = None,
    correlation_id: Optional[str] = None,
):
    """Handle operation output with multiple formats and enhanced logging."""
    # Setup enhanced logger with structured logging
    logger = setup_logger(
        "aws_ops.output",
        "operations.log",
        # Use default
    )

    # Enhanced logging with correlation ID and structured data
    if hasattr(results, "processed_zones") and hasattr(results, "success_rate"):
        log_data = {
            "operation_type": "zone_operation",
            "processed_zones": results.processed_zones,
            "total_zones": results.total_zones,
            "success_rate": round(results.success_rate, 1),
            "execution_time": round(results.execution_time, 2),
            "correlation_id": correlation_id,
        }

        logger.info(
            f"[{correlation_id or 'N/A'}] Operation completed: {results.processed_zones}/{results.total_zones} zones processed ({results.success_rate:.1f}% success rate) in {results.execution_time:.2f}s"
        )

        # Log successful and failed zones for better visibility
        if hasattr(results, "failed_zones") and results.failed_zones:
            successful_zones = [
                zone
                for zone in getattr(results, "metadata", {}).get("all_zones", [])
                if zone not in results.failed_zones
            ]
            if successful_zones:
                successful_zone_names = [
                    _get_zone_name(zone) for zone in successful_zones
                ]
                logger.info(
                    f"[{correlation_id or 'N/A'}] Successful zones ({len(successful_zones)}): {', '.join(successful_zone_names)}"
                )
            failed_zone_names = [_get_zone_name(zone) for zone in results.failed_zones]
            logger.info(
                f"[{correlation_id or 'N/A'}] Failed zones ({len(results.failed_zones)}): {', '.join(failed_zone_names)}"
            )
        elif hasattr(results, "failed_zones"):
            # All zones were successful
            all_zones = getattr(results, "metadata", {}).get("all_zones", [])
            if all_zones:
                all_zone_names = [_get_zone_name(zone) for zone in all_zones]
                logger.info(
                    f"[{correlation_id or 'N/A'}] All zones successful ({len(all_zones)}): {', '.join(all_zone_names)}"
                )

        if results.errors:
            logger.error(
                f"[{correlation_id or 'N/A'}] Operation errors: {results.errors}"
            )
    else:
        log_data = {
            "operation_type": "generic_operation",
            "result_type": type(results).__name__,
            "correlation_id": correlation_id,
        }

        logger.info(
            f"[{correlation_id or 'N/A'}] Operation completed: {type(results).__name__}"
        )

    # Handle output
    if output_handler:
        output_handler(results, output_path)
    elif output_path:
        with open(output_path, "w") as f:
            f.write(str(results))
        click.echo(f"Results saved to {output_path}")

        logger.info(f"[{correlation_id or 'N/A'}] Results saved to {output_path}")
    else:
        click.echo(results)


def execute_zone_operation(
    job_class: Type[BaseJob], operation_name: str = "aws_operation", **kwargs
) -> Any:
    """Execute zone-based operation with standardized processing."""
    # Extract zone-related parameters
    landing_zones = kwargs.pop("landing_zones", None)
    output = kwargs.pop("output", None)
    output_handler = kwargs.pop("output_handler", None)

    # Setup configuration
    config = ConfigManager()

    # Get zones from config and filter if landing_zones specified
    zones = config.get_zones() if hasattr(config, "get_zones") else []

    # Filter zones by landing_zones if specified
    if landing_zones:
        from aws_ops.utils.lz import extract_environment_from_zone

        landing_zones_list = [lz.strip() for lz in landing_zones.split(",")]
        zones = [
            zone
            for zone in zones
            if zone.get("name") in landing_zones_list
            or zone.get("environment") in landing_zones_list
        ]

        # Validate that all selected zones belong to the same environment
        if len(zones) > 1:
            environments = set()
            for zone in zones:
                try:
                    env = extract_environment_from_zone(zone.get("name", ""))
                    environments.add(env)
                except Exception:
                    # If we can't extract environment, use the zone name as fallback
                    environments.add(zone.get("environment", zone.get("name", "")))

            if len(environments) > 1:
                zone_names = [zone.get("name", "unknown") for zone in zones]
                raise CLIError(
                    f"Multiple environments detected in selected landing zones: {', '.join(zone_names)}. "
                    f"Environments found: {', '.join(sorted(environments))}. "
                    f"Please select landing zones from only one environment at a time for safety and compliance."
                )

    # Create job instance and processor
    job = job_class(config)
    processor = ZoneProcessor(name=f"{operation_name}_processor")

    # Execute with zone processing
    def process_function(zone_info):
        return job.execute(zone_info, **kwargs)

    # Get correlation ID from job
    correlation_id = getattr(job, "correlation_id", None)

    results = processor.process_zones(
        zones,
        process_function,
        operation_name=operation_name,
        correlation_id=correlation_id,
    )

    # Handle output with correlation ID from job
    handle_output(results, output, output_handler, correlation_id)

    return results


def aws_operation(
    job_class: Type[BaseJob],
    requires_confirmation: bool = False,
    output_handler: Optional[Callable] = None,
):
    """Simplified decorator for AWS operations.

    Args:
        job_class: The job class to execute
        requires_confirmation: Whether to require user confirmation
        output_handler: Custom output handler function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(ctx, **kwargs):
            operation_name = func.__name__

            # Pre-execution confirmation
            if requires_confirmation and not kwargs.get("force", False):
                if not click.confirm(f"Continue with {operation_name}?"):
                    click.echo("Operation cancelled by user.")
                    return

            # Dry run handling
            if kwargs.get("dry_run", False):
                click.echo(f"[DRY RUN] Would execute {operation_name}")
                return

            # Execute operation
            try:
                # Add output handler to kwargs if provided
                if output_handler:
                    kwargs["output_handler"] = output_handler

                # Map CLI parameter names to job parameter names
                if "name" in kwargs:
                    kwargs["server_name"] = kwargs.pop("name")

                # Map 'all' parameter to operation-specific parameters
                if "all" in kwargs:
                    all_value = kwargs["all"]
                    kwargs["start_all"] = all_value
                    kwargs["stop_all"] = all_value

                result = execute_zone_operation(
                    job_class, operation_name=operation_name, **kwargs
                )
                return result

            except Exception as e:
                handle_operation_error(operation_name, e)
                raise

        return wrapper

    return decorator


# Generic operation decorator to eliminate redundancy
def operation_decorator(operation_type: str, requires_confirmation: bool = True):
    """Generic decorator for all operation types."""

    def decorator(func: Callable) -> Callable:
        job_class = get_job_class(operation_type, func.__name__)
        return aws_operation(
            job_class=job_class,
            requires_confirmation=requires_confirmation,
        )(func)

    return decorator


# Specialized decorators using the generic pattern
def server_operation(requires_confirmation: bool = True):
    """Decorator for server-related operations."""
    return operation_decorator("server", requires_confirmation)


def backup_operation(requires_confirmation: bool = True):
    """Decorator for backup-related operations."""
    return operation_decorator("backup", requires_confirmation)


def ami_operation(requires_confirmation: bool = True):
    """Decorator for AMI-related operations."""
    return operation_decorator("ami", requires_confirmation)
