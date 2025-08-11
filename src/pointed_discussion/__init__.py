"""Pointed Discussion: Static site generator for Magic: The Gathering card comments.

This library provides tools to generate static websites from archived MTG card
comment data, including utilities for data processing, image downloading, and
site generation.
"""

from .api_utils import RateLimiter, fetch_card_metadata
from .data_utils import (
    iter_card_entries,
    iter_data_files,
    load_card_name_map,
    load_multiverse_ids,
    load_scryfall_data,
    parse_data_key,
)
from .models import Card, Comment

__version__ = "0.1.0"

__all__ = [
    # Data models
    "Card",
    "Comment",
    # Data utilities
    "iter_card_entries",
    "iter_data_files",
    "load_card_name_map",
    "load_multiverse_ids",
    "load_scryfall_data",
    "parse_data_key",
    # API utilities
    "RateLimiter",
    "fetch_card_metadata",
]
