#!/usr/bin/env python3
"""
Report Generator Utility

Provides a reusable framework for generating CSV reports from data collections.
Supports flexible field ordering, custom formatting, and automatic report organization.

Usage:
    from aws_ops.core.processors.report_generator import CSVReportGenerator

    # Basic usage
    generator = CSVReportGenerator()
    generator.generate_report(data, "servers_report.csv")

    # Advanced usage with custom configuration
    generator = CSVReportGenerator(
        output_dir="custom_reports",
        preferred_fields=["name", "id", "status"],
        timestamp_format="%Y%m%d_%H%M%S"
    )
    generator.generate_report(data, scan_type="ec2_servers")
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

from aws_ops.utils.logger import setup_logger


@dataclass
class ReportConfig:
    """Configuration for CSV report generation."""

    output_dir: str = "reports"
    timestamp_format: str = "%Y%m%d_%H%M%S"
    preferred_fields: List[str] = field(default_factory=list)
    auto_timestamp: bool = True
    create_dirs: bool = True
    encoding: str = "utf-8"

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.output_dir:
            raise ValueError("output_dir cannot be empty")
        if not self.timestamp_format:
            raise ValueError("timestamp_format cannot be empty")


class CSVReportGenerator:
    """Utility class for generating CSV reports from data collections."""

    def __init__(
        self,
        config: Optional[ReportConfig] = None,
        logger_name: str = "report_generator",
    ):
        """Initialize the CSV report generator.

        Args:
            config: Report configuration (uses defaults if None)
            logger_name: Name for the logger instance
        """
        self.config = config or ReportConfig()
        self.logger = setup_logger(logger_name, f"{logger_name}.log")

        # Ensure output directory exists if auto-creation is enabled
        if self.config.create_dirs:
            self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Ensure the output directory exists."""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Ensured output directory exists: {output_path}")

    def _get_ordered_fieldnames(self, data: List[Dict[str, Any]]) -> List[str]:
        """Get ordered fieldnames for CSV output.

        Args:
            data: List of dictionaries containing the data

        Returns:
            List of fieldnames in preferred order
        """
        if not data:
            return self.config.preferred_fields.copy()

        # Collect all unique fields from the data
        all_fields = set()
        for item in data:
            all_fields.update(item.keys())

        # Start with preferred fields that exist in the data
        ordered_fields = [
            field for field in self.config.preferred_fields if field in all_fields
        ]

        # Add remaining fields in alphabetical order
        remaining_fields = sorted(all_fields - set(ordered_fields))
        ordered_fields.extend(remaining_fields)

        return ordered_fields

    def _generate_filename(self, base_name: str, scan_type: str = "data") -> str:
        """Generate a filename with optional timestamp.

        Args:
            base_name: Base filename (with or without extension)
            scan_type: Type of scan/data for filename generation

        Returns:
            Generated filename with timestamp if enabled
        """
        # Remove extension if present
        if base_name.endswith(".csv"):
            base_name = base_name[:-4]

        if self.config.auto_timestamp:
            timestamp = datetime.now().strftime(self.config.timestamp_format)
            filename = f"{base_name}_{timestamp}.csv"
        else:
            filename = f"{base_name}.csv"

        return filename

    def _validate_data(self, data: List[Dict[str, Any]]) -> None:
        """Validate input data format.

        Args:
            data: Data to validate

        Raises:
            ValueError: If data format is invalid
        """
        if not isinstance(data, list):
            raise ValueError("Data must be a list of dictionaries")

        if data and not all(isinstance(item, dict) for item in data):
            raise ValueError("All data items must be dictionaries")

    def generate_report(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        scan_type: str = "data",
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a CSV report from the provided data.

        Args:
            data: List of dictionaries containing the data to export
            filename: Output filename (auto-generated if None)
            scan_type: Type of scan/data for filename generation
            additional_info: Additional information to log/return

        Returns:
            Dictionary with report generation results
        """
        try:
            self._validate_data(data)

            if not data:
                self.logger.warning("No data provided for report generation")
                return {
                    "success": True,
                    "filename": None,
                    "records_written": 0,
                    "message": "No data to write",
                }

            # Generate filename if not provided
            if not filename:
                filename = self._generate_filename(f"{scan_type}_report", scan_type)
            elif not filename.endswith(".csv"):
                filename = f"{filename}.csv"

            # Ensure output directory exists
            if self.config.create_dirs:
                self._ensure_output_dir()

            # Construct full output path
            output_path = Path(self.config.output_dir) / filename

            # Get ordered fieldnames
            fieldnames = self._get_ordered_fieldnames(data)

            # Write CSV file
            with open(
                output_path, "w", newline="", encoding=self.config.encoding
            ) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            # Log success
            self.logger.info(f"CSV report generated: {output_path}")
            self.logger.info(f"Records written: {len(data)}")

            # Print user-friendly output
            print(f"CSV report written to {output_path}")
            print(f"Total records: {len(data)}")

            if additional_info:
                for key, value in additional_info.items():
                    print(f"{key}: {value}")

            return {
                "success": True,
                "filename": str(output_path),
                "records_written": len(data),
                "fieldnames": fieldnames,
                "message": "Report generated successfully",
            }

        except Exception as e:
            error_msg = f"Error generating CSV report: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "filename": None,
                "records_written": 0,
                "error": str(e),
                "message": "Report generation failed",
            }

    def generate_multiple_reports(
        self,
        reports_data: Dict[str, List[Dict[str, Any]]],
        base_filename: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Generate multiple CSV reports from a dictionary of data.

        Args:
            reports_data: Dictionary where keys are report names and values are data lists
            base_filename: Base filename pattern (report name will be appended)

        Returns:
            Dictionary with results for each report
        """
        results = {}

        for report_name, data in reports_data.items():
            if base_filename:
                filename = f"{base_filename}_{report_name}"
            else:
                filename = None

            result = self.generate_report(
                data=data, filename=filename, scan_type=report_name
            )

            results[report_name] = result

        return results

    def update_config(self, **kwargs) -> None:
        """Update configuration parameters.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.debug(f"Updated config: {key} = {value}")
            else:
                self.logger.warning(f"Unknown config parameter: {key}")

        # Re-ensure output directory if it was changed
        if "output_dir" in kwargs and self.config.create_dirs:
            self._ensure_output_dir()


# Convenience functions for common use cases
def generate_csv_report(
    data: List[Dict[str, Any]],
    filename: Optional[str] = None,
    scan_type: str = "data",
    output_dir: str = "reports",
    preferred_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Convenience function to generate a CSV report with default settings.

    Args:
        data: List of dictionaries containing the data to export
        filename: Output filename (auto-generated if None)
        scan_type: Type of scan/data for filename generation
        output_dir: Output directory for the report
        preferred_fields: Preferred field ordering

    Returns:
        Dictionary with report generation results
    """
    config = ReportConfig(
        output_dir=output_dir, preferred_fields=preferred_fields or []
    )

    generator = CSVReportGenerator(config)
    return generator.generate_report(data, filename, scan_type)


def generate_timestamped_report(
    data: List[Dict[str, Any]],
    base_name: str,
    scan_type: str = "data",
    output_dir: str = "reports",
) -> Dict[str, Any]:
    """Convenience function to generate a timestamped CSV report.

    Args:
        data: List of dictionaries containing the data to export
        base_name: Base name for the file (timestamp will be added)
        scan_type: Type of scan/data for logging
        output_dir: Output directory for the report

    Returns:
        Dictionary with report generation results
    """
    config = ReportConfig(output_dir=output_dir, auto_timestamp=True)
    generator = CSVReportGenerator(config)
    return generator.generate_report(data, base_name, scan_type)
