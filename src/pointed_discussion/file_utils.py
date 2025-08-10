#!/usr/bin/env python3
"""Common file and path utilities."""

import logging
import shutil
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)


def copy_file_safe(
    source_path: Path, dest_path: Path, description: str = "file"
) -> bool:
    """Safely copy a file with error handling and logging.

    Args:
        source_path: Source file path
        dest_path: Destination file path
        description: Human-readable description for logging

    Returns:
        True if copy succeeded, False otherwise

    """
    try:
        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy the file
        shutil.copy2(source_path, dest_path)
        return True

    except Exception as e:
        log.error(
            f"Failed to copy {description} from {source_path} to {dest_path}: {e}"
        )
        return False


def copy_tree_safe(
    source_dir: Path, dest_dir: Path, description: str = "directory"
) -> bool:
    """Safely copy a directory tree with error handling.

    Args:
        source_dir: Source directory path
        dest_dir: Destination directory path
        description: Human-readable description for logging

    Returns:
        True if copy succeeded, False otherwise

    """
    try:
        shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
        return True

    except Exception as e:
        log.error(
            f"Failed to copy {description} from {source_dir} to {dest_dir}: {e}"
        )
        return False


def find_files_by_extensions(directory: Path, extensions: List[str]) -> List[Path]:
    """Find all files in directory with specified extensions.

    Args:
        directory: Directory to search in
        extensions: List of file extensions (with or without dots)

    Returns:
        List of matching file paths

    """
    # Normalize extensions to include dots
    normalized_extensions = []
    for ext in extensions:
        if not ext.startswith("."):
            ext = f".{ext}"
        normalized_extensions.append(ext)

    matches = []
    if directory.exists():
        for ext in normalized_extensions:
            matches.extend(directory.rglob(f"*{ext}"))

    return matches


def get_file_size_human(file_path: Path) -> str:
    """Get human-readable file size.

    Args:
        file_path: Path to file

    Returns:
        Human-readable size string (e.g., "1.5 MB")

    """
    if not file_path.exists():
        return "0 B"

    size = file_path.stat().st_size

    # Convert to human readable format
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def clean_filename(filename: str) -> str:
    """Clean filename to be filesystem-safe.

    Args:
        filename: Original filename

    Returns:
        Cleaned filename safe for filesystem use

    """
    # Replace problematic characters
    unsafe_chars = '<>:"/\\|?*'
    cleaned = filename
    for char in unsafe_chars:
        cleaned = cleaned.replace(char, "_")

    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip(" .")

    # Ensure it's not empty
    if not cleaned:
        cleaned = "untitled"

    return cleaned
