#!/usr/bin/env python3
"""Landing Zone Utilities

Enterprise-grade landing zone management utilities for AWS operations.
Supports both legacy plain-text format and modern JSON API format.

Features:
- Environment extraction from zone names
- Account ID mapping via external services
- Enterprise validation and compliance
- Support for nonprod, preprod, and prod environments
- Integration with ConfigManager for centralized zone management
- Enhanced zone filtering and processing capabilities
"""

import os
import requests
from typing import List, Dict, Set, Optional
from .exceptions import CLIError, ValidationRules
from .logger import setup_logger

logger = setup_logger(__name__, "lz.log")


def fetch_zones_from_url(url: str) -> List[str]:
    """
    Fetch landing zones from a given URL.
    Filters out empty lines and comments starting with "#".
    """
    resp = requests.get(url, verify=os.environ.get("AWS_CA_BUNDLE"))
    resp.raise_for_status()
    return [
        ln.strip()
        for ln in resp.text.splitlines()
        if ln.strip() and not ln.startswith("#")
    ]


# ============================================================================
# Enterprise Landing Zone Functions
# ============================================================================

def extract_environment_from_zone(zone_name: str) -> str:
    zone_lower = zone_name.lower()
    
    if 'nonprod' in zone_lower:
        return 'nonprod'
    
    if 'preprod' in zone_lower:
        return 'preprod'
    
    if 'prod' in zone_lower and 'nonprod' not in zone_lower and 'preprod' not in zone_lower:
        return 'prod'
    
    raise CLIError(
        f"Unsupported environment in zone '{zone_name}'. "
        f"Only 'nonprod', 'preprod', and 'prod' environments are supported."
    )


def fetch_account_mapping(config: 'ConfigManager') -> Dict[str, str]:
    try:
        # Priority 1: Try to get account_mapping from settings.yml
        account_mapping = config.get_account_mapping()
        
        if account_mapping:
            logger.info(f"Using account mapping from settings.yml: {len(account_mapping)} zones")
            
            # Validate account IDs
            for zone_name, account_id in account_mapping.items():
                if not ValidationRules.validate_aws_account_id(account_id):
                    raise CLIError(
                        f"Invalid account ID '{account_id}' for zone '{zone_name}'"
                    )
            
            return account_mapping
        
        # Priority 2: Fall back to external URL if account_mapping is not available
        logger.info("No account_mapping found in settings.yml, falling back to external URL")
        zones_url = config.get_zones_url()
        
        if not zones_url:
            raise CLIError("No zones_url found in configuration and no account_mapping available")
        
        # Fetch zones from external URL and parse them
        zone_lines = fetch_zones_from_url(zones_url)
        account_mapping = {}
        
        for line in zone_lines:
            parts = line.split()
            if len(parts) >= 2:
                account_id = parts[0]
                zone_name = parts[1]
                
                if ValidationRules.validate_aws_account_id(account_id):
                    account_mapping[zone_name] = account_id
                else:
                    logger.warning(f"Skipping invalid account ID '{account_id}' for zone '{zone_name}'")
        
        if not account_mapping:
            raise CLIError("No valid account mapping found from external URL")
        
        logger.info(f"Fetched account mapping from external URL: {len(account_mapping)} zones")
        return account_mapping
        
    except Exception as e:
        if isinstance(e, CLIError):
            raise
        raise CLIError(f"Failed to fetch account mapping: {str(e)}")
