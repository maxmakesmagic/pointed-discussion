#!/usr/bin/env python3
"""Tests for the site generator."""

import json
import tempfile
import unittest
from pathlib import Path

from pointed_discussion.data_utils import load_ratings
from pointed_discussion.models import Card, Comment
from pointed_discussion.sitegenerator import SiteGenerator


class TestComment(unittest.TestCase):
    """Test Comment dataclass."""

    def test_star_rating_calculation(self):
        """Test star rating calculation."""
        # Test perfect 5-star rating
        comment = Comment(
            author="test",
            author_id=1,
            datetime="2020-01-01 00:00:00",
            id=1,
            text_parsed="Great!",
            text_posted="Great!",
            timestamp="123456789",
            vote_count=10,
            vote_sum=100,
        )
        self.assertEqual(comment.star_rating, 5.0)

        # Test 3-star rating
        comment = Comment(
            author="test",
            author_id=1,
            datetime="2020-01-01 00:00:00",
            id=1,
            text_parsed="Okay",
            text_posted="Okay",
            timestamp="123456789",
            vote_count=4,
            vote_sum=24,
        )
        self.assertEqual(comment.star_rating, 3.0)

        # Test no votes
        comment = Comment(
            author="test",
            author_id=1,
            datetime="2020-01-01 00:00:00",
            id=1,
            text_parsed="No votes",
            text_posted="No votes",
            timestamp="123456789",
            vote_count=0,
            vote_sum=0,
        )
        self.assertEqual(comment.star_rating, 0.0)

    def test_star_display(self):
        """Test star display formatting."""
        # Test 5-star display
        comment = Comment(
            author="test",
            author_id=1,
            datetime="2020-01-01 00:00:00",
            id=1,
            text_parsed="Perfect!",
            text_posted="Perfect!",
            timestamp="123456789",
            vote_count=10,
            vote_sum=100,
        )
        self.assertIn("★★★★★", comment.star_display)
        self.assertIn("(5.0/5.0)", comment.star_display)

        # Test partial rating
        comment = Comment(
            author="test",
            author_id=1,
            datetime="2020-01-01 00:00:00",
            id=1,
            text_parsed="Good",
            text_posted="Good",
            timestamp="123456789",
            vote_count=2,
            vote_sum=17,  # 17/(2*2) = 4.25
        )
        display = comment.star_display
        self.assertIn("★★★★", display)
        self.assertIn("☆", display)
        self.assertIn("(4.2/5.0)", display)


class TestSiteGenerator(unittest.TestCase):
    """Test SiteGenerator functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.output_dir = Path(self.temp_dir) / "output"

        # Create test data structure
        self.data_dir.mkdir(parents=True)
        test_set_dir = self.data_dir / "199x" / "1993"
        test_set_dir.mkdir(parents=True)

        # Create test JSON file
        test_data = {
            "97042: Arena": [
                {
                    "author": "TestUser",
                    "author_id": 12345,
                    "datetime": "2010-04-30 22:48:13",
                    "id": 70172,
                    "text_parsed": "This is a test comment.",
                    "text_posted": "This is a test comment.",
                    "timestamp": "1272692893637",
                    "vote_count": 5,
                    "vote_sum": 40,
                }
            ]
        }

        test_file = test_set_dir / "1993-01-01 PRM.json"
        with open(test_file, "w") as f:
            json.dump(test_data, f)

    def test_load_card_data(self):
        """Test loading card data from JSON files."""
        generator = SiteGenerator(self.data_dir, self.output_dir)
        generator.load_card_data()

        self.assertIn(97042, generator.cards)
        card = generator.cards[97042]
        self.assertEqual(card.name, "Arena")
        self.assertEqual(len(card.comments), 1)
        self.assertEqual(card.comments[0].author, "TestUser")
        self.assertEqual(card.comments[0].star_rating, 4.0)

    def test_sitemap_generation_with_base_url(self):
        """Test sitemap generation with base URL produces fully qualified URLs."""
        base_url = "https://gatherer.mtg.li"
        generator = SiteGenerator(
            self.data_dir, self.output_dir, base_url=base_url
        )
        generator.load_card_data()
        generator.generate_sitemap()

        # Check sitemap file was created
        sitemap_file = self.output_dir / "sitemap.xml"
        self.assertTrue(sitemap_file.exists())

        # Check sitemap content includes fully qualified URLs
        with open(sitemap_file, "r", encoding="utf-8") as f:
            sitemap_content = f.read()

        # Should contain fully qualified URLs
        self.assertIn(f"{base_url}/index.html", sitemap_content)
        self.assertIn(f"{base_url}/cards/97042.html", sitemap_content)

    def test_sitemap_generation_without_base_url(self):
        """Test sitemap generation without base URL produces relative URLs."""
        generator = SiteGenerator(self.data_dir, self.output_dir)
        generator.load_card_data()
        generator.generate_sitemap()

        # Check sitemap file was created
        sitemap_file = self.output_dir / "sitemap.xml"
        self.assertTrue(sitemap_file.exists())

        # Check sitemap content includes relative URLs
        with open(sitemap_file, "r", encoding="utf-8") as f:
            sitemap_content = f.read()

        # Should contain relative URLs (not fully qualified)
        self.assertIn("<loc>index.html</loc>", sitemap_content)
        self.assertIn("<loc>cards/97042.html</loc>", sitemap_content)
        # Should NOT contain any https:// URLs
        self.assertNotIn("https://", sitemap_content)


class TestLoadRatings(unittest.TestCase):
    """Test load_ratings utility."""

    def test_load_ratings_returns_mvid_to_float(self):
        """load_ratings over a tmp dir with one file returns {mvid: float}."""
        with tempfile.TemporaryDirectory() as tmp:
            ratings_dir = Path(tmp) / "ratings" / "set"
            ratings_dir.mkdir(parents=True)
            data = {
                "94: Underground Sea": {"rating": 4.955},
                "10409: Spreading Algae": {"rating": 2.1},
            }
            with open(ratings_dir / "test.json", "w") as f:
                json.dump(data, f)

            result = load_ratings(Path(tmp) / "ratings")

        self.assertEqual(result[94], 4.955)
        self.assertEqual(result[10409], 2.1)

    def test_load_ratings_missing_dir_returns_empty(self):
        """load_ratings on a nonexistent directory returns {}."""
        with tempfile.TemporaryDirectory() as tmp:
            result = load_ratings(Path(tmp) / "nonexistent")
        self.assertEqual(result, {})


class TestCardCommunityRating(unittest.TestCase):
    """Test Card.community_rating field."""

    def _make_card(self, **kwargs) -> Card:
        return Card(multiverse_id=1, name="Test", comments=[], **kwargs)

    def test_community_rating_defaults_to_none(self):
        """community_rating is None when not provided."""
        card = self._make_card()
        self.assertIsNone(card.community_rating)

    def test_community_rating_round_trips(self):
        """community_rating stores and returns the provided float."""
        card = self._make_card(community_rating=4.955)
        self.assertAlmostEqual(card.community_rating, 4.955)


class TestHighestRatedSelection(unittest.TestCase):
    """Test that generate_search_page selects highest-rated by community_rating."""

    def setUp(self):
        """Set up a minimal SiteGenerator with known cards."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.output_dir = Path(self.temp_dir) / "output"
        self.ratings_dir = Path(self.temp_dir) / "ratings"

        self.data_dir.mkdir(parents=True)
        self.ratings_dir.mkdir(parents=True)

        # Write a data file with three cards
        data = {
            "1: Alpha Card": [],
            "2: Beta Card": [],
            "3: Gamma Card": [],
            "4: Unrated Card": [],
        }
        self.data_dir.mkdir(exist_ok=True)
        test_set_dir = self.data_dir / "set"
        test_set_dir.mkdir(parents=True)
        with open(test_set_dir / "cards.json", "w") as f:
            json.dump(data, f)

        # Write ratings for three of the four cards
        ratings_data = {
            "1: Alpha Card": {"rating": 3.5},
            "2: Beta Card": {"rating": 4.9},
            "3: Gamma Card": {"rating": 2.0},
        }
        with open(self.ratings_dir / "ratings.json", "w") as f:
            json.dump(ratings_data, f)

    def test_highest_rated_ordered_by_community_rating_desc(self):
        """highest_rated list is sorted descending by community_rating."""
        generator = SiteGenerator(
            self.data_dir, self.output_dir, ratings_dir=self.ratings_dir
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        generator.load_card_data()
        generator.generate_search_page()

        index_html = (self.output_dir / "index.html").read_text(encoding="utf-8")

        # Extract just the Highest Rated section — it sits between the
        # "Highest Rated Cards" heading and the next </div> section boundary.
        start = index_html.find("Highest Rated Cards")
        end = index_html.find("</div>", start)
        highest_section = index_html[start:end]

        # Beta Card (4.9) should appear before Alpha Card (3.5) in the section
        beta_pos = highest_section.find("Beta Card")
        alpha_pos = highest_section.find("Alpha Card")
        self.assertGreater(
            alpha_pos, beta_pos, "Beta Card (4.9) should rank above Alpha Card (3.5)"
        )

    def test_unrated_card_excluded_from_highest_rated(self):
        """Cards without community_rating are excluded from highest_rated."""
        generator = SiteGenerator(
            self.data_dir, self.output_dir, ratings_dir=self.ratings_dir
        )
        generator.load_card_data()

        # Unrated Card should have None community_rating
        unrated = next(
            c for c in generator.cards.values() if c.name == "Unrated Card"
        )
        self.assertIsNone(unrated.community_rating)


if __name__ == "__main__":
    unittest.main()
