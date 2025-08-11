#!/usr/bin/env python3
"""Script to fetch additional card metadata from Scryfall API and cache it locally.

This only needs to be run once since historical card data doesn't change.
"""

import argparse
import json
import logging
from pathlib import Path

from pointed_discussion.api_utils import RateLimiter, fetch_card_metadata
from pointed_discussion.data_utils import load_multiverse_ids

log = logging.getLogger(__name__)


def main() -> None:
    """Main function to fetch and cache all card metadata."""
    parser = argparse.ArgumentParser(
        description="Fetch and cache Scryfall card metadata."
    )
    parser.add_argument(
        "data_dir",
        type=Path,
        default=Path("data"),
        help="Directory containing JSON comment data (default: data)",
    )
    args = parser.parse_args()

    data_path = args.data_dir
    scryfall_dir = Path("scryfall")
    output_file = scryfall_dir / "data.json"

    if not data_path.exists():
        log.error("Data directory %s not found!", data_path)
        return

    # Ensure scryfall directory exists
    scryfall_dir.mkdir(exist_ok=True)

    # Load existing data if it exists
    existing_data = {}
    if output_file.exists():
        log.info("Loading existing data from %s", output_file)
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        log.info("Loaded %d existing entries", len(existing_data))

    # Get all multiverse IDs
    all_ids = load_multiverse_ids(data_path)

    # Filter out IDs we already have
    existing_ids = {int(k) for k in existing_data.keys()}
    new_ids = all_ids - existing_ids

    log.info("Need to fetch data for %d new cards", len(new_ids))

    if not new_ids:
        log.info("All cards already have cached metadata!")
        return

    # Create rate limiter for API calls
    rate_limiter = RateLimiter(max_calls_per_second=9.0)

    log.info("Fetching card metadata from Scryfall...")
    log.info("This may take a while - please be patient!")

    successful = 0
    failed = 0

    for i, multiverse_id in enumerate(sorted(new_ids), 1):
        log.debug("Fetching multiverse ID %d (%d/%d)", multiverse_id, i, len(new_ids))

        metadata = fetch_card_metadata(multiverse_id, rate_limiter)
        if metadata:
            existing_data[str(multiverse_id)] = metadata
            successful += 1
        else:
            failed += 1

        # Save progress every 50 cards
        if i % 50 == 0:
            log.info(
                "Saving progress... (%d successful, %d failed)", successful, failed
            )
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

    # Final save
    log.info("Saving final results to %s", output_file)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    log.info("✅ Completed!")
    log.info("   📊 Total cards: %d", len(all_ids))
    log.info("   ✅ Successful: %d", successful)
    log.info("   ❌ Failed: %d", failed)
    log.info("   📁 Output file: %s", output_file)


def run() -> None:
    """Run the main function with CLI logging setup."""
    from pointed_discussion.logging_utils import setup_cli_logging

    setup_cli_logging()
    main()
