"""AWS Core Module

This module provides core AWS functionality for the aws-ops package.
"""

from .ec2 import EC2Manager, create_ec2_manager

__all__ = [
    'EC2Manager',
    'create_ec2_manager'
]