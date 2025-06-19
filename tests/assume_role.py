#!/usr/bin/env python3
"""
Test AWS role assumption and session management.

Usage:
    python tests/assume_role.py
    python tests/assume_role.py --account-id 123456789012
"""

import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils import (
    setup_logger,
    get_aws_region,
    get_provision_role,
    get_test_account_id,
    get_test_account_name,
    SessionManager,
)

logger = setup_logger(__name__, log_file="assume_role.log")


def validate_inputs(account_id: str, account_name: str, role: str) -> bool:
    """Validate required inputs for session testing."""
    if not account_id or not account_id.strip():
        logger.error("❌ Account ID is required")
        return False

    if not account_id.isdigit() or len(account_id) != 12:
        logger.error(f"❌ Invalid account ID format: {account_id} (must be 12 digits)")
        return False

    if not account_name or not account_name.strip():
        logger.error("❌ Account name is required")
        return False

    if not role or not role.strip():
        logger.error("❌ Provision role is not configured")
        return False

    return True


def test_session(account_id: str, account_name: str) -> bool:
    """Test AWS session creation and functionality."""
    try:
        role = get_provision_role()
        region = get_aws_region()

        # Validate inputs
        if not validate_inputs(account_id, account_name, role):
            return False

        logger.info(f"Testing session for {account_name} ({account_id})")
        logger.info(f"Using role: {role} in region: {region}")

        session = SessionManager.get_session(
            account_id, account_name, role, region, "test-session"
        )

        # Verify session works
        sts_client = session.client("sts")
        identity = sts_client.get_caller_identity()

        logger.info(f"✅ Success: Session created successfully")
        logger.info(f"   Account: {identity.get('Account')}")
        logger.info(f"   ARN: {identity.get('Arn')}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False


def main(account_id: str = None, account_name: str = None) -> None:
    """Main test function."""
    # Get values from config if not provided
    if not account_id:
        account_id = get_test_account_id()
    if not account_name:
        account_name = get_test_account_name()

    logger.info("Testing AWS session management...")

    # Check if we have the required values
    if not account_id or not account_name:
        logger.error("❌ Missing configuration:")
        if not account_id:
            logger.error("   - No test account ID found")
        if not account_name:
            logger.error("   - No test account name found")
        logger.error("")
        logger.error("Please either:")
        logger.error("   1. Create configs/settings.yaml with test_account section")
        logger.error("   2. Use command line arguments:")
        logger.error(
            "      python tests/assume_role.py --account-id 123456789012 --account-name 'Test Account'"
        )
        return

    success = test_session(account_id, account_name)
    if success:
        logger.info("🎉 All tests passed!")
    else:
        logger.error("💥 Tests failed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test AWS session management")
    parser.add_argument("--account-id", help="AWS account ID")
    parser.add_argument("--account-name", help="Account name")

    args = parser.parse_args()
    main(args.account_id, args.account_name)
