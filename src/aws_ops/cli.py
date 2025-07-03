#!/usr/bin/env python3
"""
AWS Ops - Enterprise CLI
Enterprise AWS operations toolkit with enhanced security and compliance
"""

import click
import sys
from pathlib import Path


# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import validation helpers and error handling
from .utils.decorators import (
    server_operation,
    backup_operation,
    ami_operation,
)
from aws_ops.utils.logger import setup_logger


def setup_logging(verbose: bool = False):
    level = "DEBUG" if verbose else "INFO"
    return setup_logger("aws_ops_cli", "cli.log", level)


# Common CLI options
def add_common_options(func):
    func = click.option("--landing-zones", "-l", help="Landing zones")(func)
    func = click.option("--force", is_flag=True, help="Skip confirmation prompts")(func)
    func = click.option("--verbose", is_flag=True, help="Enable verbose output")(func)
    func = click.option(
        "--dry-run", is_flag=True, help="Preview changes without executing"
    )(func)
    func = click.option(
        "--managed-by", 
        default="CMS",
        type=click.Choice(["CMS", "all"], case_sensitive=False),
        help="Filter by management type: CMS or all (default: CMS)"
    )(func)

    return func


@click.group()
@click.option("--region", default="ap-southeast-2", help="AWS region")
@click.pass_context
def cli(ctx, region):
    """AWS Ops - Simplified Enterprise Cloud Operations"""
    ctx.ensure_object(dict)

    # Store simple configuration
    ctx.obj["region"] = region


@cli.command()
@click.option("--output", type=click.Path(), help="Output file path")
@add_common_options
@click.pass_context
@server_operation(requires_confirmation=False)
def scan_servers(ctx, output, landing_zones, dry_run, verbose, force, managed_by):
    """Scan EC2 servers across landing zones"""
    setup_logging(verbose)
    # All processing logic is handled by the decorator
    pass


@cli.command()
@click.option("--name", help="Server name pattern (optional - if not provided, operates on all servers based on managed_by filter)")
@click.option("--all", "start_all", is_flag=True, help="Start all servers (equivalent to not providing --name)")
@add_common_options
@click.pass_context
@server_operation(requires_confirmation=True)
def start_servers(ctx, name, start_all, landing_zones, dry_run, verbose, force, managed_by):
    """Start EC2 servers
    
    If --name is not provided, starts all servers with managed_by filter (CMS by default).
    Use --managed-by=all to operate on all servers regardless of management type.
    """
    setup_logging(verbose)
    # All processing logic is handled by the decorator
    pass


@cli.command()
@click.option("--name", help="Server name pattern (optional - if not provided, operates on all servers based on managed_by filter)")
@click.option("--all", "stop_all", is_flag=True, help="Stop all servers (equivalent to not providing --name)")
@add_common_options
@click.pass_context
@server_operation(requires_confirmation=True)
def stop_servers(ctx, name, stop_all, landing_zones, dry_run, verbose, force, managed_by):
    """Stop EC2 servers
    
    If --name is not provided, stops all servers with managed_by filter (CMS by default).
    Use --managed-by=all to operate on all servers regardless of management type.
    """
    setup_logging(verbose)
    # All processing logic is handled by the decorator
    pass


@cli.command()
@click.option("--days", type=int, default=30, help="Number of days to look back")
@click.option("--output", type=click.Path(), help="Output file path")
@click.option("--generate-report", is_flag=True, help="Generate CSV report")
@add_common_options
@click.pass_context
@backup_operation(requires_confirmation=False)
def scan_backups(
    ctx, days, output, generate_report, landing_zones, dry_run, verbose, force, managed_by
):
    """Scan backup status"""
    setup_logging(verbose)
    # All processing logic is handled by the decorator
    pass


@cli.command()
@click.option("--days", type=int, default=30, help="Retention period in days")
@click.option("--output", type=click.Path(), help="Output file path")
@add_common_options
@click.pass_context
@backup_operation(requires_confirmation=True)
def cleanup_snapshots(ctx, days, output, landing_zones, dry_run, verbose, force, managed_by):
    """Clean up old snapshots"""
    setup_logging(verbose)
    # All processing logic is handled by the decorator
    pass


@cli.command()
@click.option("--server-name", required=True, help="Server name pattern to create AMI from")
@click.option("--no-reboot", is_flag=True, default=True, help="Create AMI without rebooting (default: True)")
@add_common_options
@click.pass_context
@ami_operation(requires_confirmation=True)
def create_ami(
    ctx, server_name, no_reboot, landing_zones, dry_run, verbose, force, managed_by
):
    """Create AMI from EC2 servers
    
    Creates AMI from servers matching the name pattern.
    Use --managed-by=all to operate on all servers regardless of management type.
    """
    setup_logging(verbose)
    # All processing logic is handled by the decorator
    pass


@cli.command()
@click.option("--ami-id", required=True, help="AMI ID to update to")
@click.option("--template-name", help="EC2 Launch template name")
@add_common_options
@click.pass_context
@ami_operation(requires_confirmation=True)
def update_ami(
    ctx, ami_id, template_name, landing_zones, dry_run, verbose, force, managed_by
):
    """Update AMI in CloudFormation templates"""
    setup_logging(verbose)
    # All processing logic is handled by the decorator
    pass


@cli.command()
def version():
    """Show version information"""
    click.echo("AWS Ops - Simplified Version 1.0.0")
    click.echo("Enterprise AWS operations toolkit")


if __name__ == "__main__":
    cli()
