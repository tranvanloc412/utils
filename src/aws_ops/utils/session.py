#!/usr/bin/env python3
"""
utils/session.py

Session management utilities for AWS interactions.

Provides functions and classes to handle AWS session creation and role assumption.
"""

import boto3
import os
from typing import Dict, Optional
from botocore.exceptions import ClientError
from .logger import setup_logger

logger = setup_logger(__name__, "session.log")


def assume_role(
    account_id: str,
    account_name: str,
    role: str,
    region: str = "ap-southeast-2",
    role_session_name: str = "cms",
) -> boto3.Session:
    """Assumes a specified role in an AWS account and returns a boto3 Session."""
    # Validate account ID
    if not account_id.isdigit() or len(account_id) != 12:
        raise ValueError(f"Invalid AWS account ID: {account_id}. Must be 12 digits.")

    role_arn = f"arn:aws:iam::{account_id}:role/{role}"

    try:
        sts_client = boto3.client("sts", region_name=region)
        response = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=f"{account_name}-{role_session_name}"
        )
        credentials = response["Credentials"]

        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        raise RuntimeError(f"Failed to assume role {role_arn}: {error_code} - {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error assuming role {role_arn}: {e}")


class SessionManager:
    """Manages AWS sessions for role assumption and credential handling."""

    @classmethod
    def get_session(
        cls,
        account_id: str,
        account_name: str,
        role: str,
        region: str = "ap-southeast-2",
        role_session_name: str = "cms",
    ) -> boto3.Session:
        """Create a boto3 Session for the specified AWS role."""
        return assume_role(account_id, account_name, role, region, role_session_name)

    @classmethod
    def get_session_from_env(cls, region: str = "ap-southeast-2") -> boto3.Session:
        """Create a boto3 Session from environment variables.

        Expected environment variables:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_SESSION_TOKEN
        """
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        session_token = os.getenv("AWS_SESSION_TOKEN")

        if not access_key or not secret_key:
            raise ValueError(
                "Missing required environment variables. "
                "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
            )

        return boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
