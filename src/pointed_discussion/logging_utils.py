#!/usr/bin/env python3
"""Common logging utilities for the pointed_discussion library."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> None:
    """Set up logging with a sensible formatter for console output.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)

    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)

    # Add handler to logger
    root_logger.addHandler(console_handler)

    # Quieten down PIL and urllib3
    logging.getLogger("PIL").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)


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
        level=level, format_string=format_string
    )
