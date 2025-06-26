#!/usr/bin/env python3
"""
utils/session.py
--------------
Session management utilities for AWS interactions.

Provides functions and classes to handle AWS session creation and role assumption.
"""

import boto3
import os
from typing import Dict, Optional


def assume_role(
    account_id: str,
    account_name: str,
    role: str,
    region: str = "ap-southeast-2",
    role_session_name: str = "cms",
) -> boto3.Session:
    """Assumes a specified role in an AWS account and returns a boto3 Session."""
    role_arn = f"arn:aws:iam::{account_id}:role/{role}"
    if not account_id.isdigit() or len(account_id) != 12:
        raise ValueError("Invalid AWS account ID")
    try:
        sts_client = boto3.client("sts", region_name=region)
        credentials = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=f"{account_name}-{role_session_name}"
        )["Credentials"]

        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to assume role {role_arn}: {e}")


class SessionManager:
    """Manages AWS sessions with caching to avoid repeated role assumptions."""

    _sessions: Dict[str, boto3.Session] = {}

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached sessions"""
        cls._sessions.clear()

    @classmethod
    def get_session(
        cls,
        account_id: str,
        account_name: str,
        role: str,
        region: str = "ap-southeast-2",
        role_session_name: str = "cms",
    ) -> boto3.Session:
        """Get or create a boto3 Session for the specified AWS role."""
        session_key = f"{account_id}:{account_name}:{role}:{region}:{role_session_name}"

        if session_key not in cls._sessions:
            cls._sessions[session_key] = assume_role(
                account_id, account_name, role, region, role_session_name
            )

        return cls._sessions[session_key]

    @classmethod
    def get_session_from_env(
        cls,
        region: str = "ap-southeast-2",
        session_name: str = "pipeline"
    ) -> boto3.Session:
        """Create a boto3 Session from environment variables for pipeline usage.
        
        Expected environment variables:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY 
        - AWS_SESSION_TOKEN
        """
        session_key = f"env:{region}:{session_name}"
        
        if session_key not in cls._sessions:
            # Check for AWS credentials in environment variables
            access_key = os.getenv('AWS_ACCESS_KEY_ID')
            secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            session_token = os.getenv('AWS_SESSION_TOKEN')
            
            if not access_key or not secret_key:
                raise ValueError(
                    "Missing required environment variables. "
                    "Please set AWS_ACCESS_KEY_IDand AWS_SECRET_ACCESS_KEY/"
                )
            
            cls._sessions[session_key] = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token,
                region_name=region
            )
            
        return cls._sessions[session_key]
