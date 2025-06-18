import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils import setup_logger, get_aws_region, get_provision_role, SessionManager

logger = setup_logger(__name__, log_file="assume_role.log")


def main():
    # Example landing zone metadata
    account_id = "954976297051"
    account_name = "dev"
    role = get_provision_role()
    region = get_aws_region()
    role_session_name = "demo-session"

    # Initialize the session manager
    sm = SessionManager()

    # Get a session (this will call STS assume-role or use cache)
    try:
        session = sm.get_session(
            account_id, account_name, role, region, role_session_name
        )
        logger.info(
            f"Successfully assumed role and created session for {account_name} in {region}"
        )
    except Exception as e:
        print(f"Failed to create session: {e}")


if __name__ == "__main__":
    main()
