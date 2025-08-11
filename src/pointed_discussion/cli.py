#!/usr/bin/env python3
"""Command-line interface for the pointed-discussion site generator."""

import argparse
import logging
import sys
from pathlib import Path

from pointed_discussion.logging_utils import setup_cli_logging
from pointed_discussion.sitegenerator import SiteGenerator

log = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate static site from MTG card comment data"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing JSON comment data (default: data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory for generated site (default: output)",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("images"),
        help="Directory containing downloaded card images (default: images)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="",
        help=(
            "Base URL for the site (e.g., https://gatherer.mtg.li) "
            "for generating sitemap with fully qualified URLs"
        ),
    )
    parser.add_argument(
        "--no-webp", action="store_true", help="Don't convert images to WebP format"
    )
    parser.add_argument(
        "--single-card",
        type=int,
        metavar="MULTIVERSE_ID",
        help="Generate page for a single card (proof of concept)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set up logging
    setup_cli_logging(verbose=args.verbose)

    # Validate data directory exists
    if not args.data_dir.exists():
        log.error("Data directory '%s' does not exist", args.data_dir)
        sys.exit(1)

    # Create site generator
    generator = SiteGenerator(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        images_dir=args.images_dir,
        convert_to_webp=not args.no_webp,
        base_url=args.base_url,
    )

    try:
        if args.single_card:
            # Generate single card page
            generator.generate_single_card(args.single_card)
            log.info("Generated page for multiverse ID %d", args.single_card)
            log.info(
                "View at: %s", args.output_dir / "cards" / f"{args.single_card}.html"
            )
        else:
            # Generate full site
            generator.generate_all_cards()

    except Exception as e:
        log.error("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
