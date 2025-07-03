#!/usr/bin/env python3
"""Simple CSV Report Generator."""

import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from aws_ops.utils.logger import setup_logger


class CSVReportGenerator:
    """Simple CSV report generator."""

    def __init__(self, output_dir: str = "reports"):
        """Initialize the CSV report generator."""
        self.output_dir = output_dir
        self.logger = setup_logger(__name__, "report_generator.log")
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Ensure the output directory exists."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        data: List[Dict[str, Any]],
        filename: str,
        fieldnames: Optional[List[str]] = None,
    ) -> bool:
        """Generate a CSV report from the provided data."""
        try:
            if not data:
                self.logger.warning("No data provided for report generation")
                return False

            if not filename.endswith(".csv"):
                filename = f"{filename}.csv"

            output_path = Path(self.output_dir) / filename
            
            # Get fieldnames - use provided order or auto-detect
            if fieldnames is None:
                fieldnames_set = set()
                for item in data:
                    fieldnames_set.update(item.keys())
                fieldnames = sorted(fieldnames_set)

            # Write CSV file
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            self.logger.info(f"CSV report generated: {output_path} ({len(data)} records)")
            return True

        except Exception as e:
            self.logger.error(f"Error generating CSV report: {e}")
            return False
