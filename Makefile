# Makefile
# Urban Intelligence Framework - Development Commands
# Common tasks for development, testing, and deployment

.PHONY: help install dev-install test lint format typecheck clean \
        docker-build docker-run docker-stop \
        fetch train predict api dashboard frontend \
        docs quality retrain

# Default target
help:
	@echo "Urban Intelligence Framework - Available Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install        Install production dependencies"
	@echo "  make dev-install    Install development dependencies"
	@echo "  make setup          Complete project setup"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run linter (Ruff)"
	@echo "  make format         Format code (Ruff)"
	@echo "  make typecheck      Run type checker (MyPy)"
	@echo "  make test           Run all tests"
	@echo "  make test-cov       Run tests with coverage"
	@echo "  make quality        Run all quality checks"
	@echo ""
	@echo "Data & ML:"
	@echo "  make fetch CITY=x   Fetch data for city (default: madrid)"
	@echo "  make train CITY=x   Train model for city"
	@echo "  make retrain        Run scheduled retraining check"
	@echo "  make validate       Validate data quality"
	@echo ""
	@echo "Applications:"
	@echo "  make api            Start FastAPI server"
	@echo "  make frontend       Start React frontend (dev)"
	@echo "  make frontend-build Build frontend for production"
	@echo "  make mlflow         Start MLflow UI"
	@echo "  make dev            Start development environment"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo "  make docker-stop    Stop Docker container"
	@echo "  make docker-all     Build and run everything"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          Clean generated files"
	@echo "  make docs           Generate documentation"
	@echo "  make pre-commit     Run pre-commit hooks"

# =============================================================================
# Variables
# =============================================================================

CITY ?= madrid
PYTHON := uv run python
PYTEST := uv run pytest
STREAMLIT := uv run streamlit
UVICORN := uv run uvicorn

# =============================================================================
# Setup & Installation
# =============================================================================

install:
	@echo "Installing dependencies..."
	uv sync

dev-install:
	@echo "Installing development dependencies..."
	uv sync --all-extras
	uv run pre-commit install

setup: dev-install
	@echo "Setting up project..."
	mkdir -p data/raw data/processed data/cache models logs
	@echo "Setup complete!"

# =============================================================================
# Code Quality
# =============================================================================

lint:
	@echo "Running linter..."
	uv run ruff check src/ scripts/ tests/ api/

format:
	@echo "Formatting code..."
	uv run ruff format src/ scripts/ tests/ api/
	uv run ruff check --fix src/ scripts/ tests/ api/

typecheck:
	@echo "Running type checker..."
	uv run mypy src/ --ignore-missing-imports

test:
	@echo "Running tests..."
	$(PYTEST) tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	$(PYTEST) tests/ --cov=src --cov-report=html --cov-report=term-missing

test-integration:
	@echo "Running integration tests..."
	$(PYTEST) tests/integration/ -v --tb=short

quality: lint typecheck test
	@echo "All quality checks passed!"

pre-commit:
	@echo "Running pre-commit hooks..."
	uv run pre-commit run --all-files

# =============================================================================
# Data & ML Pipeline
# =============================================================================

fetch:
	@echo "Fetching data for $(CITY)..."
	$(PYTHON) scripts/data_cli.py fetch $(CITY)

list-cities:
	@echo "Listing available cities..."
	$(PYTHON) scripts/data_cli.py list

status:
	@echo "Checking data status..."
	$(PYTHON) scripts/data_cli.py status

train:
	@echo "Training model for $(CITY)..."
	$(PYTHON) scripts/run_training.py --city $(CITY)

train-optimize:
	@echo "Training model with optimization for $(CITY)..."
	$(PYTHON) scripts/run_training.py --city $(CITY) --optimize --trials 50

etl:
	@echo "Running ETL pipeline for $(CITY)..."
	$(PYTHON) scripts/run_etl.py --city $(CITY)

pipeline:
	@echo "Running complete pipeline for $(CITY)..."
	$(PYTHON) scripts/run_all.py --city $(CITY)

validate:
	@echo "Validating data..."
	$(PYTHON) scripts/verify_data.py

retrain:
	@echo "Checking retraining triggers..."
	$(PYTHON) scripts/scheduled_retrain.py --check

retrain-force:
	@echo "Forcing model retraining..."
	$(PYTHON) scripts/scheduled_retrain.py --force --city $(CITY)

# =============================================================================
# Applications
# =============================================================================

api:
	@echo "Starting FastAPI server..."
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000 --reload

dashboard:
	@echo "Starting Streamlit dashboard..."
	$(STREAMLIT) run app/streamlit_app.py --server.port 8501

frontend:
	@echo "Starting React frontend..."
	cd frontend && npm run dev

frontend-install:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

frontend-build:
	@echo "Building frontend for production..."
	cd frontend && npm run build

mlflow:
	@echo "Starting MLflow UI..."
	uv run mlflow ui --host 127.0.0.1 --port 5000

demo:
	@echo "Running quickstart demo..."
	$(PYTHON) examples/quickstart.py

cli:
	@echo "Starting interactive CLI..."
	$(PYTHON) scripts/data_cli.py interactive

# Start both API and frontend
dev:
	@echo "Starting development environment..."
	@echo "Run 'make api' in one terminal and 'make frontend' in another"

# =============================================================================
# Docker
# =============================================================================

docker-build:
	@echo "Building Docker image..."
	docker build -t urban-intelligence:latest .

docker-run:
	@echo "Running Docker container..."
	docker-compose up -d app mlflow

docker-stop:
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

docker-all: docker-build docker-run
	@echo "Docker environment ready!"

docker-etl:
	@echo "Running ETL in Docker..."
	docker-compose run --rm etl

docker-train:
	@echo "Running training in Docker..."
	docker-compose run --rm training

# =============================================================================
# DVC Pipeline
# =============================================================================

dvc-repro:
	@echo "Reproducing DVC pipeline..."
	dvc repro

dvc-status:
	@echo "Checking DVC status..."
	dvc status

dvc-push:
	@echo "Pushing DVC artifacts..."
	dvc push

dvc-pull:
	@echo "Pulling DVC artifacts..."
	dvc pull

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "Documentation available in docs/"
	@echo "  - ARCHITECTURE.md"
	@echo "  - DATA_ACQUISITION_GUIDE.md"
	@echo "  - MASTER_SETUP_GUIDE.md"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning generated files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Clean complete!"

clean-data:
	@echo "Cleaning data cache..."
	rm -rf data/cache/*
	@echo "Data cache cleared!"

clean-models:
	@echo "Cleaning trained models..."
	rm -rf models/*
	@echo "Models cleared!"

clean-all: clean clean-data clean-models
	@echo "Full cleanup complete!"

# =============================================================================
# Development Helpers
# =============================================================================

shell:
	@echo "Starting Python shell..."
	$(PYTHON)

notebook:
	@echo "Starting Jupyter notebook..."
	uv run jupyter notebook

watch-test:
	@echo "Watching tests..."
	uv run pytest-watch

# =============================================================================
# CI/CD Helpers
# =============================================================================

ci-test:
	@echo "Running CI test suite..."
	$(PYTEST) tests/ -v --tb=short --cov=src --cov-report=xml

ci-lint:
	@echo "Running CI lint checks..."
	uv run ruff check src/ scripts/ tests/ api/ --output-format=github

ci-build:
	@echo "Building for CI..."
	docker build -t urban-intelligence:ci .
