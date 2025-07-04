"""Base job class for AWS operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import boto3
import uuid
from aws_ops.utils.logger import setup_logger
from aws_ops.utils.config import ConfigManager
from aws_ops.utils.session import SessionManager


class BaseJob(ABC):
    """Base class for all AWS operations jobs."""
    
    # Class-level configuration cache
    _config_manager: Optional[ConfigManager] = None
    _cached_config: Optional[Dict[str, Any]] = None

    def __init__(self, config_manager=None, job_name: str = None, default_role: str = 'provision'):
        """Initialize the job with configuration."""
        # Use provided config_manager or create/reuse cached one
        if config_manager is not None:
            self.config_manager = config_manager
        else:
            self.config_manager = self._get_or_create_config_manager()
        
        self.job_name = job_name or self.__class__.__name__.lower().replace('job', '')
        self.default_role = default_role
        self.correlation_id = str(uuid.uuid4())[:8]  # Short correlation ID for tracking
        
        # Cache configuration for efficient access
        self.config = self._get_cached_config()
        
        # Setup enhanced logger
        self.logger = setup_logger(
            name=self.__class__.__module__,
            log_file=f"{self.job_name}.log"
        )
    
    @classmethod
    def _get_or_create_config_manager(cls) -> ConfigManager:
        """Get or create a cached ConfigManager instance."""
        if cls._config_manager is None:
            cls._config_manager = ConfigManager()
        return cls._config_manager
    
    @classmethod
    def _get_cached_config(cls) -> Dict[str, Any]:
        """Get cached configuration, loading if necessary."""
        if cls._cached_config is None:
            config_manager = cls._get_or_create_config_manager()
            cls._cached_config = config_manager.config
        return cls._cached_config
    
    @classmethod
    def reload_config(cls) -> None:
        """Force reload of configuration from file."""
        cls._cached_config = None
        if cls._config_manager is not None:
            cls._config_manager.reload_config()
    
    def create_aws_session(self, zone_info: Dict[str, Any], role_type: str = None, operation_name: str = None) -> 'boto3.Session':
        """
        Create AWS session for the zone with role assumption
        """
        operation_name = operation_name or self.job_name
        role_type = role_type or self.default_role
        # Use proper nested config access for roles
        aws_config = self.config.get('aws', {})
        roles_config = aws_config.get('roles', {})
        role_name = roles_config.get(role_type)
        
        account_id = str(zone_info.get('account_id'))  # Ensure account_id is always a string
        account_name = zone_info.get('name', account_id)
        region = aws_config.get('region', 'ap-southeast-2')
        
        # Enhanced logging with correlation ID and structured data
        if hasattr(self.logger.handlers[0], 'formatter') and hasattr(self.logger.handlers[0].formatter, 'add_fields'):
            # Structured logging
            self.logger.info(
                f"Creating AWS session for account {account_name} ({account_id}) with role {role_name}",
                extra={
                    'correlation_id': self.correlation_id,
                    'account_id': account_id,
                    'account_name': account_name,
                    'role_name': role_name,
                    'operation': operation_name,
                    'region': region
                }
            )
        else:
            # Standard logging
            self.logger.info(
                f"[{self.correlation_id}] Creating AWS session for account {account_name} ({account_id}) with role {role_name} in {region}"
            )
        
        # Validate role configuration
        if not role_name:
            raise ValueError(f"Role '{role_type}' not found in AWS configuration. Available roles: {list(roles_config.keys())}")
        
        if role_name and account_id:
            # Use SessionManager to assume role in target account
            return SessionManager.get_session(
                account_id=account_id,
                account_name=account_name,
                role=role_name,
                region=region,
                role_session_name=operation_name
            )
        else:
            # Use SessionManager to get session from environment
            return SessionManager.get_session_from_env(region=region)

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the job with given parameters."""
        pass
