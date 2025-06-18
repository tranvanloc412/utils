#!/usr/bin/env python3
"""
utils/landing_zone.py

- Fetch landing zones from Zones URL. Expects plain-text response with one "<account_id> <zone_name>" per line.
- Filter landing zones by name or environment suffix.
- Get landing zone account ID from a parsed line.
"""

import os
import requests
from typing import List


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


def filter_zones(
    lines: List[str], landing_zone: str = "", environment: str = ""
) -> List[str]:
    """
    Filter landing zones either by exact zone name or by environment suffix.
    """
    if landing_zone:
        return [ln for ln in lines if ln.split()[1] == landing_zone]
    elif environment:
        return [ln for ln in lines if ln.split()[1].endswith(environment)]
    return []


def get_account_id(zone_line: str) -> str:
    """
    Extract account ID from a zone line (format: '<account_id> <zone_name>').
    """
    return zone_line.split()[0]
