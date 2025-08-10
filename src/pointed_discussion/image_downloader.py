"""Image downloader for Magic: The Gathering cards from Scryfall API.

Downloads images once and stores them locally for reuse.
"""

import argparse
import json
import logging
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, Set

import requests
from PIL import Image
from scrython.cards import Multiverse

log = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API calls to respect Scryfall's 10 requests/second limit."""

    def __init__(self, max_calls_per_second: float = 9.0):
        """Initialize rate limiter with a conservative limit."""
        self.max_calls_per_second = max_calls_per_second
        self.min_interval = 1.0 / max_calls_per_second
        self.last_call_time = 0

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)

        self.last_call_time = time.time()


class ImageDownloader:
    """Downloads and processes card images from Scryfall API."""

    def __init__(self, data_dir: Path, images_dir: Path, convert_to_webp: bool = True):
        """Initialize the ImageDownloader with directories and options."""
        self.data_dir = Path(data_dir)
        self.images_dir = Path(images_dir)
        self.convert_to_webp = convert_to_webp

        # Rate limiter for Scryfall API calls (conservative 9 req/sec)
        self.rate_limiter = RateLimiter(max_calls_per_second=9.0)

        # Ensure images directory exists
        self.images_dir.mkdir(exist_ok=True)

    def get_all_multiverse_ids(self) -> Set[int]:
        """Extract all unique multiverse IDs from the data files."""
        log.info("Scanning data files for multiverse IDs...")
        multiverse_ids = set()

        for json_file in self.data_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for key in data.keys():
                    # Parse key format: "multiverse_id: card_name"
                    multiverse_id_str = key.split(": ", 1)[0]
                    multiverse_ids.add(int(multiverse_id_str))

            except Exception as e:
                log.error("Error processing %s: %s", json_file, e)

        log.info("Found %d unique multiverse IDs", len(multiverse_ids))
        return multiverse_ids

    def get_existing_images(self) -> Set[int]:
        """Get set of multiverse IDs that already have downloaded images."""
        existing = set()

        if self.convert_to_webp:
            pattern = "*.webp"
        else:
            pattern = "*.*"

        for image_file in self.images_dir.glob(pattern):
            try:
                # Extract multiverse ID from filename (e.g., "97042.webp" -> 97042)
                multiverse_id = int(image_file.stem)
                existing.add(multiverse_id)
            except ValueError:
                # Skip files that don't match the expected format
                continue

        return existing

    def fetch_card_image_url(self, multiverse_id: int) -> Optional[str]:
        """Fetch card image URL from Scryfall API with rate limiting."""
        try:
            # Apply rate limiting before API call
            self.rate_limiter.wait_if_needed()

            card_data = Multiverse(id=multiverse_id)

            if card_data.image_uris():
                return card_data.image_uris()["large"]
            elif card_data.card_faces():
                # For double-faced cards, use the front face
                if "image_uris" in card_data.card_faces()[0]:
                    return card_data.card_faces()[0]["image_uris"]["large"]

        except Exception as e:
            log.error(
                "Failed to fetch image URL for multiverse ID %d: %s", multiverse_id, e
            )

        return None

    def download_and_process_image(self, image_url: str, multiverse_id: int) -> bool:
        """Download and optionally convert a single image."""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # Determine file extension and path
            if self.convert_to_webp:
                filename = f"{multiverse_id}.webp"
                filepath = self.images_dir / filename

                # Convert to WebP
                image = Image.open(BytesIO(response.content))
                image.save(filepath, "WEBP", quality=85, optimize=True)
            else:
                # Keep original format
                from urllib.parse import urlparse

                parsed_url = urlparse(image_url)
                extension = Path(parsed_url.path).suffix or ".jpg"
                filename = f"{multiverse_id}{extension}"
                filepath = self.images_dir / filename

                with open(filepath, "wb") as f:
                    f.write(response.content)

            return True

        except Exception as e:
            log.error(
                "Failed to download image for multiverse ID %d: %s", multiverse_id, e
            )
            return False

    def download_missing_images(self, force_redownload: bool = False) -> None:
        """Download all missing card images."""
        # Get all multiverse IDs from data
        all_multiverse_ids = self.get_all_multiverse_ids()

        if not force_redownload:
            # Skip images that already exist
            existing_images = self.get_existing_images()
            missing_ids = all_multiverse_ids - existing_images
            log.info(
                "Found %d existing images, %d missing",
                len(existing_images),
                len(missing_ids),
            )
        else:
            missing_ids = all_multiverse_ids
            log.info("Force redownload: processing all %d images", len(missing_ids))

        if not missing_ids:
            log.info("All images already downloaded!")
            return

        log.info("Downloading %d images...", len(missing_ids))
        log.info("Rate limiting API calls to respect Scryfall's limits...")

        success_count = 0
        failed_count = 0

        for i, multiverse_id in enumerate(sorted(missing_ids), 1):
            try:
                log.debug(
                    "[%d/%d] Fetching image for multiverse ID %d",
                    i,
                    len(missing_ids),
                    multiverse_id,
                )

                # Get image URL from Scryfall
                image_url = self.fetch_card_image_url(multiverse_id)

                if image_url:
                    # Download and process the image
                    if self.download_and_process_image(image_url, multiverse_id):
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    log.warning(
                        "No image URL found for multiverse ID %d", multiverse_id
                    )
                    failed_count += 1

                # Progress update every 25 images
                if i % 25 == 0 or i == len(missing_ids):
                    log.info(
                        "Progress: %d/%d processed, %d successful, %d failed",
                        i,
                        len(missing_ids),
                        success_count,
                        failed_count,
                    )

            except Exception as e:
                log.error("Error processing multiverse ID %d: %s", multiverse_id, e)
                failed_count += 1

        log.info("Image download complete!")
        log.info("Successfully downloaded: %d", success_count)
        log.info("Failed downloads: %d", failed_count)
        log.info("Images stored in: %s", self.images_dir)


def main() -> None:
    """Main entry point for image downloader."""
    parser = argparse.ArgumentParser(
        description="Download MTG card images from Scryfall API"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing JSON comment data (default: data)",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("images"),
        help="Directory to store downloaded images (default: images)",
    )
    parser.add_argument(
        "--no-webp", action="store_true", help="Don't convert images to WebP format"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload all images, even if they already exist",
    )

    args = parser.parse_args()

    # Validate data directory exists
    if not args.data_dir.exists():
        log.error("Data directory '%s' does not exist", args.data_dir)
        return

    # Create image downloader
    downloader = ImageDownloader(
        data_dir=args.data_dir,
        images_dir=args.images_dir,
        convert_to_webp=not args.no_webp,
    )

    try:
        # Download missing images
        downloader.download_missing_images(force_redownload=args.force)

    except Exception as e:
        log.error("Error: %s", e)
        raise

def run() -> None:
    """Set up logging and run main."""
    from pointed_discussion.logging_utils import setup_cli_logging
    setup_cli_logging(verbose=True)
    main()
