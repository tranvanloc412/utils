#!/usr/bin/env python3
"""Enterprise Zone Processor for AWS operations with advanced decorator support."""

import time
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from aws_ops.utils.logger import setup_logger
from aws_ops.utils.config import ConfigManager


@dataclass
class ProcessingResult:
    """Result of zone processing operation."""

    results: List[Any]
    processed_zones: int
    total_zones: int
    errors: List[str]
    execution_time: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    success_rate: float = field(init=False)
    metadata: Dict[str, Any] = field(default_factory=dict)
    failed_zones: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate success rate after initialization."""
        if self.total_zones > 0:
            self.success_rate = (self.processed_zones / self.total_zones) * 100
        else:
            self.success_rate = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "processed_zones": self.processed_zones,
            "total_zones": self.total_zones,
            "success_rate": f"{self.success_rate:.2f}%",
            "execution_time": f"{self.execution_time:.2f}s",
            "start_time": self.start_time,
            "end_time": self.end_time,
            "errors_count": len(self.errors),
            "errors": self.errors,
            "failed_zones": self.failed_zones,
            "metadata": self.metadata,
        }


class ZoneProcessor:
    """Enterprise zone processor for AWS operations with advanced features."""

    def __init__(self, name: str = "zone_processor", parallel: bool = False):
        """Initialize the zone processor.

        Args:
            name: Name of the processor instance
            parallel: Whether to enable parallel processing (future enhancement)
        """
        self.name = name
        self.parallel = parallel
        self.logger = setup_logger(__name__, "zone_processor.log")
        self._metrics = {"total_operations": 0, "total_errors": 0}
        self.config_manager = ConfigManager()

    def process_zones(
        self,
        zones: List[str],
        process_function: Callable,
        operation_name: str = "unknown",
        correlation_id: Optional[str] = None,
        **kwargs,
    ) -> ProcessingResult:
        """Process a list of zones with the given function.

        Args:
            zones: List of zone identifiers to process
            process_function: Function to execute for each zone
            operation_name: Name of the operation for logging/metrics
            correlation_id: Correlation ID for tracking operations across logs
            **kwargs: Additional arguments passed to process_function
        """
        start_time = time.time()
        start_timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S UTC", time.gmtime(start_time)
        )

        correlation_prefix = f"[{correlation_id}] " if correlation_id else ""
        self.logger.info(
            f"{correlation_prefix}Starting {operation_name} operation on {len(zones)} zones"
        )

        results = []
        errors = []
        processed = 0
        failed_zones = []

        for i, zone in enumerate(zones, 1):
            try:
                self.logger.debug(
                    f"{correlation_prefix}Processing zone {i}/{len(zones)}: {zone}"
                )
                result = process_function(zone, **kwargs)

                # Validate if processing was actually successful
                if self._validate_processing_result(result, zone):
                    results.append(result)
                    processed += 1
                    self.logger.info(
                        f"{correlation_prefix}Successfully processed zone: {zone}"
                    )
                else:
                    error_msg = f"{correlation_prefix}Zone processing returned unsuccessful result for {zone}"
                    errors.append(error_msg)
                    failed_zones.append(zone)
                    self.logger.warning(error_msg)
                    self._metrics["total_errors"] += 1

            except Exception as e:
                error_msg = (
                    f"{correlation_prefix}Error processing zone {zone}: {str(e)}"
                )
                errors.append(error_msg)
                failed_zones.append(zone)
                self.logger.error(error_msg, exc_info=True)
                self._metrics["total_errors"] += 1

        end_time = time.time()
        end_timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(end_time))
        execution_time = end_time - start_time

        self._metrics["total_operations"] += 1

        result = ProcessingResult(
            results=results,
            processed_zones=processed,
            total_zones=len(zones),
            errors=errors,
            execution_time=execution_time,
            start_time=start_timestamp,
            end_time=end_timestamp,
            failed_zones=failed_zones,
            metadata={
                "operation_name": operation_name,
                "processor_name": self.name,
                "parallel_enabled": self.parallel,
                "all_zones": zones,
            },
        )

        # Log detailed summary with successful and failed zones
        successful_zones = [zone for zone in zones if zone not in failed_zones]

        self.logger.info(
            f"{correlation_prefix}Completed {operation_name}: {processed}/{len(zones)} zones processed "
            f"({result.success_rate:.1f}% success rate) in {execution_time:.2f}s"
        )

        if successful_zones:
            successful_zone_names = [
                self._get_zone_name(zone) for zone in successful_zones
            ]
            self.logger.info(
                f"{correlation_prefix}Successful zones ({len(successful_zones)}): {', '.join(successful_zone_names)}"
            )

        if failed_zones:
            failed_zone_names = [self._get_zone_name(zone) for zone in failed_zones]
            self.logger.info(
                f"{correlation_prefix}Failed zones ({len(failed_zones)}): {', '.join(failed_zone_names)}"
            )

        return result

    def _validate_processing_result(self, result: Any, zone: str) -> bool:
        """Validate if zone processing was actually successful.

        Args:
            result: The result returned by the process function
            zone: The zone identifier for logging

        Returns:
            bool: True if processing was successful, False otherwise
        """
        if result is None:
            return False

        # For dictionary results (common pattern), check status field
        if isinstance(result, dict):
            status = result.get("status", "").lower()
            if status == "error" or status == "failed":
                return False
            # Consider success if status is explicitly 'success' or if no status but has meaningful data
            if status == "success":
                return True
            # If no explicit status, check for meaningful data indicators
            return bool(
                result.get("servers", []) or result.get("data", []) or len(result) > 1
            )

        # For list results, consider successful if not empty
        if isinstance(result, list):
            return len(result) > 0

        # For other types, consider truthy values as successful
        return bool(result)

    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics for monitoring."""
        return self._metrics.copy()

    def reset_metrics(self) -> None:
        """Reset processor metrics."""
        self._metrics = {"total_operations": 0, "total_errors": 0}

    def _get_zone_name(self, zone) -> str:
        """Extract zone name for display purposes.

        Args:
            zone: Zone identifier (string or dict)

        Returns:
            str: Zone name for display
        """
        if isinstance(zone, dict):
            return zone.get("name", zone.get("account_id", str(zone)))
        return str(zone)

    def _resolve_zone_info(self, zone_name: str) -> Optional[Dict[str, str]]:
        """Resolve zone information with fallback logic.

        Priority:
        1. Check account_mapping in settings.yml
        2. If not found, fetch from zones_url
        3. Cache external results to avoid repeated API calls

        Args:
            zone_name: Name of the zone to resolve

        Returns:
            Dict with zone info or None if not found
        """
        # Priority 1: Check account_mapping first
        account_mapping = self.config_manager.get_account_mapping()
        if zone_name in account_mapping:
            self.logger.debug(f"Found zone '{zone_name}' in account_mapping")
            return {
                "account_id": str(account_mapping[zone_name]),  # Ensure account_id is always a string
                "name": zone_name,
                "environment": zone_name,
                "source": "local_config",
            }

        # Priority 2: Fetch from external zones_url
        zones_url = self.config_manager.get_zones_url()
        if not zones_url:
            self.logger.warning(
                f"Zone '{zone_name}' not found in account_mapping and no zones_url configured"
            )
            return None

        try:
            self.logger.info(
                f"Zone '{zone_name}' not found locally, fetching from external URL: {zones_url}"
            )
            from aws_ops.utils.lz import fetch_zones_from_url

            zone_lines = fetch_zones_from_url(zones_url)

            # Parse zones from external source and find the requested zone
            for line in zone_lines:
                parts = line.split()
                if len(parts) >= 2:
                    account_id = parts[0]
                    external_zone_name = parts[1]
                    if external_zone_name == zone_name:
                        zone_info = {
                            "account_id": account_id,
                            "name": external_zone_name,
                            "environment": external_zone_name,
                            "source": "external_url",
                        }
                        self.logger.info(
                            f"Successfully resolved zone '{zone_name}' from external URL"
                        )
                        return zone_info

            # Zone not found in external source
            self.logger.warning(f"Zone '{zone_name}' not found in external zones list")
            return None

        except Exception as e:
            self.logger.error(
                f"Failed to fetch zone '{zone_name}' from external URL {zones_url}: {e}"
            )
            return None

    def resolve_zones(self, zone_names: List[str]) -> List[Dict[str, str]]:
        """Resolve multiple zones with fallback logic.

        Args:
            zone_names: List of zone names to resolve

        Returns:
            List of resolved zone dictionaries
        """
        resolved_zones = []
        unresolved_zones = []

        for zone_name in zone_names:
            zone_info = self._resolve_zone_info(zone_name)
            if zone_info:
                resolved_zones.append(zone_info)
            else:
                unresolved_zones.append(zone_name)

        if unresolved_zones:
            self.logger.warning(
                f"Could not resolve zones: {', '.join(unresolved_zones)}"
            )

        self.logger.info(f"Resolved {len(resolved_zones)}/{len(zone_names)} zones")
        return resolved_zones
