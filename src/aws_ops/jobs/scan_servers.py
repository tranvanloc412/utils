#!/usr/bin/env python3
"""Scan EC2 Servers

Scans EC2 servers across AWS landing zones with flexible filtering options
and generates CSV reports.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from aws_ops.core.processors.zone_processor import ZoneProcessor
from aws_ops.core.processors.report_generator import CSVReportGenerator, ReportConfig
from aws_ops.utils.logger import setup_logger
from aws_ops.core.aws.ec2 import create_ec2_manager
from aws_ops.core.models.server import create_server_info
from aws_ops.jobs.base import BaseJob

logger = setup_logger(__name__, "scan_servers.log")


@dataclass
class ScanParameters:
    """Parameters for EC2 server scanning."""

    region: str = "ap-southeast-2"
    platform: Optional[str] = None
    env_filter: Optional[str] = None
    scan_all: bool = False
    output: Optional[str] = None
    lz_env: Optional[str] = None

    def get_scan_type(self) -> str:
        """Determine scan type for reporting."""
        if self.platform:
            return self.platform
        elif self.env_filter:
            return f"env_{self.env_filter}"
        return "all"

    def get_filter_description(self) -> str:
        """Get human-readable filter description."""
        filters = []
        if self.platform:
            filters.append(f"Platform: {self.platform}")
        if self.env_filter:
            filters.append(f"Environment: {self.env_filter}")
        if self.lz_env:
            filters.append(f"Landing Zone Env: {self.lz_env}")
        if self.scan_all:
            filters.append("Scan all instances")
        return ", ".join(filters) if filters else "No filters"


def _build_ec2_filters(params: ScanParameters) -> List[Dict[str, Any]]:
    """Build EC2 API filters based on parameters."""
    if params.scan_all:
        return []  # No pre-filtering when scanning all

    filters = []
    if params.platform and params.platform.lower() in ["windows", "linux"]:
        filters.append({"Name": "platform", "Values": [params.platform.lower()]})
    if params.env_filter:
        filters.append({"Name": "tag:Environment", "Values": [params.env_filter]})
    return filters


def _should_include_server(server_dict: Dict[str, Any], params: ScanParameters) -> bool:
    """Determine if server should be included in results."""
    if not params.scan_all or not params.env_filter:
        return True
    return server_dict.get("Environment", "").lower() == params.env_filter.lower()


def scan_ec2_servers(
    session, zone_name: str, account_id: str, **kwargs
) -> List[Dict[str, Any]]:
    """Scan for EC2 servers with flexible filtering options.

    Args:
        session: AWS session
        zone_name: Landing zone name
        account_id: AWS account ID
        **kwargs: Additional parameters including scan_params

    Returns:
        List of server dictionaries
    """
    # Extract parameters from kwargs
    params = ScanParameters(
        region=kwargs.get("region", "ap-southeast-2"),
        platform=kwargs.get("platform"),
        env_filter=kwargs.get("env_filter"),
        scan_all=kwargs.get("scan_all", False),
    )

    try:
        ec2_manager = create_ec2_manager(session, params.region)
        filters = _build_ec2_filters(params)

        # Get instances with filters
        instances = ec2_manager.describe_instances(filters=filters if filters else None)

        servers = []
        for instance in instances:
            server = create_server_info(instance)
            server_dict = server.to_dict()
            server_dict["LandingZone"] = zone_name

            # Extract environment from landing zone name
            lz_env = "N/A"
            zone_name_lower = zone_name.lower()
            for env_suffix in ["nonprod", "preprod", "prod"]:
                if zone_name_lower.endswith(env_suffix):
                    lz_env = env_suffix
                    break
            server_dict["Environment"] = lz_env

            # Apply post-filtering if needed
            if _should_include_server(server_dict, params):
                servers.append(server_dict)

        logger.info(
            f"Found {len(servers)} servers in {zone_name} with filters: {params.get_filter_description().lower()}"
        )
        return servers

    except Exception as e:
        logger.error(f"Error scanning EC2 servers in {zone_name}: {e}")
        return []


def write_csv_report(
    servers: List[Dict[str, Any]], filename: str = None, scan_type: str = "all"
):
    """Write server information to CSV file using CSVReportGenerator.

    Args:
        servers: List of server dictionaries
        filename: Output filename (auto-generated if None)
        scan_type: Type of scan for filename generation
    """
    if not servers:
        print("No servers to write to CSV")
        return

    # Configure report generator
    config = ReportConfig(
        output_dir="reports",
        preferred_fields=[
            "LandingZone",
            "Environment",
            "instance_name",
            "instance_id",
            "instance_type",
            "state",
            "platform",
        ],
    )

    generator = CSVReportGenerator(config)

    # Generate report
    result = generator.generate_report(
        data=servers, filename=filename, scan_type=f"{scan_type}_servers"
    )

    # The generator already returns the full path in the result
    output_file = result.get("filename", "report.csv")
    output_path = Path(config.output_dir) / output_file

    print(f"EC2 servers report written to {output_path}")
    print(f"Total servers found: {len(servers)}")


class ScanServers(BaseJob):
    """Job for scanning EC2 servers across AWS landing zones."""

    def execute(
        self,
        environment: Optional[str] = None,
        landing_zones: Optional[List[str]] = None,
        region: str = "ap-southeast-2",
        output: Optional[str] = None,
        platform: Optional[str] = None,
        env_filter: Optional[str] = None,
        scan_all: bool = False,
        lz_env: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute the server scanning job.

        Args:
            environment: Environment to scan
            landing_zones: Specific landing zones to scan
            region: AWS region to scan
            output: Output CSV file path
            platform: Platform filter (windows or linux)
            env_filter: Environment tag filter
            scan_all: Scan all instances regardless of platform
            lz_env: Landing zone environment filter (nonprod, preprod, prod)
            **kwargs: Additional parameters

        Returns:
            Dictionary with execution results
        """
        params = ScanParameters(
            region=region,
            platform=platform,
            env_filter=env_filter,
            scan_all=scan_all,
            output=output,
            lz_env=lz_env,
        )

        processor = ZoneProcessor(
            script_name="scan_ec2_servers",
            description="Scan EC2 servers across AWS landing zones with flexible filtering",
        )

        try:
            all_servers, summary = processor.process_zones_with_aggregation(
                process_function=scan_ec2_servers,
                landing_zones=landing_zones,
                environment=environment,
                session_purpose="ec2-server-scan",
                region=params.region,
                platform=params.platform,
                env_filter=params.env_filter,
                scan_all=params.scan_all,
            )

            # Write CSV report if servers found
            if all_servers:
                write_csv_report(all_servers, params.output, params.get_scan_type())

            # Print summary
            processor.print_summary(
                summary,
                {
                    "Output file": params.output if all_servers else "None (no data)",
                    "Region": params.region,
                    "Filters applied": params.get_filter_description(),
                    "Total servers found": len(all_servers) if all_servers else 0,
                },
            )

            return {
                "success": True,
                "servers_found": len(all_servers) if all_servers else 0,
                "output_file": params.output if all_servers else None,
                "filters_applied": params.get_filter_description(),
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"Error executing scan server job: {e}")
            return {
                "success": False,
                "error": str(e),
                "servers_found": 0,
                "output_file": None,
            }
