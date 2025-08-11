"""Static site generator for Magic: The Gathering card comments archive."""

import logging
import re
import shutil
import string
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader

from pointed_discussion.data_utils import (
    iter_card_entries,
    load_card_name_map,
    load_scryfall_data,
)
from pointed_discussion.models import Card, Comment

log = logging.getLogger(__name__)


class SiteGenerator:
    """Generates static site from MTG card comment data."""

    def __init__(
        self,
        data_dir: Path,
        output_dir: Path,
        images_dir: Optional[Path] = None,
        convert_to_webp: bool = True,
        base_url: str = "",
    ):
        """Initialize the SiteGenerator with directories and options."""
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.images_dir = Path(images_dir) if images_dir else Path("images")
        self.convert_to_webp = convert_to_webp
        self.base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self.cards: Dict[int, Card] = {}
        self.scryfall_data: Dict[int, Dict] = {}
        self.cardmap: Dict[str, int] = {}

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

        # Load cached Scryfall data if available
        self.scryfall_data = load_scryfall_data()

        # Load card name mapping if available
        self.cardmap = load_card_name_map()

    def process_card_links(self, text: str) -> str:
        """Replace card links in text with local links to card pages."""
        # Pattern to match card links like:
        # <a href="/Pages/Card/Details.aspx?name=Progenitus" class="autoCard"
        # data:cardname="Progenitus">Progenitus</a>
        pattern = r'<a href="/Pages/Card/Details\.aspx\?name=([^"]+)" class="autoCard" data:cardname="[^"]*">([^<]+)</a>'  # noqa: E501

        def replace_link(match):
            card_name = match.group(1).replace("%20", " ")  # URL decode spaces
            link_text = match.group(2)

            target_multiverse_id = self.cardmap.get(str(card_name).lower())

            if target_multiverse_id:
                return f'<a href="../cards/{target_multiverse_id}.html" class="card-link">{link_text}</a>'  # noqa: E501
            else:
                # If we don't have the card, just return the text without a link
                return link_text

        return re.sub(pattern, replace_link, text)

    def load_card_data(self) -> None:
        """Load all card data from JSON files using shared utilities."""
        log.info("Loading card data...")

        # Use shared utility to iterate over all card entries
        for multiverse_id, card_name, comments_data in iter_card_entries(self.data_dir):
            # Convert comment data to Comment objects
            comments = []
            for comment_data in comments_data:
                comment = Comment(**comment_data)
                comments.append(comment)

            # Create or update card
            if multiverse_id in self.cards:
                # Merge comments if card already exists
                self.cards[multiverse_id].comments.extend(comments)
                self.cards[multiverse_id].comments.sort(key=lambda c: c.datetime)
            else:
                card = Card(
                    multiverse_id=multiverse_id,
                    name=card_name,
                    comments=comments,
                )

                # Enrich with cached Scryfall data if available
                if multiverse_id in self.scryfall_data:
                    scryfall_info = self.scryfall_data[multiverse_id]
                    card.set_name = scryfall_info.get("set_name")
                    card.set_code = scryfall_info.get("set_code")
                    card.artist = scryfall_info.get("artist")
                    card.collector_number = scryfall_info.get("collector_number")
                    card.released_at = scryfall_info.get("released_at")

                self.cards[multiverse_id] = card

        # Process card links in all comments after all cards are loaded
        self.process_all_card_links()

    def process_all_card_links(self) -> None:
        """Process card links in all comment text after all cards are loaded."""
        log.info("Processing card links in comments...")

        for card in self.cards.values():
            for comment in card.comments:
                comment.text_parsed = self.process_card_links(comment.text_parsed)

    def find_card_image(self, multiverse_id: int) -> Optional[str]:
        """Find existing card image in the images directory."""
        # Check for WebP format first
        webp_path = self.images_dir / f"{multiverse_id}.webp"
        if webp_path.exists():
            return str(webp_path)

        # Check for common image formats
        for ext in [".jpg", ".jpeg", ".png", ".gif"]:
            img_path = self.images_dir / f"{multiverse_id}{ext}"
            if img_path.exists():
                return str(img_path)

        return None

    def copy_card_image(self, image_path: str, multiverse_id: int) -> Optional[str]:
        """Copy card image from images directory to output directory."""
        output_images_dir = self.output_dir / "images"
        output_images_dir.mkdir(exist_ok=True)

        try:
            source_path = Path(image_path)
            filename = source_path.name
            output_path = output_images_dir / filename

            # Copy the image file
            shutil.copy2(source_path, output_path)

            return f"images/{filename}"

        except Exception as e:
            log.error("Failed to copy image for multiverse ID %d: %s", multiverse_id, e)
            return None

    def generate_card_page(self, card: Card) -> None:
        """Generate HTML page for a single card."""
        log.debug("Generating page for %s (ID: %d)", card.name, card.multiverse_id)

        # Find and copy image if available
        if not card.image_url:
            image_path = self.find_card_image(card.multiverse_id)
            if image_path:
                local_image_path = self.copy_card_image(image_path, card.multiverse_id)
                card.image_url = local_image_path
            else:
                log.warning(
                    "No image found for %s (ID: %d)", card.name, card.multiverse_id
                )

        # Create cards directory
        cards_dir = self.output_dir / "cards"
        cards_dir.mkdir(exist_ok=True)

        # Render template
        template = self.jinja_env.get_template("card.html")
        html_content = template.render(card=card)

        # Write HTML file
        card_file = cards_dir / f"{card.multiverse_id}.html"
        with open(card_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    def generate_single_card(self, multiverse_id: int) -> None:
        """Generate site for a single card (proof of concept)."""
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)

        # Load only the data we need for this card
        self.load_card_data()

        if multiverse_id not in self.cards:
            raise ValueError(
                f"Card with multiverse ID {multiverse_id} not found in data"
            )

        card = self.cards[multiverse_id]
        self.generate_card_page(card)

        # Copy CSS
        self.copy_static_files()

        log.info(
            "Generated page for %s at %s",
            card.name,
            self.output_dir / "cards" / f"{multiverse_id}.html",
        )

    def generate_all_cards(self) -> None:
        """Generate complete static site for all cards."""
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)

        # Load all card data
        self.load_card_data()

        if not self.cards:
            log.info("No cards found in data directory.")
            return

        log.info("Generating pages for %d cards...", len(self.cards))

        # Generate individual card pages
        for i, (multiverse_id, card) in enumerate(self.cards.items(), 1):
            try:
                self.generate_card_page(card)
                if i % 10 == 0 or i == len(self.cards):
                    log.info("Generated %d/%d cards...", i, len(self.cards))
            except Exception as e:
                log.error(
                    "Error generating page for %s (ID: %d): %s",
                    card.name,
                    multiverse_id,
                    e,
                )

        # Generate search/index page
        self.generate_search_page()

        # Generate sitemap
        self.generate_sitemap()

        # Copy static files
        self.copy_static_files()

        log.info("Site generation complete!")
        log.info("Output directory: %s", self.output_dir)
        log.info("Main page: %s", self.output_dir / "index.html")
        log.info("Sitemap: %s", self.output_dir / "sitemap.xml")

    def generate_search_page(self) -> None:
        """Generate the main search/index page with full functionality."""
        # Calculate statistics
        total_comments = sum(len(card.comments) for card in self.cards.values())
        cards_with_images = sum(
            1
            for card in self.cards.values()
            if self.find_card_image(card.multiverse_id)
        )

        # Sort cards by various criteria
        most_commented = sorted(
            self.cards.values(), key=lambda c: len(c.comments), reverse=True
        )[:10]

        # Calculate average ratings for cards with votes
        def get_avg_rating(card):
            if not card.comments:
                return 0
            rated_comments = [c for c in card.comments if c.vote_count > 0]
            if not rated_comments:
                return 0
            return sum(c.star_rating for c in rated_comments) / len(rated_comments)

        # Get highest rated cards (only those with at least 3 ratings)
        rated_cards = [(card, get_avg_rating(card)) for card in self.cards.values()]
        rated_cards = [
            (card, rating)
            for card, rating in rated_cards
            if rating > 0 and sum(1 for c in card.comments if c.vote_count > 0) >= 3
        ]
        highest_rated = sorted(rated_cards, key=lambda x: x[1], reverse=True)[:10]
        highest_rated = [
            {
                "name": card.name,
                "multiverse_id": card.multiverse_id,
                "display_name": card.display_name,
                "avg_rating": rating,
            }
            for card, rating in highest_rated
        ]

        # Group cards alphabetically
        cards_by_letter = defaultdict(list)
        for card in sorted(self.cards.values(), key=lambda c: c.name.lower()):
            first_char = card.name[0].upper()

            # Create enhanced card object with avg_rating
            enhanced_card = {
                "name": card.name,
                "multiverse_id": card.multiverse_id,
                "display_name": card.display_name,
                "comments": card.comments,
                "avg_rating": get_avg_rating(card),
            }

            if first_char.isdigit():
                cards_by_letter["0-9"].append(enhanced_card)
            elif first_char.isalpha():
                cards_by_letter[first_char].append(enhanced_card)
            else:
                cards_by_letter["0-9"].append(enhanced_card)

        # Create alphabet list
        alphabet = list(string.ascii_uppercase)

        # Prepare template data
        template_data = {
            "card_count": len(self.cards),
            "total_comments": total_comments,
            "cards_with_images": cards_with_images,
            "most_commented": most_commented,
            "highest_rated": highest_rated,
            "cards_by_letter": dict(cards_by_letter),
            "alphabet": alphabet,
        }

        # Render template
        template = self.jinja_env.get_template("search.html")
        html_content = template.render(**template_data)

        # Write HTML file
        index_file = self.output_dir / "index.html"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    def generate_sitemap(self) -> None:
        """Generate XML sitemap for all cards."""
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        sitemap_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]

        # Add main page
        main_url = f"{self.base_url}/index.html" if self.base_url else "index.html"
        sitemap_lines.extend(
            [
                "  <url>",
                f"    <loc>{main_url}</loc>",
                "    <priority>1.0</priority>",
                "  </url>",
            ]
        )

        # Add all card pages
        for multiverse_id, card in sorted(self.cards.items()):
            if self.base_url:
                card_url = f"{self.base_url}/cards/{multiverse_id}.html"
            else:
                card_url = f"cards/{multiverse_id}.html"
            sitemap_lines.extend(
                [
                    "  <url>",
                    f"    <loc>{card_url}</loc>",
                    "    <priority>0.8</priority>",
                    "  </url>",
                ]
            )

        sitemap_lines.append("</urlset>")

        sitemap_file = self.output_dir / "sitemap.xml"
        with open(sitemap_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sitemap_lines))

    def copy_static_files(self) -> None:
        """Copy CSS and other static files."""
        static_dir = Path(__file__).parent / "static"
        output_static_dir = self.output_dir / "static"

        if static_dir.exists():
            shutil.copytree(static_dir, output_static_dir, dirs_exist_ok=True)
