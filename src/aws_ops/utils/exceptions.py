"""Exception classes and validation utilities for AWS operations.

This module contains common exception classes and validation rules
used across the AWS operations toolkit.
"""

import re


class CLIError(Exception):
    """Custom exception for CLI-related errors."""

    pass


class ValidationRules:
    """Validation utilities for AWS resources."""

    @staticmethod
    def validate_aws_account_id(account_id: str) -> bool:
        """Validate AWS account ID format (12 digits)."""
        return bool(re.match(r"^\d{12}$", account_id))
