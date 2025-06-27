# src/aws_ops/cli.py
import click
from aws_ops.jobs import (
    ScanServers,
    ManageServers,
    ManageBackups,
)
from aws_ops.utils.config import ConfigManager


@click.group()
@click.option("--config", help="Configuration file path")
@click.pass_context
def cli(ctx, config):
    """AWS Operations CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = ConfigManager(config)


@cli.command()
@click.option(
    "--landing-zones", "-l", multiple=True, help="Specific landing zones to scan"
)
@click.option("--region", "-r", default="ap-southeast-2", help="AWS region to scan")
@click.option("--output", "--output-file", "-o", help="Output CSV file path")
@click.option(
    "--platform",
    "-p",
    type=click.Choice(["windows", "linux"]),
    help="Filter by platform (windows or linux)",
)
@click.option(
    "--env-filter", help="Filter by Environment tag value (e.g., prod, dev, test)"
)
@click.option(
    "--scan-all", is_flag=True, help="Scan all EC2 instances regardless of platform"
)
@click.option(
    "--lz-env",
    type=click.Choice(["nonprod", "preprod", "prod"]),
    help="Filter landing zones by environment suffix (nonprod, preprod, prod)",
)
@click.option(
    "--test",
    is_flag=True,
    help="Use test account configuration from settings.yaml (overrides --landing-zones)",
)
@click.pass_context
def scan_servers(
    ctx, landing_zones, region, output, platform, env_filter, scan_all, lz_env, test
):
    """Scan EC2 servers across AWS landing zones with flexible filtering."""
    # Validate that only one of lz_env or landing_zones is specified
    if lz_env and landing_zones and not test:
        click.echo(
            "Error: Cannot specify both --lz-env and --landing-zones at the same time. Choose one.",
            err=True,
        )
        ctx.exit(1)

    # Handle test account configuration
    if test:
        config_manager = ctx.obj["config"]
        test_account_id = config_manager.get_test_account_id()
        test_account_name = config_manager.get_test_account_name()
        landing_zones = [f"{test_account_name}:{test_account_id}"]
    else:
        landing_zones = list(landing_zones) if landing_zones else None

    # Validate landing zones have consistent environment if multiple specified
    if landing_zones and len(landing_zones) > 1 and not test:
        environments = set()
        for zone in landing_zones:
            zone_name = zone.split(":")[0] if ":" in zone else zone
            # Extract environment suffix (nonprod, preprod, prod)
            for env_suffix in ["nonprod", "preprod", "prod"]:
                if zone_name.lower().endswith(env_suffix):
                    environments.add(env_suffix)
                    break

        if len(environments) > 1:
            click.echo(
                f"Error: All landing zones must belong to the same environment. Found: {', '.join(environments)}",
                err=True,
            )
            ctx.exit(1)

    # Filter landing zones by environment suffix if lz_env is specified
    if lz_env and not test:
        config_manager = ctx.obj["config"]
        all_landing_zones = config_manager.get_all_landing_zones()
        filtered_zones = []
        for zone in all_landing_zones:
            zone_name = zone.split(":")[0] if ":" in zone else zone
            if zone_name.lower().endswith(lz_env.lower()):
                filtered_zones.append(zone)
        landing_zones = filtered_zones if filtered_zones else landing_zones

    job = ScanServers(ctx.obj["config"])
    job.execute(
        landing_zones=landing_zones,
        region=region,
        output=output,
        platform=platform,
        env_filter=env_filter,
        scan_all=scan_all,
        lz_env=lz_env,
    )


@cli.command()
@click.option(
    "--landing-zones", "-l", multiple=True, help="Specific landing zones to process"
)
@click.option(
    "--region", "-r", default="ap-southeast-2", help="AWS region to operate in"
)
@click.option("--server-name", help="Specific server name to start")
@click.option(
    "--start-all", is_flag=True, help="Start all stopped servers in the landing zone(s)"
)
@click.option(
    "--dry-run", is_flag=True, help="Preview operations without executing them"
)
@click.option(
    "--test",
    is_flag=True,
    help="Use test account configuration from settings.yaml (overrides --landing-zones)",
)
@click.pass_context
def start_servers(ctx, landing_zones, region, server_name, start_all, dry_run, test):
    """Start EC2 servers by name or all servers in a specific landing zone."""
    # Handle test account configuration
    if test:
        config_manager = ctx.obj["config"]
        test_account_id = config_manager.get_test_account_id()
        test_account_name = config_manager.get_test_account_name()
        landing_zones = [f"{test_account_name}:{test_account_id}"]
    else:
        landing_zones = list(landing_zones) if landing_zones else None

    job = ManageServers(ctx.obj["config"])
    result = job.execute(
        landing_zones=landing_zones,
        region=region,
        server_name=server_name,
        action="start",
        process_all=start_all,
        dry_run=dry_run,
    )

    # Exit with appropriate code
    if not result.get("success", False):
        click.echo(f"Error: {result.get('error', 'Unknown error occurred')}", err=True)
        ctx.exit(1)


@cli.command()
@click.option(
    "--landing-zones", "-l", multiple=True, help="Specific landing zones to process"
)
@click.option(
    "--region", "-r", default="ap-southeast-2", help="AWS region to operate in"
)
@click.option("--server-name", help="Specific server name to stop")
@click.option(
    "--stop-all", is_flag=True, help="Stop all running servers in the landing zone(s)"
)
@click.option(
    "--dry-run", is_flag=True, help="Preview operations without executing them"
)
@click.option(
    "--test",
    is_flag=True,
    help="Use test account configuration from settings.yaml (overrides --landing-zones)",
)
@click.pass_context
def stop_servers(ctx, landing_zones, region, server_name, stop_all, dry_run, test):
    """Stop EC2 servers by name or all servers in a specific landing zone."""
    # Handle test account configuration
    if test:
        config_manager = ctx.obj["config"]
        test_account_id = config_manager.get_test_account_id()
        test_account_name = config_manager.get_test_account_name()
        landing_zones = [f"{test_account_name}:{test_account_id}"]
    else:
        landing_zones = list(landing_zones) if landing_zones else None

    job = ManageServers(ctx.obj["config"])
    result = job.execute(
        landing_zones=landing_zones,
        region=region,
        server_name=server_name,
        action="stop",
        process_all=stop_all,
        dry_run=dry_run,
    )

    # Exit with appropriate code
    if not result.get("success", False):
        click.echo(f"Error: {result.get('error', 'Unknown error occurred')}", err=True)
        ctx.exit(1)


@cli.command()
@click.option(
    "--landing-zones", "-l", multiple=True, help="Specific landing zones to process"
)
@click.option(
    "--region", "-r", default="ap-southeast-2", help="AWS region to operate in"
)
@click.option(
    "--output", "--output-file", "-o", help="Output CSV file path for backup report"
)
@click.option(
    "--snapshot-age-days",
    type=int,
    default=30,
    help="Age threshold for snapshots in days (default: 30)",
)
@click.option(
    "--ami-age-days",
    type=int,
    default=90,
    help="Age threshold for AMIs in days (default: 90)",
)
@click.option(
    "--test",
    is_flag=True,
    help="Use test account configuration from settings.yaml (overrides --landing-zones)",
)
@click.pass_context
def scan_backups(
    ctx, landing_zones, region, output, snapshot_age_days, ami_age_days, test
):
    """Scan and report on AWS backups (snapshots and AMIs) based on age thresholds."""
    # Handle test account configuration
    if test:
        config_manager = ctx.obj["config"]
        test_account_id = config_manager.get_test_account_id()
        test_account_name = config_manager.get_test_account_name()
        landing_zones = [f"{test_account_name}:{test_account_id}"]
    else:
        landing_zones = list(landing_zones) if landing_zones else None

    job = ManageBackups(ctx.obj["config"])
    result = job.execute(
        landing_zones=landing_zones,
        region=region,
        output=output,
        snapshot_age_days=snapshot_age_days,
        ami_age_days=ami_age_days,
        delete_old_snapshots=False,
        delete_old_amis=False,
        create_amis=False,
        dry_run=True,
    )

    # Exit with appropriate code
    if not result.get("success", False):
        click.echo(f"Error: {result.get('error', 'Unknown error occurred')}", err=True)
        ctx.exit(1)


@cli.command()
@click.option(
    "--landing-zones", "-l", multiple=True, help="Specific landing zones to process"
)
@click.option(
    "--region", "-r", default="ap-southeast-2", help="AWS region to operate in"
)
@click.option(
    "--age-days",
    type=int,
    default=30,
    help="Age threshold for snapshots in days (default: 30)",
)
@click.option(
    "--dry-run", is_flag=True, help="Preview operations without executing them"
)
@click.option(
    "--test",
    is_flag=True,
    help="Use test account configuration from settings.yaml (overrides --landing-zones)",
)
@click.pass_context
def delete_old_snapshots(ctx, landing_zones, region, age_days, dry_run, test):
    """Delete EBS snapshots older than specified age threshold."""
    # Handle test account configuration
    if test:
        config_manager = ctx.obj["config"]
        test_account_id = config_manager.get_test_account_id()
        test_account_name = config_manager.get_test_account_name()
        landing_zones = [f"{test_account_name}:{test_account_id}"]
    else:
        landing_zones = list(landing_zones) if landing_zones else None

    job = ManageBackups(ctx.obj["config"])
    result = job.execute(
        landing_zones=landing_zones,
        region=region,
        snapshot_age_days=age_days,
        ami_age_days=90,  # Not used for this operation
        delete_old_snapshots=True,
        delete_old_amis=False,
        create_amis=False,
        dry_run=dry_run,
    )

    # Exit with appropriate code
    if not result.get("success", False):
        click.echo(f"Error: {result.get('error', 'Unknown error occurred')}", err=True)
        ctx.exit(1)


@cli.command()
@click.option(
    "--landing-zones", "-l", multiple=True, help="Specific landing zones to process"
)
@click.option(
    "--region", "-r", default="ap-southeast-2", help="AWS region to operate in"
)
@click.option(
    "--age-days",
    type=int,
    default=90,
    help="Age threshold for AMIs in days (default: 90)",
)
@click.option(
    "--dry-run", is_flag=True, help="Preview operations without executing them"
)
@click.option(
    "--test",
    is_flag=True,
    help="Use test account configuration from settings.yaml (overrides --landing-zones)",
)
@click.pass_context
def delete_old_amis(ctx, landing_zones, region, age_days, dry_run, test):
    """Delete AMIs older than specified age threshold."""
    # Handle test account configuration
    if test:
        config_manager = ctx.obj["config"]
        test_account_id = config_manager.get_test_account_id()
        test_account_name = config_manager.get_test_account_name()
        landing_zones = [f"{test_account_name}:{test_account_id}"]
    else:
        landing_zones = list(landing_zones) if landing_zones else None

    job = ManageBackups(ctx.obj["config"])
    result = job.execute(
        landing_zones=landing_zones,
        region=region,
        snapshot_age_days=30,  # Not used for this operation
        ami_age_days=age_days,
        delete_old_snapshots=False,
        delete_old_amis=True,
        create_amis=False,
        dry_run=dry_run,
    )

    # Exit with appropriate code
    if not result.get("success", False):
        click.echo(f"Error: {result.get('error', 'Unknown error occurred')}", err=True)
        ctx.exit(1)


@cli.command()
@click.option(
    "--landing-zones", "-l", multiple=True, help="Specific landing zones to process"
)
@click.option(
    "--region", "-r", default="ap-southeast-2", help="AWS region to operate in"
)
@click.option(
    "--dry-run", is_flag=True, help="Preview operations without executing them"
)
@click.option(
    "--test",
    is_flag=True,
    help="Use test account configuration from settings.yaml (overrides --landing-zones)",
)
@click.pass_context
def create_amis(ctx, landing_zones, region, dry_run, test):
    """Create AMIs for EC2 instances tagged with managed_by=CMS."""
    # Handle test account configuration
    if test:
        config_manager = ctx.obj["config"]
        test_account_id = config_manager.get_test_account_id()
        test_account_name = config_manager.get_test_account_name()
        landing_zones = [f"{test_account_name}:{test_account_id}"]
    else:
        landing_zones = list(landing_zones) if landing_zones else None

    job = ManageBackups(ctx.obj["config"])
    result = job.execute(
        landing_zones=landing_zones,
        region=region,
        snapshot_age_days=30,  # Not used for this operation
        ami_age_days=90,  # Not used for this operation
        delete_old_snapshots=False,
        delete_old_amis=False,
        create_amis=True,
        dry_run=dry_run,
    )

    # Exit with appropriate code
    if not result.get("success", False):
        click.echo(f"Error: {result.get('error', 'Unknown error occurred')}", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    cli()
