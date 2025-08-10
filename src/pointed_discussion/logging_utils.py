#!/usr/bin/env python3
"""Common logging utilities for the pointed_discussion library."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    logger_name: Optional[str] = None,
) -> None:
    """Set up logging with a sensible formatter for console output.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
        logger_name: Name for the logger (optional, defaults to package name)

    """
    if logger_name is None:
        logger_name = "pointed_discussion"

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)


# Set up package-level logger with nice formatting for CLI tools
def setup_cli_logging(verbose: bool = False) -> None:
    """Set up logging specifically for CLI tools with clean output.

    Args:
        verbose: If True, show DEBUG messages

    """
    level = logging.DEBUG if verbose else logging.INFO

    # Use a cleaner format for CLI tools
    format_string = "%(levelname)s: %(message)s"

    setup_logging(
        level=level, format_string=format_string, logger_name="pointed_discussion"
    )
