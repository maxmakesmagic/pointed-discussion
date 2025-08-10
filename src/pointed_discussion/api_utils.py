#!/usr/bin/env python3
"""Common API utilities for Scryfall API access."""

import logging
import time
from typing import Dict, Optional

from scrython.cards import Multiverse

log = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API calls to respect Scryfall's rate limits.

    Scryfall allows ~10 requests/second, so we use a conservative 9 req/sec.
    """

    def __init__(self, max_calls_per_second: float = 9.0):
        """Initialize rate limiter with a conservative limit.

        Args:
            max_calls_per_second: Maximum API calls per second

        """
        self.max_calls_per_second = max_calls_per_second
        self.min_interval = 1.0 / max_calls_per_second
        self.last_call_time = 0

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)

        self.last_call_time = time.time()

    def sleep_for_rate_limit(self) -> None:
        """Alias for wait_if_needed for backward compatibility."""
        self.wait_if_needed()


def fetch_card_metadata(
    multiverse_id: int, rate_limiter: RateLimiter
) -> Optional[Dict]:
    """Fetch card metadata from Scryfall API with rate limiting.

    Args:
        multiverse_id: The multiverse ID to fetch
        rate_limiter: Rate limiter instance

    Returns:
        Dictionary of card metadata, or None if fetch failed

    """
    rate_limiter.wait_if_needed()

    try:
        card = Multiverse(id=multiverse_id)

        # Basic required fields
        metadata = {
            "multiverse_id": multiverse_id,
            "name": card.name(),
            "set_name": card.set_name(),
            "set_code": str(card.set_code()).upper(),
            "artist": card.artist(),
            "released_at": card.released_at(),
            "scryfall_id": card.id(),
        }

        # Optional fields that might not exist on all cards
        optional_fields = [
            ("mana_cost", "mana_cost"),
            ("type_line", "type_line"),
            ("rarity", "rarity"),
            ("collector_number", "collector_number"),
            ("cmc", "cmc"),
            ("image_uris", "image_uris"),
        ]

        for field_name, method_name in optional_fields:
            try:
                if hasattr(card, method_name):
                    value = getattr(card, method_name)()
                    metadata[field_name] = value
                else:
                    metadata[field_name] = None
            except Exception as e:
                log.debug(
                    "Could not get %s for multiverse ID %d: %s",
                    field_name,
                    multiverse_id,
                    e,
                )
                metadata[field_name] = None

        return metadata

    except Exception as e:
        log.error("Error fetching data for multiverse ID %d: %s", multiverse_id, e)
        return None


def get_card_image_url(
    card_metadata: Dict, image_type: str = "normal"
) -> Optional[str]:
    """Extract image URL from card metadata.

    Args:
        card_metadata: Card metadata from Scryfall
        image_type: Type of image (normal, large, small, art_crop, etc.)

    Returns:
        Image URL string, or None if not available

    """
    image_uris = card_metadata.get("image_uris")
    if not image_uris:
        return None

    return image_uris.get(image_type)
