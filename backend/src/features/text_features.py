# backend/src/features/text_features.py
# Urban Intelligence Framework v2.0.0
# Transformer-based NLP features for listing text analysis

"""
TextFeatureEngineer module.

Extracts semantic features from listing text fields (name, description,
neighborhood_overview) using DistilBERT embeddings and a sentiment
analyzer. Falls back to TF-IDF bag-of-words features if PyTorch is
not available (CPU-only environments without heavy dependencies).

Generated feature columns (prefixed 'nlp_'):
- nlp_sentiment_score     : compound sentiment score -1 to +1
- nlp_description_length  : character count of description
- nlp_has_description     : 1 if a non-empty description exists
- nlp_embedding_*         : 32 PCA-compressed BERT embedding dimensions
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import polars as pl
import structlog

logger = structlog.get_logger(__name__)


def _simple_sentiment(text: str) -> float:
    """
    Lightweight rule-based sentiment scorer (no external dependencies).

    Returns a score in [-1, +1] based on positive and negative keyword counts.
    Used when transformer models are not available.
    """
    positive = {
        "beautiful",
        "stunning",
        "cozy",
        "charming",
        "spacious",
        "clean",
        "modern",
        "comfortable",
        "lovely",
        "great",
        "excellent",
        "perfect",
        "amazing",
        "wonderful",
        "fantastic",
        "bright",
        "quiet",
        "nice",
        "convenient",
        "central",
        "views",
        "private",
    }
    negative = {
        "noisy",
        "small",
        "dirty",
        "dark",
        "old",
        "broken",
        "smell",
        "cold",
        "uncomfortable",
        "crowded",
        "difficult",
        "far",
    }
    text_lower = text.lower()
    words = set(re.findall(r"\b\w+\b", text_lower))
    pos = len(words & positive)
    neg = len(words & negative)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


class TextFeatureEngineer:
    """
    Extracts NLP features from Airbnb listing text fields.

    If use_transformers=True and the transformers + torch libraries are
    installed, uses DistilBERT to produce dense semantic embeddings,
    which are then compressed to 32 dimensions via TruncatedSVD (fast PCA).

    Otherwise, falls back to simple keyword-based sentiment and TF-IDF.
    """

    def __init__(
        self, use_transformers: bool = False, n_embedding_dims: int = 32
    ) -> None:
        self.use_transformers = use_transformers
        self.n_embedding_dims = n_embedding_dims
        self._tokenizer: Any = None
        self._model: Any = None
        self._svd: Any = None

    # ── Public API ────────────────────────────────────────────────────────

    def fit_transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add NLP features to the DataFrame in-place."""
        logger.info("Extracting text features", rows=len(df))

        # Combine text fields into a single corpus column
        df = self._build_combined_text(df)

        # Basic structural features
        df = self._add_structural_features(df)

        # Sentiment
        df = self._add_sentiment_features(df)

        # Embeddings (if transformer mode is active)
        if self.use_transformers:
            df = self._add_transformer_embeddings(df)
        else:
            df = self._add_tfidf_features(df)

        # Drop intermediate column
        if "_combined_text" in df.columns:
            df = df.drop("_combined_text")

        logger.info(
            "Text features extracted",
            nlp_cols=[c for c in df.columns if c.startswith("nlp_")],
        )
        return df

    # ── Private helpers ───────────────────────────────────────────────────

    def _build_combined_text(self, df: pl.DataFrame) -> pl.DataFrame:
        """Concatenate available text columns into a single field."""
        text_cols = [
            c
            for c in ("name", "description", "neighborhood_overview")
            if c in df.columns
        ]
        if not text_cols:
            return df.with_columns(pl.lit("").alias("_combined_text"))

        combined = pl.concat_str(
            [pl.col(c).fill_null("").cast(pl.Utf8) for c in text_cols],
            separator=" ",
        ).alias("_combined_text")
        return df.with_columns(combined)

    def _add_structural_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add character-count and existence flags."""
        if "description" in df.columns:
            df = df.with_columns(
                [
                    pl.col("description")
                    .fill_null("")
                    .str.len_chars()
                    .alias("nlp_description_length"),
                    (pl.col("description").fill_null("").str.len_chars() > 10)
                    .cast(pl.Int8)
                    .alias("nlp_has_description"),
                ]
            )
        else:
            df = df.with_columns(
                [
                    pl.lit(0).cast(pl.Int32).alias("nlp_description_length"),
                    pl.lit(0).cast(pl.Int8).alias("nlp_has_description"),
                ]
            )

        if "name" in df.columns:
            df = df.with_columns(
                pl.col("name")
                .fill_null("")
                .str.len_chars()
                .alias("nlp_name_length")
            )
        return df

    def _add_sentiment_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply sentiment scoring to the combined text field."""
        texts = df["_combined_text"].to_list()
        scores = [_simple_sentiment(str(t)) for t in texts]
        return df.with_columns(
            pl.Series("nlp_sentiment_score", scores, dtype=pl.Float64)
        )

    def _add_transformer_embeddings(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Generate DistilBERT embeddings compressed to n_embedding_dims via SVD.
        Requires: transformers, torch, scikit-learn.
        """
        try:
            import torch
            from sklearn.decomposition import TruncatedSVD
            from transformers import AutoModel, AutoTokenizer

            from src.config import settings

            if self._tokenizer is None:
                logger.info("Loading tokenizer", model=settings.nlp_model)
                self._tokenizer = AutoTokenizer.from_pretrained(
                    settings.nlp_model,
                    revision=settings.nlp_model_revision,
                )
                self._model = AutoModel.from_pretrained(
                    settings.nlp_model,
                    revision=settings.nlp_model_revision,
                )
                self._model.eval()

            texts = [str(t)[:512] for t in df["_combined_text"].to_list()]

            embeddings: list[np.ndarray] = []
            batch_size = 32
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                enc = self._tokenizer(
                    batch,
                    max_length=settings.nlp_max_length,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                )
                with torch.no_grad():
                    out = self._model(**enc)
                # CLS token embedding
                cls_emb = out.last_hidden_state[:, 0, :].numpy()
                embeddings.append(cls_emb)

            all_embeddings = np.vstack(embeddings)

            # Compress with TruncatedSVD
            if self._svd is None:
                self._svd = TruncatedSVD(
                    n_components=self.n_embedding_dims, random_state=42
                )
                compressed = self._svd.fit_transform(all_embeddings)
            else:
                compressed = self._svd.transform(all_embeddings)

            for dim_idx in range(self.n_embedding_dims):
                col_name = f"nlp_embedding_{dim_idx:02d}"
                df = df.with_columns(
                    pl.Series(
                        col_name,
                        compressed[:, dim_idx].tolist(),
                        dtype=pl.Float64,
                    )
                )

        except ImportError:
            logger.warning(
                "Transformer dependencies not available; skipping embeddings"
            )

        return df

    def _add_tfidf_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Lightweight keyword frequency features (no heavy dependencies).

        Counts occurrences of high-signal amenity / quality keywords.
        """
        keyword_groups: dict[str, list[str]] = {
            "luxury": [
                "luxury",
                "premium",
                "deluxe",
                "exclusive",
                "penthouse",
            ],
            "location": [
                "central",
                "centre",
                "downtown",
                "metro",
                "transport",
            ],
            "amenities": ["wifi", "pool", "parking", "kitchen", "gym"],
            "quality": ["clean", "modern", "renovated", "new", "updated"],
            "nature": ["garden", "terrace", "balcony", "view", "park"],
        }

        texts = [str(t).lower() for t in df["_combined_text"].to_list()]

        for group, keywords in keyword_groups.items():
            counts = [
                sum(1 for kw in keywords if kw in text) for text in texts
            ]
            df = df.with_columns(
                pl.Series(f"nlp_kw_{group}", counts, dtype=pl.Int16)
            )
        return df
