# Urban Intelligence Framework - Version History

# All notable changes to this project are documented here

# Changelog

All notable changes to the Urban Intelligence Framework are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-02

### Added

#### A/B Testing Framework

- **ABTestingManager**: Complete A/B testing infrastructure
- Traffic splitting with consistent hashing
- Statistical significance testing (t-test, ANOVA)
- Experiment lifecycle management (draft, running, paused, completed)
- Real-time metrics per variant

#### Multi-Model Ensemble

- **EnsembleModel**: Combine multiple models for improved predictions
- Support for averaging, weighted averaging, and stacking strategies
- Automatic weight optimization based on validation performance
- Uncertainty estimation from model disagreement

#### Time Series Forecasting

- **PriceForecaster**: Seasonal price forecasting
- Holt-Winters triple exponential smoothing
- Trend and seasonality decomposition
- Confidence interval estimation
- Anomaly detection

#### Feature Store

- **FeatureStore**: Centralized feature management
- Feature versioning and lineage tracking
- Built-in feature computations
- Feature set management
- Statistics computation

#### React + TypeScript Frontend

- Modern responsive dashboard
- Real-time data visualization with Recharts
- Dark/light theme support
- Mobile-friendly design
- Pages: Dashboard, Predict, Cities, Analytics, Experiments, Monitoring, Settings

#### New API Endpoints

- `/experiments/*` - A/B testing management
- `/monitoring/*` - Performance monitoring
- `/monitoring/drift` - Drift detection reports
- `/monitoring/alerts` - Alert management

### Changed

- Replaced Streamlit with React + TypeScript frontend
- Enhanced API with modular routers
- Improved monitoring with real-time metrics

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

## [1.0.0] - 2026-01

### Added

#### Core Architecture

- **DataService**: Unified API implementing "fetch once, query fast" pattern
- **CityRegistry**: City metadata management with automatic discovery
- **CacheManager**: DuckDB-based intelligent caching layer
- **InsideAirbnbScraper**: Automated web scraper for data discovery

#### Data Acquisition

- Automated scraping from Inside Airbnb with rate limiting
- Open-Meteo weather API integration (2+ years historical data)
- OpenStreetMap POI fetching via Overpass API
- Progress callbacks for real-time UI updates

#### ETL Pipeline

- **AirbnbCleaner**: Polars-based data cleaning with price parsing
- **FeatureTransformer**: Feature engineering and encoding
- **SpatialEnricher**: Geospatial feature extraction

#### Feature Engineering

- **CalendarFeatureEngineer**: Seasonal and temporal features
- **SeasonalPriceAdjuster**: Dynamic pricing based on patterns
- **TextFeatureEngineer**: Review sentiment analysis
- **ReviewAggregator**: Listing-level review statistics

#### Machine Learning

- **ModelTrainer**: XGBoost training with MLflow tracking
- **HyperparameterOptimizer**: Optuna Bayesian optimization
- Cross-validation and comprehensive metrics

#### Model Monitoring

- **DriftDetector**: Statistical drift detection (KS, Chi-squared, PSI)
- **PerformanceMonitor**: Real-time performance tracking
- Automated alerting and retraining triggers

#### Data Validation

- **DataValidator**: Great Expectations pattern validation
- Multi-stage validation (raw, cleaned, enriched, model input)
- Detailed validation reports

#### DevOps & MLOps

- GitHub Actions CI/CD pipelines
- Docker containerization with multi-stage builds
- Docker Compose orchestration
- DVC data versioning
- Pre-commit hooks for code quality
- Makefile for common commands

---

## Roadmap

### Planned for v2.0.0

- [ ] Multi-city transfer learning
- [ ] GraphQL API
- [ ] Advanced NLP for reviews (transformers)
- [ ] Image feature extraction
- [ ] Automated data quality remediation

---

## License

MIT License - see LICENSE file for details.
