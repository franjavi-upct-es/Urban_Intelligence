# Urban Intelligence Framework — Version History

# All notable changes to this project are documented here

# Changelog

All notable changes to the Urban Intelligence Framework are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-03

### Added

#### Flutter Mobile App (new)

- **UrbanIntelligenceApp**: Full Flutter 3.x companion app for iOS and Android
- Material 3 dark theme matching the web dashboard colour palette
- Bottom navigation shell with GoRouter declarative routing
- **DashboardScreen**: KPI overview, city status list, recent prediction feed
- **PredictScreen**: Full listing form with live prediction result card and confidence interval display
- **CitiesScreen**: City catalogue with per-city fetch controls and inline progress indicators
- **AnalyticsScreen**: fl_chart bar chart histogram, room-type breakdown with progress bars
- **MonitoringScreen**: Snapshot metrics, alert cards with severity colours, pull-to-refresh
- **SettingsScreen**: Default city selector, toggle preferences, API health check, reset dialog
- Riverpod 2.x state management with `FutureProvider`, `StateNotifierProvider`, and `StateProvider`
- `ApiService`: typed HTTP client wrapping all REST endpoints with `ApiException` error handling
- `City`, `PredictionRequest`, `PredictionResult`, `MonitoringSnapshot`, `Alert` data models with full `fromJson`/`toJson`
- `SharedPreferences`-backed city persistence across sessions
- `google_fonts: ^6.2.1` for Inter font — no local `.ttf` asset files required
- Flutter widget and model unit test suite (`test/widget_test.dart`)

#### Multi-city Transfer Learning

- **TransferLearningManager**: CORAL (Correlation Alignment) domain adaptation
- Up-sampling of minority source cities to median listing count before pooling
- Optimal base-vs-fine-tuned blend weight search (α grid over 21 steps)
- Transfer gain metric logged to MLflow (`transfer_rmse` vs `target_only_rmse`)
- `--transfer` flag on `run_training.py` and `scheduled_retrain.py`

#### GraphQL API

- **Strawberry GraphQL** schema alongside the existing REST API at `/graphql`
- GraphiQL interactive playground enabled in development
- `Query` type: `cities`, `city`, `listings`, `monitoringSnapshot`
- `Mutation` type: `triggerFetch`, `resolveAlert`
- Shares resolvers and data service with the REST layer — zero data duplication

#### Transformer NLP Features

- **TextFeatureEngineer**: DistilBERT CLS-token embeddings compressed to 32 dims via `TruncatedSVD`
- Batched inference (batch size 32) with `torch.no_grad()` for memory efficiency
- Keyword-group TF-IDF fallback (`luxury`, `location`, `amenities`, `quality`, `nature`) when PyTorch is unavailable
- `nlp_sentiment_score`, `nlp_description_length`, `nlp_has_description`, `nlp_name_length` structural features

#### Computer Vision Features

- **VisionFeatureEngineer**: EfficientNet-B0 photo quality scoring via torchvision
- Lazy model loading — CNN only initialised when `use_cnn=True`
- Pillow-based brightness fallback when torchvision is unavailable
- `vision_photo_count`, `vision_avg_brightness`, `vision_quality_score`, `vision_has_photos` columns

#### Ensemble Model Trainer

- Upgraded from single XGBoost to a three-model ensemble: **XGBoost + LightGBM + CatBoost**
- Integer-weight grid search over all model combinations to find the optimal ensemble blend
- Per-model Optuna Bayesian optimisation with independent hyperparameter spaces
- `TrainingResult` dataclass: models, weights, metrics, feature names, training time, MLflow run ID
- Graceful degradation: skips any model library that is not installed rather than crashing

#### Automated Data Quality Remediation

- `AirbnbCleaner` now drops columns exceeding a configurable `drop_null_threshold` (default 80 %)
- IQR outlier removal on price capped at P1–P99 to preserve extreme-but-valid listings
- Boolean string normalisation (`"t"` / `"f"` → `True` / `False`)
- Percentage column parsing (`"95%"` → `0.95`) for host response and acceptance rates
- Amenity count derived automatically when `amenity_count` column is absent

#### Feature Store

- **FeatureStore**: versioned Parquet artefacts under `data/processed/features/{city_id}/`
- JSON metadata sidecar per feature set (name, version, n_rows, stats, created_at)
- `save()`, `load()`, `load_meta()`, `list_feature_sets()`, `exists()` API
- Per-column statistics (mean, std, min, max, null_count) computed on save

#### Scheduled Retraining

- **scheduled_retrain.py**: drift-score and model-age based retraining trigger
- Retrains if drift score > 0.4 or model file is older than `MAX_MODEL_AGE_DAYS` (14 days)
- `--dry-run` flag logs what would be retrained without executing
- `--force` flag bypasses all threshold checks
- Designed for use as a daily cron job or Kubernetes CronJob

#### CI/CD Pipelines

- **ci.yml**: matrix build across Python 3.11 and 3.12; ruff lint + format check; pytest with coverage upload to Codecov; TypeScript type-check + ESLint + Vite build; Flutter `analyze` + `flutter test`; Docker image build for both backend and frontend
- **cd.yml**: GHCR image push on merge to `main`; semantic version tag triggers GitHub Release with auto-generated release notes

#### Docker & Infrastructure

- Multi-stage `backend/Dockerfile`: UV builder stage → slim runtime with `libgomp1` for XGBoost/LightGBM
- Multi-stage `frontend/Dockerfile`: Node 20 build stage → nginx 1.27 runtime with SPA routing and immutable asset caching headers
- `docker-compose.yml`: Redis 7, MLflow, backend, frontend with health checks, named volumes, and internal bridge network
- `postcss.config.js` added to frontend — required for Tailwind CSS to process styles

#### Project Fixes

- Added `backend/src/__init__.py` — Python package resolution was broken without it
- Added `backend/tests/__init__.py` — pytest import resolution was broken without it
- Fixed invalid `import numpy as np as _np` syntax in `run_training.py`

### Changed

- **README.md**: full rewrite following Keep a Changelog + badge conventions; ASCII architecture diagram replaced with a Mermaid `flowchart TD` rendered natively by GitHub; added phase-by-phase pipeline tables, benchmark targets, services table, full technology stack table
- **pyproject.toml**: upgraded to v2.0.0, added LightGBM, CatBoost, Strawberry, transformers, torch, torchvision, Pillow, Redis, structlog, prometheus-client
- `DataService` expanded from 5 cities to 10 cities in `INSIDE_AIRBNB_CATALOGUE` (added Amsterdam, Lisbon, Madrid, Berlin, Rome, Tokyo)
- `FeatureTransformer` now computes `dist_to_centre` using the Haversine formula for all 10 registered city centres
- `MonitoringRouter` and `ExperimentsRouter` extracted into dedicated `api/routers/` modules
- `Settings` extended with `redis_url`, `transfer_learning_enabled`, `source_cities`, `nlp_model`, `nlp_max_length`, `cv_model`, `cv_batch_size`, `api_rate_limit`, `cors_origins`
- WebSocket handler refactored into a `ConnectionManager` class supporting multi-channel broadcasts
- Frontend `hooks/index.ts` merged all React Query hooks, Zustand settings store, and WebSocket hook into a single import surface
- Mobile font strategy changed from local `.ttf` asset files to `google_fonts` package (Inter loaded at runtime, cached automatically)

### Removed

- Streamlit dashboard (replaced by React + TypeScript frontend in v1.2.0 — fully removed in v2.0.0)
- DVC pipeline (`dvc.yaml`, `params.yaml`) — replaced by FeatureStore versioning and MLflow artefact tracking
- Pre-commit hooks configuration — replaced by ruff in CI and a `make lint` / `make format` workflow

---

## [1.2.0] - 2026-02

### Added

#### A/B Testing Framework

- **ABTestingManager**: complete A/B testing infrastructure
- Traffic splitting with consistent hashing
- Statistical significance testing (t-test, ANOVA)
- Experiment lifecycle management (draft, running, paused, completed)
- Real-time metrics per variant

#### Multi-Model Ensemble

- **EnsembleModel**: combine multiple models for improved predictions
- Support for averaging, weighted averaging, and stacking strategies
- Automatic weight optimisation based on validation performance
- Uncertainty estimation from model disagreement

#### Time Series Forecasting

- **PriceForecaster**: seasonal price forecasting
- Holt-Winters triple exponential smoothing
- Trend and seasonality decomposition
- Confidence interval estimation
- Anomaly detection

#### Feature Store

- **FeatureStore**: centralised feature management
- Feature versioning and lineage tracking
- Built-in feature computations and statistics

#### React + TypeScript Frontend

- Modern responsive dashboard
- Real-time data visualisation with Recharts
- Dark/light theme support
- Mobile-friendly design
- Pages: Dashboard, Predict, Cities, Analytics, Experiments, Monitoring, Settings

#### New API Endpoints

- `/experiments/*` — A/B testing management
- `/monitoring/*` — performance monitoring
- `/monitoring/drift` — drift detection reports
- `/monitoring/alerts` — alert management

### Changed

- Replaced Streamlit with React + TypeScript frontend
- Enhanced API with modular routers
- Improved monitoring with real-time metrics

---

## [1.1.0] - 2026-02

### Added

#### Real-time Updates

- WebSocket support for live metrics
- Real-time prediction streaming
- Live alert notifications

#### Mobile-Responsive Dashboard

- Responsive layout for all screen sizes
- Touch-friendly controls
- Collapsible sidebar navigation

### Changed

- Improved chart performance
- Better error handling in API

---

## [1.0.0] - 2026-01

### Added

#### Core Architecture

- **DataService**: unified API implementing "fetch once, query fast" pattern
- **CityRegistry**: city metadata management with automatic discovery
- **CacheManager**: DuckDB-based intelligent caching layer
- **InsideAirbnbScraper**: automated web scraper for data discovery

#### Data Acquisition

- Automated scraping from Inside Airbnb with rate limiting
- Open-Meteo weather API integration (2+ years historical data)
- OpenStreetMap POI fetching via Overpass API
- Progress callbacks for real-time UI updates

#### ETL Pipeline

- **AirbnbCleaner**: Polars-based data cleaning with price parsing
- **FeatureTransformer**: feature engineering and encoding
- **SpatialEnricher**: geospatial feature extraction

#### Feature Engineering

- **CalendarFeatureEngineer**: seasonal and temporal features
- **SeasonalPriceAdjuster**: dynamic pricing based on patterns
- **TextFeatureEngineer**: review sentiment analysis
- **ReviewAggregator**: listing-level review statistics

#### Machine Learning

- **ModelTrainer**: XGBoost training with MLflow tracking
- **HyperparameterOptimizer**: Optuna Bayesian optimisation
- Cross-validation and comprehensive metrics

#### Model Monitoring

- **DriftDetector**: statistical drift detection (KS, Chi-squared, PSI)
- **PerformanceMonitor**: real-time performance tracking
- Automated alerting and retraining triggers

#### Data Validation

- **DataValidator**: Great Expectations pattern validation
- Multi-stage validation (raw, cleaned, enriched, model input)
- Detailed validation reports

#### DevOps & MLOps

- GitHub Actions CI/CD pipelines
- Docker containerisation with multi-stage builds
- Docker Compose orchestration
- DVC data versioning
- Pre-commit hooks for code quality
- Makefile for common commands

---

## License

MIT License — see the LICENSE file for details.
