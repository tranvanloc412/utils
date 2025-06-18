#!/usr/bin/env python3
"""
main.py
-------
Main entry point for AWS Operations utility scripts.

This script provides a command-line interface to run various utility jobs
for AWS operations including:
- Fetching landing zones
- Listing old snapshots
- Reviewing approved landing zones

Usage:
    python main.py <job_name> [job_arguments]

Available jobs:
    fetch-zones         - Fetch landing zones from configured endpoints
    list-snapshots      - List EC2 snapshots older than 30 days
    review-lzs          - Review approved landing zones against snapshot reports
    
Examples:
    python main.py fetch-zones
    python main.py list-snapshots
    python main.py review-lzs --approved approved_lzs.csv --report snapshot_report.csv

For job-specific help:
    python main.py <job_name> --help
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

from utils.logger import setup_logger

# Available jobs mapping
JOBS = {
    'fetch-zones': {
        'script': 'jobs/fetch_landing_zones.py',
        'description': 'Fetch landing zones from configured HTTP endpoints'
    },
    'list-snapshots': {
        'script': 'jobs/list_old_snapshots.py', 
        'description': 'List EC2 snapshots older than 30 days in target AWS account'
    },
    'review-lzs': {
        'script': 'jobs/review_approved_lzs.py',
        'description': 'Review approved landing zones against snapshot reports'
    }
}


def setup_main_parser() -> argparse.ArgumentParser:
    """Setup the main argument parser."""
    parser = argparse.ArgumentParser(
        description='AWS Operations Utility Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available jobs:
{chr(10).join([f'  {name:<15} - {info["description"]}' for name, info in JOBS.items()])}

Examples:
  python main.py fetch-zones
  python main.py list-snapshots  
  python main.py review-lzs --approved approved.csv --report report.csv

For job-specific help:
  python main.py <job_name> --help
        """
    )
    
    parser.add_argument(
        'job',
        choices=list(JOBS.keys()),
        help='Job to execute'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def run_job(job_name: str, job_args: List[str], verbose: bool = False) -> int:
    """Run a specific job with given arguments.
    
    Args:
        job_name: Name of the job to run
        job_args: Arguments to pass to the job script
        verbose: Enable verbose logging
        
    Returns:
        Exit code from the job script
    """
    logger = setup_logger('main', level='DEBUG' if verbose else 'INFO')
    
    if job_name not in JOBS:
        logger.error(f"Unknown job: {job_name}")
        logger.info(f"Available jobs: {', '.join(JOBS.keys())}")
        return 1
    
    job_info = JOBS[job_name]
    script_path = Path(__file__).parent / job_info['script']
    
    if not script_path.exists():
        logger.error(f"Job script not found: {script_path}")
        return 1
    
    # Prepare command
    cmd = [sys.executable, str(script_path)] + job_args
    
    logger.info(f"Running job: {job_name}")
    logger.info(f"Description: {job_info['description']}")
    if verbose:
        logger.debug(f"Command: {' '.join(cmd)}")
    
    try:
        # Run the job script
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            check=False  # Don't raise exception on non-zero exit
        )
        
        if result.returncode == 0:
            logger.info(f"Job '{job_name}' completed successfully")
        else:
            logger.error(f"Job '{job_name}' failed with exit code {result.returncode}")
            
        return result.returncode
        
    except KeyboardInterrupt:
        logger.warning(f"Job '{job_name}' interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Failed to run job '{job_name}': {e}")
        return 1


def main() -> int:
    """Main entry point."""
    # Parse known args to separate main args from job args
    parser = setup_main_parser()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    # Parse only the job name and main flags first
    try:
        # Find where job args start (after the job name)
        job_arg_start = 2  # Default: after 'main.py job_name'
        
        # Handle verbose flag
        args_copy = sys.argv[1:]
        verbose = False
        if '--verbose' in args_copy or '-v' in args_copy:
            verbose = True
            args_copy = [arg for arg in args_copy if arg not in ['--verbose', '-v']]
        
        if not args_copy:
            parser.print_help()
            return 0
            
        job_name = args_copy[0]
        job_args = args_copy[1:] if len(args_copy) > 1 else []
        
        # Validate job name
        if job_name not in JOBS:
            if job_name in ['--help', '-h']:
                parser.print_help()
                return 0
            print(f"Error: Unknown job '{job_name}'")
            print(f"Available jobs: {', '.join(JOBS.keys())}")
            return 1
        
        return run_job(job_name, job_args, verbose)
        
    except Exception as e:
        print(f"Error parsing arguments: {e}")
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())