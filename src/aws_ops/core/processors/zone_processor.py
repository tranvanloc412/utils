#!/usr/bin/env python3
"""
Zone Processor Utility

Provides a reusable framework for processing AWS landing zones with common patterns:
- Zone filtering and iteration
- Session management and error handling
- Progress tracking and logging

Usage:
    from aws_ops.core.processors.zone_processor import ZoneProcessor

    def process_zone(session, zone_name, account_id, **kwargs):
        # Your zone-specific logic here
        return results

    processor = ZoneProcessor("my_script", "My AWS script")
    results = processor.process_zones(
        process_function=process_zone,
        landing_zones=args.landing_zones,
        environment=args.environment
    )
"""

import argparse
from typing import Callable, Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from aws_ops.utils.lz import fetch_zones_from_url, filter_zones
from aws_ops.utils.session import SessionManager
from aws_ops.utils.config import get_zones_url, get_aws_region, get_provision_role
from aws_ops.utils.logger import setup_logger


@dataclass
class ProcessingResult:
    """Result of zone processing operation."""

    results: List[Any]
    processed_zones: int
    total_zones: int
    errors: List[str]

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (
            (self.processed_zones / self.total_zones * 100)
            if self.total_zones > 0
            else 0
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "results": self.results,
            "processed_zones": self.processed_zones,
            "total_zones": self.total_zones,
            "errors": self.errors,
        }


class ZoneProcessor:
    """Utility class for processing AWS landing zones with common patterns."""

    def __init__(
        self, script_name: str, description: str, log_file: Optional[str] = None
    ):
        """Initialize the zone processor.

        Args:
            script_name: Name of the script (used for logging context)
            description: Description for argument parser
            log_file: Optional log file name (defaults to {script_name}.log)
        """
        self.script_name = script_name
        self.description = description
        self.logger = setup_logger(script_name, log_file or f"{script_name}.log")

        # Initialize AWS components
        self.zones_url = get_zones_url()
        self.region = get_aws_region()
        self.role = get_provision_role()
        self.session_manager = SessionManager()

    def get_zones_to_process(
        self, landing_zones: List[str], environment: str
    ) -> List[str]:
        """Get the list of zones to process based on criteria.

        Args:
            landing_zones: List of specific landing zone names or "name:account_id" format
            environment: Environment filter (prod/nonprod)

        Returns:
            List of zone lines in format "<account_id> <zone_name>"
        """
        if not landing_zones:
            zones = fetch_zones_from_url(self.zones_url)
            return filter_zones(zones, environment=environment)

        # Handle different landing zone formats
        zones = []
        traditional_zones = []

        for lz in landing_zones:
            if ":" in lz:
                # Format: "name:account_id" -> "account_id name"
                name, account_id = lz.split(":", 1)
                zones.append(f"{account_id} {name}")
            else:
                traditional_zones.append(lz)

        # Fetch and filter traditional zones if any
        if traditional_zones:
            all_zones = fetch_zones_from_url(self.zones_url)
            zones.extend(
                [
                    zone_line
                    for zone_line in all_zones
                    if zone_line.split()[1] in traditional_zones
                ]
            )

        return zones

    def _process_single_zone(
        self, zone_line: str, process_function: Callable, session_purpose: str, **kwargs
    ) -> Tuple[Any, Optional[str]]:
        """Process a single zone and return result or error.

        Returns:
            Tuple of (result, error_message). One will be None.
        """
        account_id, zone_name = zone_line.split()

        try:
            session = self.session_manager.get_session(
                account_id, zone_name, self.role, self.region, session_purpose
            )

            result = process_function(
                session=session, zone_name=zone_name, account_id=account_id, **kwargs
            )

            self.logger.debug(f"Successfully processed zone {zone_name}")
            return result, None

        except Exception as e:
            error_msg = f"Error processing {zone_name}: {e}"
            self.logger.error(error_msg)
            return None, error_msg

    def process_zones(
        self,
        process_function: Callable,
        landing_zones: List[str],
        environment: str,
        session_purpose: str = "zone-processing",
        **kwargs,
    ) -> ProcessingResult:
        """Process zones using the provided function.

        Args:
            process_function: Function to call for each zone.
                             Signature: func(session, zone_name, account_id, **kwargs) -> Any
            landing_zones: List of specific landing zone names
            environment: Environment filter (prod/nonprod)
            session_purpose: Purpose string for session management
            **kwargs: Additional arguments passed to process_function

        Returns:
            ProcessingResult with results and summary information
        """
        zones = self.get_zones_to_process(landing_zones, environment)

        if not zones:
            self.logger.warning("No zones found matching criteria")
            return ProcessingResult([], 0, 0, ["No zones found matching criteria"])

        self.logger.info(f"Processing {len(zones)} zones")

        results = []
        errors = []
        processed_count = 0

        for zone_line in zones:
            result, error = self._process_single_zone(
                zone_line, process_function, session_purpose, **kwargs
            )

            if error:
                errors.append(error)
            elif result is not None:
                results.append(result)
                processed_count += 1
            else:
                processed_count += 1  # Successful but no result returned

        self.logger.info(f"Completed: {processed_count}/{len(zones)} zones processed")

        return ProcessingResult(results, processed_count, len(zones), errors)

    def process_zones_with_aggregation(
        self,
        process_function: Callable,
        landing_zones: List[str],
        environment: str,
        session_purpose: str = "zone-processing",
        **kwargs,
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """Process zones and aggregate results into a flat list.

        This is useful when each zone returns a list of items that should be combined.

        Args:
            process_function: Function to call for each zone (should return a list)
            landing_zones: List of specific landing zone names
            environment: Environment filter (prod/nonprod)
            session_purpose: Purpose string for session management
            **kwargs: Additional arguments passed to process_function

        Returns:
            Tuple of (aggregated_results, summary_info)
        """
        result = self.process_zones(
            process_function, landing_zones, environment, session_purpose, **kwargs
        )

        # Flatten results if they are lists
        aggregated_results = []
        for item in result.results:
            if isinstance(item, list):
                aggregated_results.extend(item)
            else:
                aggregated_results.append(item)

        summary = {
            "processed_zones": result.processed_zones,
            "total_zones": result.total_zones,
            "total_items": len(aggregated_results),
            "errors": result.errors,
        }

        return aggregated_results, summary

    def add_common_arguments(
        self, parser: argparse.ArgumentParser
    ) -> argparse.ArgumentParser:
        """Add common landing zone and environment arguments to parser."""
        parser.add_argument(
            "--landing-zones",
            "-l",
            nargs="*",
            default=[],
            help="Landing zone names (e.g., cmsnonprod appnonprod). Leave blank for all zones in the environment.",
        )
        parser.add_argument(
            "--environment",
            "-e",
            default="nonprod",
            choices=["prod", "nonprod"],
            help="Environment suffix to filter zones if landing-zones not specified.",
        )
        return parser

    def create_standard_parser(
        self, additional_args: Optional[Callable] = None
    ) -> argparse.ArgumentParser:
        """Create a standard argument parser with common arguments.

        Args:
            additional_args: Optional function to add script-specific arguments.
                           Signature: func(parser) -> parser

        Returns:
            Configured ArgumentParser
        """
        parser = argparse.ArgumentParser(description=self.description)
        parser = self.add_common_arguments(parser)

        if additional_args:
            parser = additional_args(parser)

        return parser

    def print_summary(
        self, summary: Dict[str, Any], additional_info: Optional[Dict[str, Any]] = None
    ):
        """Print a standardized summary of processing results.

        Args:
            summary: Summary dictionary from process_zones methods
            additional_info: Optional additional information to display
        """
        print("\nSummary:")
        print(
            f"  Zones processed: {summary['processed_zones']}/{summary['total_zones']}"
        )

        if "total_items" in summary:
            print(f"  Total items found: {summary['total_items']}")

        if additional_info:
            for key, value in additional_info.items():
                print(f"  {key}: {value}")

        if summary["errors"]:
            error_count = len(summary["errors"])
            print(f"  Errors: {error_count}")

            # Show first 3 errors
            for error in summary["errors"][:3]:
                print(f"    - {error}")

            if error_count > 3:
                print(f"    ... and {error_count - 3} more errors")
