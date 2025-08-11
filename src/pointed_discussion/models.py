"""Data models for MTG card comments and metadata."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Comment:
    """Represents a single comment on a card."""

    author: str
    author_id: int
    datetime: str
    id: int
    text_parsed: str
    text_posted: str
    timestamp: str
    vote_count: int
    vote_sum: int

    @property
    def star_rating(self) -> float:
        """Calculate star rating from votes (5-star scale)."""
        if self.vote_count == 0:
            return 0.0
        return self.vote_sum / (2 * self.vote_count)

    @property
    def star_display(self) -> str:
        """Display rating as Unicode stars."""
        rating = self.star_rating
        full_stars = int(rating)
        half_star = rating - full_stars >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)

        stars = "★" * full_stars
        if half_star:
            stars += "☆"  # Using ☆ as half-star substitute
        stars += "☆" * empty_stars

        return f"{stars} ({rating:.1f}/5.0)"


@dataclass
class Card:
    """Represents a Magic card with its comments and metadata."""

    multiverse_id: int
    name: str
    comments: List[Comment]
    image_url: Optional[str] = None
    set_name: Optional[str] = None
    set_code: Optional[str] = None
    artist: Optional[str] = None
    collector_number: Optional[str] = None
    released_at: Optional[str] = None

    def __post_init__(self):
        """Sort comments by date."""
        self.comments.sort(key=lambda c: c.datetime)

    @property
    def display_name(self) -> str:
        """Get a display name that helps distinguish card variants."""
        base_name = self.name

        # Add distinguishing information if available
        distinguishers = []

        if self.set_code:
            distinguishers.append(f"({self.set_code})")

        if self.collector_number:
            distinguishers.append(f"#{self.collector_number}")

        if distinguishers:
            return f"{base_name} — {' | '.join(distinguishers)}"
        else:
            # Fallback to multiverse ID if no other info
            return f"{base_name} (ID: {self.multiverse_id})"

    @property
    def average_rating(self) -> float:
        """Calculate average star rating across all rated comments."""
        rated_comments = [c for c in self.comments if c.vote_count > 0]
        if not rated_comments:
            return 0.0
        return sum(c.star_rating for c in rated_comments) / len(rated_comments)

    @property
    def total_comments(self) -> int:
        """Get total number of comments."""
        return len(self.comments)

    @property
    def total_ratings(self) -> int:
        """Get total number of rated comments."""
        return sum(1 for c in self.comments if c.vote_count > 0)
