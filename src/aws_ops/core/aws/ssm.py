"""Simple SSM Manager for AWS operations."""

from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_ops.utils.logger import setup_logger


class SSMManager:
    """Simple AWS SSM resource manager."""

    def __init__(self, session: boto3.Session, region: str = "ap-southeast-2"):
        """Initialize SSMManager."""
        self.session = session
        self.region = region
        self.ssm_client = session.client("ssm", region_name=region)
        self.logger = setup_logger(__name__, "ssm_manager.log")

    def get_parameter(self, name: str, with_decryption: bool = True) -> Optional[str]:
        """Get SSM parameter value."""
        try:
            response = self.ssm_client.get_parameter(
                Name=name, WithDecryption=with_decryption
            )
            return response["Parameter"]["Value"]
        except ClientError as e:
            self.logger.error(f"Error getting parameter {name}: {e}")
            return None

    def get_parameters(self, names: List[str], with_decryption: bool = True) -> Dict[str, str]:
        """Get multiple SSM parameters."""
        try:
            response = self.ssm_client.get_parameters(
                Names=names, WithDecryption=with_decryption
            )
            return {param["Name"]: param["Value"] for param in response["Parameters"]}
        except ClientError as e:
            self.logger.error(f"Error getting parameters: {e}")
            return {}

    def put_parameter(
        self, name: str, value: str, parameter_type: str = "String", overwrite: bool = True
    ) -> bool:
        """Put SSM parameter."""
        try:
            self.ssm_client.put_parameter(
                Name=name, Value=value, Type=parameter_type, Overwrite=overwrite
            )
            self.logger.info(f"Parameter {name} updated successfully")
            return True
        except ClientError as e:
            self.logger.error(f"Error putting parameter {name}: {e}")
            return False


def create_ssm_manager(session: boto3.Session, region: str = "ap-southeast-2") -> SSMManager:
    """Create SSMManager instance."""
    return SSMManager(session, region)