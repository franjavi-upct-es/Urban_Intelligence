# backend/src/data/data_service.py
# Urban Intelligence Framework v2.0.0
# Unified data acquisition service implementing "fetch once, query fast"

"""
DataService module.

Implements the core "fetch once, query fast" pattern:
- First request for a city discovers the latest dataset URL from Inside Airbnb,
  then downloads and caches it as Parquet.
- Subsequent requests are served instantly from the DuckDB / Parquet cache.
- If the download fails for any reason, the service transparently falls back
  to synthetic data so the rest of the pipeline is never blocked.
- Progress callbacks allow real-time UI updates via WebSocket.

URL discovery strategy
----------------------
Inside Airbnb rotates datasets and blocks plain HTTP clients.  We scrape
http://insideairbnb.com/get-the-data/ with full browser headers to find the
most recent listings.csv.gz URL for each city, falling back to a known-good
URL pattern if scraping fails.
"""

from __future__ import annotations

import gzip
import io
import re
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx
import polars as pl
import structlog

from src.config import settings
from src.database import db

logger = structlog.get_logger(__name__)

# ── Type aliases ──────────────────────────────────────────────────────────
ProgressCallback = Callable[["FetchProgress"], None]

# ── Browser-like headers that Inside Airbnb accepts ──────────────────────
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://insideairbnb.com/get-the-data/",
    "Connection": "keep-alive",
}

_SAFE_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# ── Data classes ──────────────────────────────────────────────────────────


@dataclass
class FetchProgress:
    """Progress report emitted during a multi-step data fetch."""

    city_id: str
    step: str
    current: int
    total: int
    message: str = ""
    error: str | None = None

    @property
    def percent(self) -> float:
        return round(100 * self.current / max(self.total, 1), 1)


@dataclass
class CityData:
    """Container for all data associated with a single city."""

    city_id: str
    name: str
    listings: pl.DataFrame = field(default_factory=pl.DataFrame)
    weather: pl.DataFrame = field(default_factory=pl.DataFrame)
    pois: pl.DataFrame = field(default_factory=pl.DataFrame)
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    is_synthetic: bool = False

    @property
    def listing_count(self) -> int:
        return len(self.listings)

    @property
    def is_fresh(self) -> bool:
        return (datetime.utcnow() - self.fetched_at) < timedelta(hours=24)


# ── City catalogue ────────────────────────────────────────────────────────
# Search keywords used to find each city's URL on insideairbnb.com/get-the-data/
# The dict also stores the last-known URL as a fallback and geographic metadata.

INSIDE_AIRBNB_CATALOGUE: dict[str, dict[str, Any]] = {
    "london": {
        "name": "London",
        "country": "United Kingdom",
        "search_path": "united-kingdom/england/london",
        "lat": 51.5074,
        "lon": -0.1278,
        "currency": "GBP",
    },
    "paris": {
        "name": "Paris",
        "country": "France",
        "search_path": "france/ile-de-france/paris",
        "lat": 48.8566,
        "lon": 2.3522,
        "currency": "EUR",
    },
    "barcelona": {
        "name": "Barcelona",
        "country": "Spain",
        "search_path": "spain/catalonia/barcelona",
        "lat": 41.3851,
        "lon": 2.1734,
        "currency": "EUR",
    },
    "new-york": {
        "name": "New York City",
        "country": "United States",
        "search_path": "united-states/ny/new-york-city",
        "lat": 40.7128,
        "lon": -74.0060,
        "currency": "USD",
    },
    "amsterdam": {
        "name": "Amsterdam",
        "country": "Netherlands",
        "search_path": "the-netherlands/north-holland/amsterdam",
        "lat": 52.3676,
        "lon": 4.9041,
        "currency": "EUR",
    },
    "lisbon": {
        "name": "Lisbon",
        "country": "Portugal",
        "search_path": "portugal/lisbon/lisbon",
        "lat": 38.7169,
        "lon": -9.1399,
        "currency": "EUR",
    },
    "madrid": {
        "name": "Madrid",
        "country": "Spain",
        "search_path": "spain/comunidad-de-madrid/madrid",
        "lat": 40.4168,
        "lon": -3.7038,
        "currency": "EUR",
    },
    "berlin": {
        "name": "Berlin",
        "country": "Germany",
        "search_path": "germany/be/berlin",
        "lat": 52.5200,
        "lon": 13.4050,
        "currency": "EUR",
    },
    "rome": {
        "name": "Rome",
        "country": "Italy",
        "search_path": "italy/lazio/rome",
        "lat": 41.9028,
        "lon": 12.4964,
        "currency": "EUR",
    },
    "tokyo": {
        "name": "Tokyo",
        "country": "Japan",
        "search_path": "japan/kanto/tokyo",
        "lat": 35.6762,
        "lon": 139.6503,
        "currency": "JPY",
    },
}

# Runtime URL cache so we only scrape the data page once per session
_discovered_urls: dict[str, str] = {}


# ── DataService ────────────────────────────────────────────────────────────


class DataService:
    """
    Unified data acquisition and caching service.

    Fetch order for each city:
    1. Return Parquet cache if fresh and force_refresh=False.
    2. Discover the latest URL from insideairbnb.com/get-the-data/.
    3. Download the .csv.gz with browser-like headers.
    4. On any download failure → generate synthetic data and log a warning.
    """

    _FETCH_STEPS = 6

    def __init__(self) -> None:
        self._raw_path = settings.raw_data_path
        self._processed_path = settings.processed_data_path
        self._raw_path.mkdir(parents=True, exist_ok=True)
        self._processed_path.mkdir(parents=True, exist_ok=True)
        db.connect()

    # ── Public API ────────────────────────────────────────────────────────

    def get_available_cities(self) -> list[dict[str, Any]]:
        """Return all cities with their cache status."""
        return [
            {
                "city_id": city_id,
                "name": meta["name"],
                "country": meta["country"],
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "currency": meta["currency"],
                "is_cached": (
                    self._raw_path / f"{city_id}_listings.parquet"
                ).exists(),
            }
            for city_id, meta in INSIDE_AIRBNB_CATALOGUE.items()
        ]

    async def fetch_city(
        self,
        city_id: str,
        force_refresh: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> CityData:
        """
        Fetch all data for a city, falling back to synthetic data on failure.

        Steps:
            1. Check Parquet cache.
            2. Discover current download URL.
            3. Download with browser headers.
            4. Parse + save to Parquet.
            5. Fetch weather (best-effort).
            6. Register DuckDB view.
        """
        if city_id not in INSIDE_AIRBNB_CATALOGUE:
            raise ValueError(
                f"Unknown city '{city_id}'. "
                f"Available: {list(INSIDE_AIRBNB_CATALOGUE.keys())}"
            )

        meta = INSIDE_AIRBNB_CATALOGUE[city_id]
        parquet_path = self._raw_path / f"{city_id}_listings.parquet"

        # ── Step 1: Cache hit ─────────────────────────────────────────────
        self._emit(
            on_progress, city_id, "Checking cache", 1, self._FETCH_STEPS
        )
        if parquet_path.exists() and not force_refresh:
            logger.info("Loading city from cache", city=city_id)
            listings = pl.read_parquet(parquet_path)
            return CityData(
                city_id=city_id,
                name=meta["name"],
                listings=listings,
                fetched_at=datetime.fromtimestamp(
                    parquet_path.stat().st_mtime
                ),
            )

        # ── Step 2: Discover URL ──────────────────────────────────────────
        self._emit(
            on_progress,
            city_id,
            "Discovering dataset URL",
            2,
            self._FETCH_STEPS,
        )
        url = await self._discover_url(city_id, meta["search_path"])

        # ── Step 3: Download ──────────────────────────────────────────────
        self._emit(
            on_progress, city_id, "Downloading listings", 3, self._FETCH_STEPS
        )
        raw_bytes: bytes | None = None
        is_synthetic = False

        if url:
            try:
                raw_bytes = await self._download(url)
            except Exception as exc:
                logger.warning(
                    "Download failed — falling back to synthetic data",
                    city=city_id,
                    url=url,
                    error=str(exc),
                )
        else:
            logger.warning(
                "No URL discovered — falling back to synthetic data",
                city=city_id,
            )

        # ── Step 4: Parse or synthesise ───────────────────────────────────
        self._emit(
            on_progress, city_id, "Processing data", 4, self._FETCH_STEPS
        )
        if raw_bytes:
            listings = self._parse_listings(raw_bytes)
        else:
            listings = self._generate_synthetic(city_id)
            is_synthetic = True
            logger.warning(
                "Using synthetic data for city",
                city=city_id,
                note="Run the ETL again once internet access to insideairbnb.com is available.",
            )

        # ── Step 5: Weather (best-effort) ─────────────────────────────────
        self._emit(
            on_progress, city_id, "Fetching weather", 5, self._FETCH_STEPS
        )
        weather = await self._fetch_weather(meta["lat"], meta["lon"])

        # ── Step 6: Save + register ───────────────────────────────────────
        self._emit(
            on_progress, city_id, "Saving to cache", 6, self._FETCH_STEPS
        )
        listings.write_parquet(parquet_path)
        db.register_parquet(
            f"listings_{city_id.replace('-', '_')}", parquet_path
        )
        self._upsert_city_registry(city_id, meta, len(listings))

        logger.info(
            "City data ready",
            city=city_id,
            listings=len(listings),
            synthetic=is_synthetic,
        )
        return CityData(
            city_id=city_id,
            name=meta["name"],
            listings=listings,
            weather=weather,
            is_synthetic=is_synthetic,
        )

    def query_listings(
        self,
        city_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> pl.DataFrame:
        """Query cached listings for a city with optional column filters."""
        view_name = f"listings_{city_id.replace('-', '_')}"
        if not db.table_exists(view_name):
            raise RuntimeError(
                f"No cached data for city '{city_id}'. Call fetch_city() first."
            )
        if not _SAFE_SQL_IDENTIFIER.fullmatch(view_name):
            raise ValueError(f"Unsafe city/view identifier: {city_id}")

        df = db.read_table(view_name)
        if filters:
            for col, val in filters.items():
                if not _SAFE_SQL_IDENTIFIER.fullmatch(col):
                    raise ValueError(f"Unsafe filter column: {col}")
                if col not in df.columns:
                    raise ValueError(f"Unknown filter column: {col}")
                df = df.filter(pl.col(col) == val)

        return df.head(int(limit))

    # ── URL discovery ─────────────────────────────────────────────────────

    async def _discover_url(
        self, city_id: str, search_path: str
    ) -> str | None:
        """
        Scrape insideairbnb.com/get-the-data/ to find the latest listings URL.

        Returns the most recent matching URL, or None if scraping fails.
        Results are cached in-process to avoid repeated scrapes.
        """
        if city_id in _discovered_urls:
            return _discovered_urls[city_id]

        try:
            async with httpx.AsyncClient(
                headers=_BROWSER_HEADERS,
                timeout=20.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    "https://insideairbnb.com/get-the-data/"
                )
                response.raise_for_status()
                html = response.text

            # Find all listings.csv.gz URLs that match this city's path segment
            pattern = (
                r"https://data\.insideairbnb\.com/"
                + re.escape(search_path)
                + r"/\d{4}-\d{2}-\d{2}/data/listings\.csv\.gz"
            )
            matches = re.findall(pattern, html)

            if matches:
                # Take the lexicographically last match = most recent date
                url = sorted(matches)[-1]
                _discovered_urls[city_id] = url
                logger.info("Discovered dataset URL", city=city_id, url=url)
                return url

            logger.warning(
                "No URL found on data page", city=city_id, path=search_path
            )

        except Exception as exc:
            logger.warning(
                "URL discovery failed", city=city_id, error=str(exc)
            )

        return None

    # ── Download ──────────────────────────────────────────────────────────

    async def _download(self, url: str) -> bytes:
        """Download a gzip-compressed CSV with browser-like headers."""
        async with httpx.AsyncClient(
            headers=_BROWSER_HEADERS,
            timeout=180.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    # ── Parsing ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_listings(raw_bytes: bytes) -> pl.DataFrame:
        """Parse gzip-compressed CSV bytes into a Polars DataFrame."""
        decompressed = gzip.decompress(raw_bytes)
        return pl.read_csv(
            io.BytesIO(decompressed),
            infer_schema_length=5000,
            ignore_errors=True,
        )

    # ── Synthetic fallback ────────────────────────────────────────────────

    @staticmethod
    def _generate_synthetic(city_id: str) -> pl.DataFrame:
        """Generate realistic synthetic listings when real data is unavailable."""
        from src.data.generator import SyntheticDataGenerator

        gen = SyntheticDataGenerator(seed=42)
        return gen.generate(
            city_id=city_id, n_samples=settings.n_synthetic_samples
        )

    # ── Weather ───────────────────────────────────────────────────────────

    async def _fetch_weather(self, lat: float, lon: float) -> pl.DataFrame:
        """Fetch 2-year historical daily weather from Open-Meteo (best-effort)."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=730)
        url = (
            "https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={end_date}"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
            "&timezone=auto"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
            daily = data.get("daily", {})
            return pl.DataFrame(
                {
                    "date": daily.get("time", []),
                    "temperature_max": daily.get("temperature_2m_max", []),
                    "temperature_min": daily.get("temperature_2m_min", []),
                    "precipitation": daily.get("precipitation_sum", []),
                    "windspeed": daily.get("windspeed_10m_max", []),
                }
            )
        except Exception as exc:
            logger.warning("Weather fetch failed", error=str(exc))
            return pl.DataFrame()

    # ── DB helpers ────────────────────────────────────────────────────────

    def _upsert_city_registry(
        self, city_id: str, meta: dict[str, Any], listing_count: int
    ) -> None:
        # Pass now() as a Python value — DuckDB does not accept `current_timestamp`
        # as a bare keyword inside a VALUES clause (only in DEFAULT definitions).
        now = datetime.utcnow().isoformat()
        db.execute(
            """
            INSERT INTO cities (city_id, name, country, latitude, longitude,
                                currency, last_fetched, listing_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (city_id) DO UPDATE SET
                last_fetched  = excluded.last_fetched,
                listing_count = excluded.listing_count
            """,
            [
                city_id,
                meta["name"],
                meta["country"],
                meta["lat"],
                meta["lon"],
                meta["currency"],
                now,
                listing_count,
            ],
        )

    @staticmethod
    def _emit(
        callback: ProgressCallback | None,
        city_id: str,
        step: str,
        current: int,
        total: int,
        message: str = "",
    ) -> None:
        if callback is not None:
            with suppress(Exception):
                callback(FetchProgress(city_id, step, current, total, message))
