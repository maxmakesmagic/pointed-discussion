"""Common data access utilities for the pointed_discussion library."""

import json
import logging
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

log = logging.getLogger(__name__)


def parse_data_key(key: str) -> Tuple[int, str]:
    """Parse a data file key into multiverse ID and card name."""
    multiverse_id_str, card_name = key.split(": ", 1)
    return int(multiverse_id_str), card_name


def load_multiverse_ids(data_dir: Path) -> Set[int]:
    """Load all unique multiverse IDs from data files."""
    multiverse_ids = set()

    for _, data in iter_data_files(data_dir):
        for key in data.keys():
            multiverse_id, _ = parse_data_key(key)
            multiverse_ids.add(multiverse_id)

    return multiverse_ids


def iter_data_files(data_dir: Path) -> Iterator[Tuple[Path, Dict]]:
    """Iterate over all data files, yielding path and parsed JSON content."""
    for json_file in data_dir.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            yield json_file, data
        except Exception as e:
            log.warning("Error processing %s: %s", json_file, e)


def iter_card_entries(data_dir: Path) -> Iterator[Tuple[int, str, List[Dict]]]:
    """Iterate over all card entries across all data files.

    Args:
        data_dir: Directory containing JSON data files

    Yields:
        Tuple of (multiverse_id, card_name, comments_data)

    """
    for _, data in iter_data_files(data_dir):
        for key, comments_data in data.items():
            multiverse_id, card_name = parse_data_key(key)
            yield multiverse_id, card_name, comments_data


def generate_card_name_map(data_dir: Path) -> Dict[str, int]:
    """Generate a mapping from card names (lowercase) to multiverse IDs.

    For duplicate card names, the first encountered multiverse ID is kept.

    Args:
        data_dir: Directory containing JSON data files

    Returns:
        Dictionary mapping lowercase card names to multiverse IDs

    """
    cardmap = {}

    for multiverse_id, card_name, _ in iter_card_entries(data_dir):
        card_name_lower = card_name.lower()
        if card_name_lower not in cardmap:
            cardmap[card_name_lower] = multiverse_id

    return cardmap


def load_scryfall_data(scryfall_file: Optional[Path] = None) -> Dict[int, Dict]:
    """Load cached Scryfall data from JSON file.

    Args:
        scryfall_file: Path to scryfall data file. Defaults to "scryfall/data.json"

    Returns:
        Dictionary mapping multiverse IDs to Scryfall metadata

    """
    if scryfall_file is None:
        scryfall_file = Path("scryfall") / "data.json"

    if not scryfall_file.exists():
        log.info("No Scryfall data found at %s", scryfall_file)
        return {}

    try:
        with open(scryfall_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Convert string keys to int keys
        return {int(k): v for k, v in data.items()}
    except Exception as e:
        log.error("Error loading Scryfall data from %s: %s", scryfall_file, e)
        return {}


def load_card_name_map(cardmap_file: Optional[Path] = None) -> Dict[str, int]:
    """Load cached card name to multiverse ID mapping.

    Args:
        cardmap_file: Path to cardmap file. Defaults to "scryfall/cardmap.json"

    Returns:
        Dictionary mapping lowercase card names to multiverse IDs

    """
    if cardmap_file is None:
        cardmap_file = Path("scryfall") / "cardmap.json"

    if not cardmap_file.exists():
        log.info("No card mapping found at %s", cardmap_file)
        return {}

    try:
        with open(cardmap_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Error loading card mapping from %s: %s", cardmap_file, e)
        return {}


def save_json_data(data: Dict, output_file: Path, description: str = "data") -> None:
    """Save data to JSON file with error handling and feedback.

    Args:
        data: Data to save
        output_file: Path to output file
        description: Human-readable description for logging

    """
    try:
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write the data to JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        log.info("Saved %s to: %s", description, output_file)

    except Exception as e:
        log.error("Error saving %s to %s: %s", description, output_file, e)
        raise
