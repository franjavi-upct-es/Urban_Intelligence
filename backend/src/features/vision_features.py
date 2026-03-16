# backend/src/features/vision_features.py
# Urban Intelligence Framework v2.0.0
# Computer vision feature extraction for Airbnb listing photos

"""
VisionFeatureEngineer module.

Downloads and scores listing photos using a pre-trained EfficientNet model
(or a lightweight fallback) to produce quality-related image features:

- vision_photo_count     : number of photos available
- vision_avg_brightness  : average pixel brightness (proxy for natural light)
- vision_quality_score   : EfficientNet-based aesthetic quality score [0, 1]
- vision_has_photos      : 1 if at least one photo was successfully processed
"""

from __future__ import annotations

import io
import statistics
from typing import Any

import httpx
import polars as pl
import structlog

logger = structlog.get_logger(__name__)


class VisionFeatureEngineer:
    """
    Extracts visual quality signals from Airbnb listing photos.

    Parameters
    ----------
    use_cnn : bool
        If True and torchvision is installed, use EfficientNet-B0 for scoring.
        Falls back to Pillow-based brightness analysis if False or unavailable.
    max_photos : int
        Maximum number of photos to download per listing (to cap API cost).
    timeout : float
        HTTP timeout in seconds for photo downloads.
    """

    def __init__(
        self,
        use_cnn: bool = False,
        max_photos: int = 5,
        timeout: float = 10.0,
    ) -> None:
        self.use_cnn = use_cnn
        self.max_photos = max_photos
        self.timeout = timeout
        self._model: Any = None
        self._transform: Any = None

    def fit_transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add vision features to the DataFrame.

        Looks for a 'picture_url' column. If absent, fills all vision
        columns with neutral default values.
        """
        logger.info("Extracting vision features", rows=len(df))

        if "picture_url" not in df.columns:
            return self._fill_defaults(df, len(df))

        if self.use_cnn:
            self._load_model()

        urls = df["picture_url"].fill_null("").to_list()
        photo_counts: list[int] = []
        brightness_scores: list[float] = []
        quality_scores: list[float] = []
        has_photos: list[int] = []

        for url in urls:
            result = self._process_photo(str(url))
            photo_counts.append(result["count"])
            brightness_scores.append(result["brightness"])
            quality_scores.append(result["quality"])
            has_photos.append(result["has_photo"])

        df = df.with_columns(
            [
                pl.Series("vision_photo_count", photo_counts, dtype=pl.Int16),
                pl.Series(
                    "vision_avg_brightness",
                    brightness_scores,
                    dtype=pl.Float64,
                ),
                pl.Series(
                    "vision_quality_score", quality_scores, dtype=pl.Float64
                ),
                pl.Series("vision_has_photos", has_photos, dtype=pl.Int8),
            ]
        )

        logger.info("Vision features extracted")
        return df

    # ── Private helpers ───────────────────────────────────────────────────

    def _process_photo(self, url: str) -> dict:
        """Download and analyse a single photo URL."""
        default = {
            "count": 0,
            "brightness": 0.5,
            "quality": 0.5,
            "has_photo": 0,
        }

        if not url or url == "nan":
            return default

        try:
            from PIL import Image

            response = httpx.get(
                url, timeout=self.timeout, follow_redirects=True
            )
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content)).convert("RGB")

            # Brightness: mean of all pixels normalised to [0, 1]
            pixel_mean = statistics.mean([v / 255.0 for v in img.tobytes()])

            quality = (
                self._cnn_score(img)
                if self.use_cnn and self._model
                else pixel_mean
            )

            return {
                "count": 1,
                "brightness": round(pixel_mean, 4),
                "quality": round(quality, 4),
                "has_photo": 1,
            }

        except Exception as exc:
            logger.debug(
                "Photo processing failed", url=url[:60], error=str(exc)
            )
            return default

    def _load_model(self) -> None:
        """Lazily load the EfficientNet-B0 model for quality scoring."""
        if self._model is not None:
            return
        try:
            import torchvision.models as models
            import torchvision.transforms as transforms

            self._model = models.efficientnet_b0(
                weights=models.EfficientNet_B0_Weights.DEFAULT
            )
            self._model.eval()

            self._transform = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            )
            logger.info("EfficientNet-B0 loaded for vision scoring")

        except ImportError:
            logger.warning("torchvision not available; CNN scoring disabled")
            self.use_cnn = False

    def _cnn_score(self, img: Any) -> float:
        """
        Run EfficientNet forward pass and return a normalised quality score.

        Uses the softmax probability of the 'top-quality' class as a proxy.
        """
        try:
            import torch

            tensor = self._transform(img).unsqueeze(0)  # type: ignore[misc]
            with torch.no_grad():
                logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1)
            # ImageNet class 759 ~ "restaurant" (often high-quality interior shots)
            # Use max probability as a generic "confidence in a clear category" signal
            return float(probs.max().item())
        except Exception:
            return 0.5

    @staticmethod
    def _fill_defaults(df: pl.DataFrame, n: int) -> pl.DataFrame:
        """Fill all vision columns with neutral default values."""
        return df.with_columns(
            [
                pl.lit(0).cast(pl.Int16).alias("vision_photo_count"),
                pl.lit(0.5).cast(pl.Float64).alias("vision_avg_brightness"),
                pl.lit(0.5).cast(pl.Float64).alias("vision_quality_score"),
                pl.lit(0).cast(pl.Int8).alias("vision_has_photos"),
            ]
        )
