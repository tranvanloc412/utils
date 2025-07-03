# utils/logger.py
import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logger(
    name: str,
    log_file: str,
    level: str = "INFO",
    enable_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Setup logger with enhanced enterprise features"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Prevent duplicate handlers
    if not logger.handlers:
        # Standard formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler for immediate feedback
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)  # Only INFO and above to console
        logger.addHandler(stream_handler)

        # File handler with rotation if log_file is specified
        if log_file:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            log_path = logs_dir / log_file

            try:
                if enable_rotation:
                    # Use rotating file handler for production
                    file_handler = logging.handlers.RotatingFileHandler(
                        log_path,
                        maxBytes=max_bytes,
                        backupCount=backup_count,
                        encoding="utf-8",
                    )
                else:
                    # Use basic file handler
                    file_handler = logging.FileHandler(log_path, encoding="utf-8")

                file_handler.setFormatter(formatter)
                file_handler.setLevel(logging.DEBUG)  # All levels to file
                logger.addHandler(file_handler)

            except (OSError, PermissionError) as e:
                # Fallback: log to console if file creation fails
                logger.warning(
                    f"Failed to create log file {log_path}: {e}. Logging to console only."
                )

        # Prevent propagation to root logger to avoid duplicate messages
        logger.propagate = False

    return logger
