"""
logger.py - Structured Application Logging
-------------------------------------------
Provides a consistent logger used across all modules.
Using Python's built-in logging module configured for readability.

Why structured logging?
- Makes debugging easier during development
- Essential for monitoring in production
- Shows timestamps, module name, and log level clearly
"""

import logging
import sys
from backend.config import settings


def get_logger(name: str) -> logging.Logger:
    """
    Creates and returns a configured logger for a given module.
    
    Usage:
        from backend.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Server started")
    
    Args:
        name: Typically __name__ of the calling module
    
    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Set log level based on DEBUG mode in config
    level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(level)

    # Create a console handler (outputs to terminal)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Format: [2024-01-01 12:00:00] INFO     backend.main - Server started
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger