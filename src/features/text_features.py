# src/features/text_features.py
# Urban Intelligence Framework - Text Feature Engineering
# Extracts features from reviews and descriptions using NLP

"""
Text feature engineering for the Urban Intelligence Framework.

This module extracts features from:
    - Review text (sentiment, topics, keywords)
    - Listing descriptions (amenities, highlights)
    - Host descriptions
    - Neighborhood overviews

Features are extracted using rule-based methods and simple NLP
to avoid heavy dependencies while still capturing useful signals.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


# =============================================================================
# Sentiment Lexicons
# =============================================================================

# Positive sentiment words (weighted by intensity)
POSITIVE_WORDS = {
    # Strong positive
    "amazing": 3,
    "excellent": 3,
    "fantastic": 3,
    "outstanding": 3,
    "perfect": 3,
    "wonderful": 3,
    "exceptional": 3,
    "incredible": 3,
    "superb": 3,
    "brilliant": 3,
    # Medium positive
    "great": 2,
    "lovely": 2,
    "beautiful": 2,
    "comfortable": 2,
    "clean": 2,
    "spacious": 2,
    "helpful": 2,
    "friendly": 2,
    "convenient": 2,
    "delightful": 2,
    "charming": 2,
    "cozy": 2,
    # Mild positive
    "good": 1,
    "nice": 1,
    "pleasant": 1,
    "fine": 1,
    "okay": 1,
    "decent": 1,
    "adequate": 1,
    "satisfactory": 1,
    "enjoy": 1,
    "recommend": 2,
    "recommended": 2,
    "love": 2,
    "loved": 2,
}

# Negative sentiment words (weighted by intensity)
NEGATIVE_WORDS = {
    # Strong negative
    "terrible": -3,
    "horrible": -3,
    "awful": -3,
    "disgusting": -3,
    "worst": -3,
    "disaster": -3,
    "nightmare": -3,
    "unacceptable": -3,
    # Medium negative
    "bad": -2,
    "dirty": -2,
    "noisy": -2,
    "uncomfortable": -2,
    "disappointing": -2,
    "poor": -2,
    "broken": -2,
    "rude": -2,
    "cold": -1,
    "small": -1,
    "cramped": -1,
    "old": -1,
    # Mild negative
    "okay": 0,
    "average": 0,
    "mediocre": -1,
    "lacking": -1,
    "issue": -1,
    "problem": -1,
    "complaint": -1,
}

# Amenity keywords to detect
AMENITY_KEYWORDS = {
    "wifi": ["wifi", "wi-fi", "wireless", "internet"],
    "pool": ["pool", "swimming"],
    "parking": ["parking", "garage", "car park"],
    "kitchen": ["kitchen", "cooking", "stove", "oven", "fridge"],
    "ac": ["air conditioning", "ac", "a/c", "air-conditioning", "climate"],
    "heating": ["heating", "heater", "heated", "warm"],
    "washer": ["washer", "washing machine", "laundry"],
    "dryer": ["dryer", "tumble dry"],
    "tv": ["tv", "television", "netflix", "streaming"],
    "gym": ["gym", "fitness", "workout"],
    "balcony": ["balcony", "terrace", "patio"],
    "garden": ["garden", "yard", "outdoor space"],
    "view": ["view", "views", "sea view", "city view", "mountain view"],
    "elevator": ["elevator", "lift"],
    "doorman": ["doorman", "concierge", "24-hour"],
    "pet_friendly": ["pet", "pets", "dog", "cat", "animal"],
}

# Location quality indicators
LOCATION_KEYWORDS = {
    "central": ["central", "downtown", "city center", "centre"],
    "quiet": ["quiet", "peaceful", "tranquil"],
    "walkable": ["walkable", "walking distance", "steps from"],
    "transit": ["metro", "subway", "bus stop", "train station", "transport"],
    "tourist": ["tourist", "attractions", "sightseeing", "landmark"],
    "nightlife": ["nightlife", "bars", "clubs", "restaurants"],
    "safe": ["safe", "security", "secure"],
}


@dataclass
class SentimentScore:
    """Sentiment analysis result."""

    positive_score: float
    negative_score: float
    compound_score: float
    word_count: int
    positive_words: list[str]
    negative_words: list[str]

    @property
    def sentiment_label(self) -> str:
        """Get sentiment label based on compound score."""
        if self.compound_score >= 0.5:
            return "very_positive"
        elif self.compound_score >= 0.1:
            return "positive"
        elif self.compound_score <= -0.5:
            return "very_negative"
        elif self.compound_score <= -0.1:
            return "negative"
        else:
            return "neutral"


class TextFeatureEngineer:
    """
    Extracts features from text fields in Airbnb data.

    This class uses rule-based NLP methods to extract:
        - Sentiment scores from reviews
        - Amenity mentions from descriptions
        - Location quality indicators
        - Text statistics (length, word count)

    Example:
        >>> engineer = TextFeatureEngineer()
        >>> features_df = engineer.create_features(listings_df, reviews_df)
    """

    def __init__(
        self,
        include_sentiment: bool = True,
        include_amenities: bool = True,
        include_location: bool = True,
        include_stats: bool = True,
    ) -> None:
        """Initialize the text feature engineer.

        Args:
            include_sentiment: Whether to include sentiment features
            include_amenities: Whether to include amenity detection
            include_location: Whether to include location quality features
            include_stats: Whether to include text statistics
        """
        self.include_sentiment = include_sentiment
        self.include_amenities = include_amenities
        self.include_location = include_location
        self.include_stats = include_stats

    def create_features(
        self,
        listings_df: pl.DataFrame,
        reviews_df: pl.DataFrame | None = None,
    ) -> pl.DataFrame:
        """Create text features.

        Args:
            listings_df: Listings DataFrame
            reviews_df: Optional reviews DataFrame

        Returns:
            DataFrame with added text features
        """
        result_df = listings_df.clone()

        # Extract features from description
        if "description" in listings_df.columns:
            result_df = self._add_description_features(result_df)

        # Extract features from reviews
        if reviews_df is not None:
            result_df = self._add_review_features(result_df, reviews_df)

        # Extract features from name/title
        if "name" in listings_df.columns:
            result_df = self._add_name_features(result_df)

        logger.info(f"Created text features, new columns: {result_df.width - listings_df.width}")

        return result_df

    def _add_description_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add features extracted from listing descriptions.

        Args:
            df: DataFrame with description column

        Returns:
            DataFrame with description features
        """
        descriptions = df["description"].fill_null("").to_list()

        # Initialize feature lists
        amenity_features: dict[str, list[int]] = {k: [] for k in AMENITY_KEYWORDS}
        location_features: dict[str, list[int]] = {k: [] for k in LOCATION_KEYWORDS}
        char_lengths = []
        word_counts = []

        for desc in descriptions:
            desc_lower = desc.lower() if desc else ""

            # Text statistics
            char_lengths.append(len(desc))
            word_counts.append(len(desc.split()) if desc else 0)

            # Amenity detection
            for amenity, keywords in AMENITY_KEYWORDS.items():
                found = any(kw in desc_lower for kw in keywords)
                amenity_features[amenity].append(int(found))

            # Location quality detection
            for quality, keywords in LOCATION_KEYWORDS.items():
                found = any(kw in desc_lower for kw in keywords)
                location_features[quality].append(int(found))

        # Add features to DataFrame
        if self.include_stats:
            df = df.with_columns(
                [
                    pl.Series("description_length", char_lengths),
                    pl.Series("description_word_count", word_counts),
                ]
            )

        if self.include_amenities:
            for amenity, values in amenity_features.items():
                df = df.with_columns(pl.Series(f"has_{amenity}", values))

            # Total amenities mentioned
            amenity_sum = [
                sum(amenity_features[k][i] for k in amenity_features)
                for i in range(len(descriptions))
            ]
            df = df.with_columns(pl.Series("amenity_mentions", amenity_sum))

        if self.include_location:
            for quality, values in location_features.items():
                df = df.with_columns(pl.Series(f"location_{quality}", values))

        return df

    def _add_review_features(
        self,
        df: pl.DataFrame,
        reviews_df: pl.DataFrame,
    ) -> pl.DataFrame:
        """Add features extracted from reviews.

        Args:
            df: Listings DataFrame
            reviews_df: Reviews DataFrame

        Returns:
            DataFrame with review features
        """
        if "listing_id" not in reviews_df.columns or "comments" not in reviews_df.columns:
            logger.warning("Reviews DataFrame missing required columns")
            return df

        # Analyze sentiment for each review
        sentiment_results = []

        for listing_id in df["id"].to_list():
            listing_reviews = (
                reviews_df.filter(pl.col("listing_id") == listing_id)["comments"]
                .fill_null("")
                .to_list()
            )

            if listing_reviews:
                # Combine all reviews
                combined_text = " ".join(listing_reviews)
                sentiment = self._analyze_sentiment(combined_text)

                sentiment_results.append(
                    {
                        "id": listing_id,
                        "review_sentiment_positive": sentiment.positive_score,
                        "review_sentiment_negative": sentiment.negative_score,
                        "review_sentiment_compound": sentiment.compound_score,
                        "review_word_count": sentiment.word_count,
                        "review_count": len(listing_reviews),
                    }
                )
            else:
                sentiment_results.append(
                    {
                        "id": listing_id,
                        "review_sentiment_positive": 0.0,
                        "review_sentiment_negative": 0.0,
                        "review_sentiment_compound": 0.0,
                        "review_word_count": 0,
                        "review_count": 0,
                    }
                )

        # Create sentiment DataFrame and join
        sentiment_df = pl.DataFrame(sentiment_results)
        df = df.join(sentiment_df, on="id", how="left")

        return df

    def _add_name_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add features from listing name/title.

        Args:
            df: DataFrame with name column

        Returns:
            DataFrame with name features
        """
        names = df["name"].fill_null("").to_list()

        # Extract features
        name_lengths = [len(n) for n in names]
        has_emoji = [int(bool(re.search(r"[\U0001F300-\U0001F9FF]", n))) for n in names]
        has_star = [int("★" in n or "⭐" in n or "star" in n.lower()) for n in names]
        has_luxury = [
            int(any(w in n.lower() for w in ["luxury", "luxurious", "premium", "exclusive"]))
            for n in names
        ]
        has_cozy = [
            int(any(w in n.lower() for w in ["cozy", "cosy", "charming", "cute"])) for n in names
        ]

        df = df.with_columns(
            [
                pl.Series("name_length", name_lengths),
                pl.Series("name_has_emoji", has_emoji),
                pl.Series("name_has_star", has_star),
                pl.Series("name_is_luxury", has_luxury),
                pl.Series("name_is_cozy", has_cozy),
            ]
        )

        return df

    def _analyze_sentiment(self, text: str) -> SentimentScore:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            SentimentScore with analysis results
        """
        if not text:
            return SentimentScore(
                positive_score=0.0,
                negative_score=0.0,
                compound_score=0.0,
                word_count=0,
                positive_words=[],
                negative_words=[],
            )

        # Tokenize and lowercase
        words = re.findall(r"\b\w+\b", text.lower())
        word_count = len(words)

        # Count sentiment words
        positive_found = []
        negative_found = []
        positive_score = 0
        negative_score = 0

        for word in words:
            if word in POSITIVE_WORDS:
                positive_score += POSITIVE_WORDS[word]
                positive_found.append(word)
            elif word in NEGATIVE_WORDS:
                negative_score += abs(NEGATIVE_WORDS[word])
                negative_found.append(word)

        # Normalize scores
        max_possible = word_count * 3 if word_count > 0 else 1
        norm_positive = positive_score / max_possible
        norm_negative = negative_score / max_possible

        # Compound score (-1 to 1)
        total = positive_score + negative_score
        compound = (positive_score - negative_score) / total if total > 0 else 0.0

        return SentimentScore(
            positive_score=norm_positive,
            negative_score=norm_negative,
            compound_score=compound,
            word_count=word_count,
            positive_words=list(set(positive_found)),
            negative_words=list(set(negative_found)),
        )

    def extract_review_statistics(
        self,
        reviews_df: pl.DataFrame,
    ) -> dict[str, Any]:
        """Extract summary statistics from reviews.

        Args:
            reviews_df: Reviews DataFrame

        Returns:
            Dictionary of review statistics
        """
        stats: dict[str, Any] = {}

        stats["total_reviews"] = reviews_df.height

        if "listing_id" in reviews_df.columns:
            stats["unique_listings"] = reviews_df["listing_id"].n_unique()

        if "comments" in reviews_df.columns:
            comments = reviews_df["comments"].fill_null("")
            word_counts = [len(c.split()) for c in comments.to_list()]
            stats["avg_review_length"] = sum(word_counts) / len(word_counts) if word_counts else 0
            stats["total_words"] = sum(word_counts)

        if "date" in reviews_df.columns:
            stats["date_range"] = {
                "min": str(reviews_df["date"].min()),
                "max": str(reviews_df["date"].max()),
            }

        return stats


class ReviewAggregator:
    """
    Aggregates review features at the listing level.

    This class provides methods to summarize reviews into
    listing-level features for model training.
    """

    def __init__(self) -> None:
        """Initialize the review aggregator."""
        self.text_engineer = TextFeatureEngineer()

    def aggregate_reviews(
        self,
        reviews_df: pl.DataFrame,
        listing_ids: list[int] | None = None,
    ) -> pl.DataFrame:
        """Aggregate reviews by listing.

        Args:
            reviews_df: Reviews DataFrame
            listing_ids: Optional list of listing IDs to process

        Returns:
            DataFrame with one row per listing
        """
        if listing_ids is not None:
            reviews_df = reviews_df.filter(pl.col("listing_id").is_in(listing_ids))

        # Group by listing
        aggregated = reviews_df.group_by("listing_id").agg(
            [
                pl.count().alias("review_count"),
                pl.col("comments").fill_null("").str.len_chars().mean().alias("avg_review_length"),
            ]
        )

        # Add sentiment features
        sentiment_features = []

        for listing_id in aggregated["listing_id"].to_list():
            listing_reviews = (
                reviews_df.filter(pl.col("listing_id") == listing_id)["comments"]
                .fill_null("")
                .to_list()
            )

            combined = " ".join(listing_reviews)
            sentiment = self.text_engineer._analyze_sentiment(combined)

            sentiment_features.append(
                {
                    "listing_id": listing_id,
                    "sentiment_compound": sentiment.compound_score,
                    "sentiment_label": sentiment.sentiment_label,
                }
            )

        sentiment_df = pl.DataFrame(sentiment_features)
        aggregated = aggregated.join(sentiment_df, on="listing_id", how="left")

        return aggregated
