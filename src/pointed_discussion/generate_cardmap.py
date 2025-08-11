#!/usr/bin/env python3
"""Generate a mapping from card names to multiverse IDs for efficient lookups."""

import logging
from pathlib import Path

from pointed_discussion.data_utils import generate_card_name_map, save_json_data

log = logging.getLogger(__name__)


def generate_cardmap(data_dir: Path, output_file: Path) -> None:
    """Generate a mapping from card names to multiverse IDs."""
    log.info("Generating card name to multiverse ID mapping...")
    cardmap = generate_card_name_map(data_dir)
    save_json_data(
        cardmap,
        output_file,
        f"card mapping with {len(cardmap)} unique card names"
    )


def main() -> None:
    """Main entry point."""
    data_dir = Path("data")
    output_file = Path("scryfall") / "cardmap.json"

    if not data_dir.exists():
        log.error("Data directory not found: %s", data_dir)
        return

    generate_cardmap(data_dir, output_file)


def run() -> None:
    """Set up logging and run main."""
    from pointed_discussion.logging_utils import setup_cli_logging
    setup_cli_logging(verbose=True)
    main()
