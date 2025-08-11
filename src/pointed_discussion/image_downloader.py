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

    def __init__(self, data_dir: Path, images_dir: Path):
        """Initialize the ImageDownloader with directories."""
        self.data_dir = Path(data_dir)
        self.images_dir = Path(images_dir)

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
        """Get set of multiverse IDs that already have downloaded WebP images."""
        existing = set()

        for image_file in self.images_dir.glob("*.webp"):
            try:
                # Extract multiverse ID from filename (e.g., "97042.webp" -> 97042)
                multiverse_id = int(image_file.stem)
                existing.add(multiverse_id)
            except ValueError:
                # Skip files that don't match the expected format
                continue

        return existing

    def fetch_card_image_url(self, multiverse_id: int) -> Optional[str]:
        """Fetch card image URL from Scryfall API with rate limiting.

        Prefers PNG format over JPEG for better quality and transparency support.
        """
        try:
            # Apply rate limiting before API call
            self.rate_limiter.wait_if_needed()

            card_data = Multiverse(id=multiverse_id)

            if card_data.image_uris():
                image_uris = card_data.image_uris()
                # Prefer PNG format if available, fallback to large JPEG
                if "png" in image_uris:
                    return image_uris["png"]
                elif "large" in image_uris:
                    return image_uris["large"]
            elif card_data.card_faces():
                # For double-faced cards, use the front face
                if "image_uris" in card_data.card_faces()[0]:
                    image_uris = card_data.card_faces()[0]["image_uris"]
                    # Prefer PNG format if available, fallback to large JPEG
                    if "png" in image_uris:
                        return image_uris["png"]
                    elif "large" in image_uris:
                        return image_uris["large"]

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

            # Load image from response
            image = Image.open(BytesIO(response.content))

            # Resize image to optimal dimensions (330x459) for mobile-friendly size
            # This keeps total site under 1GB (estimated 0.97GB) while maintaining
            # good quality for card readability
            target_width, target_height = 330, 459

            # Calculate resize dimensions maintaining aspect ratio
            original_width, original_height = image.size
            aspect_ratio = original_width / original_height
            target_aspect = target_width / target_height

            if aspect_ratio > target_aspect:
                # Image is wider, scale by width
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                # Image is taller, scale by height
                new_height = target_height
                new_width = int(target_height * aspect_ratio)

            # Resize with high-quality resampling
            resized_image = image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

            # Always convert to WebP format
            filename = f"{multiverse_id}.webp"
            filepath = self.images_dir / filename

            # Convert to WebP with alpha channel preservation
            # Use lossless=False but high quality to balance size and quality
            has_alpha = (
                resized_image.mode in ('RGBA', 'LA') or
                'transparency' in resized_image.info
            )
            if has_alpha:
                # Image has alpha channel - preserve it
                resized_image.save(
                    filepath,
                    "WEBP",
                    quality=85,
                    optimize=True,
                    method=4,  # Better compression method
                    exact=True  # Preserve transparency exactly
                )
            else:
                # No alpha channel - standard WebP
                resized_image.save(filepath, "WEBP", quality=85, optimize=True)

            return True

        except Exception as e:
            log.error(
                "Failed to download image for multiverse ID %d: %s", multiverse_id, e
            )
            return False

    def download_missing_images(self,
                                multiverse_ids_to_download: set[int],
                                force_redownload: bool = False) -> None:
        """Download all missing card images."""
        if not force_redownload:
            # Skip images that already exist
            existing_images = self.get_existing_images()
            missing_ids = multiverse_ids_to_download - existing_images
            log.info(
                "Found %d existing images, %d missing",
                len(existing_images),
                len(missing_ids),
            )
        else:
            missing_ids = multiverse_ids_to_download
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
        "--force",
        action="store_true",
        help="Redownload all images, even if they already exist",
    )
    parser.add_argument(
        "--multiverse-ids",
        type=int,
        nargs="+",
        metavar="ID",
        help=(
            "Download specific images by multiverse ID "
            "(e.g., --multiverse-ids 97042 97043)"
        ),
    )

    args = parser.parse_args()

    # Validate data directory exists
    if not args.data_dir.exists():
        log.error("Data directory '%s' does not exist", args.data_dir)
        return

    # Create image downloader (always uses WebP format)
    downloader = ImageDownloader(
        data_dir=args.data_dir,
        images_dir=args.images_dir,
    )

    multiverse_ids: set[int]

    if args.multiverse_ids:
        multiverse_ids = set(args.multiverse_ids)
    else:
        # Get all multiverse IDs from data
        multiverse_ids = downloader.get_all_multiverse_ids()

    try:
        # Download images
        downloader.download_missing_images(multiverse_ids, force_redownload=args.force)

    except Exception as e:
        log.error("Error: %s", e)
        raise

def run() -> None:
    """Set up logging and run main."""
    from pointed_discussion.logging_utils import setup_cli_logging
    setup_cli_logging(verbose=True)
    log.info("Running image downloader")
    main()
