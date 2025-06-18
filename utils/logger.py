# utils/logger.py
import logging
import sys
from pathlib import Path


def setup_logger(
    name: str, log_file: str , level: str = "INFO"
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        if log_file:
            Path("logs").mkdir(exist_ok=True)
            file_handler = logging.FileHandler(f"logs/{log_file}")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
