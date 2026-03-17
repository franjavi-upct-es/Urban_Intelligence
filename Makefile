# Makefile
# Urban Intelligence Framework v2.0.0
# Convenience commands for development, testing, and deployment

.PHONY: help up down backend frontend mlflow test lint format clean \
        build logs shell-backend etl train retrain migrate

# Default target
.DEFAULT_GOAL := help

# ─────────────────────────────────────────────
# Colors for pretty output
# ─────────────────────────────────────────────
CYAN  := \033[36m
RESET := \033[0m
BOLD  := \033[1m

help: ## Show this help message
	@echo "$(BOLD)Urban Intelligence Framework v2.0.0$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'

# ─────────────────────────────────────────────
# Docker Compose
# ─────────────────────────────────────────────
up: ## Start all services (detached)
	docker compose up -d --build

down: ## Stop all services
	docker compose down

logs: ## Tail logs from all services
	docker compose logs -f

build: ## Build all Docker images without cache
	docker compose build --no-cache

# ─────────────────────────────────────────────
# Individual service shortcuts
# ─────────────────────────────────────────────
backend: ## Start backend only (dev mode with reload)
	cd backend && uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend dev server
	cd frontend && npm run dev

mlflow: ## Start MLflow tracking server
	cd backend && uv run mlflow ui --host 0.0.0.0 --port 5001

# ─────────────────────────────────────────────
# Backend pipeline commands
# ─────────────────────────────────────────────
etl: ## Run the full ETL pipeline
	cd backend && uv run python scripts/run_etl.py

train: ## Train models for all available cities
	cd backend && uv run python scripts/run_training.py

retrain: ## Trigger scheduled retraining check
	cd backend && uv run python scripts/scheduled_retrain.py

# ─────────────────────────────────────────────
# Code quality
# ─────────────────────────────────────────────
lint: ## Run ruff linter on backend
	cd backend && uv run ruff check src/ api/ scripts/

format: ## Auto-format backend code
	cd backend && uv run ruff format src/ api/ scripts/

lint-fix: ## Auto-fix lint issues
	cd backend && uv ruff check --fix src/ api/ scripts/

# ─────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────
test-backend: ## Run all backend tests
	cd backend && uv run pytest tests/ -v --cov=src --cov-report=term-missing

test-mobile: ## Run all mobile tests
	cd mobile && flutter test

test: test-backend test-mobile ## Run all tests

test-api: ## Run API tests only
	cd backend && uv run pytest tests/test_api.py -v

test-models: ## Run model tests only
	cd backend && uv run pytest tests/test_models.py -v

# ─────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────
shell-backend: ## Open a shell inside the backend container
	docker compose exec backend bash

clean: ## Remove Python cache files and build artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	cd frontend && rm -rf dist node_modules/.vite

install-backend: ## Install backend dependencies with UV
	cd backend && uv sync

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

install: install-backend install-frontend ## Install all dependencies

setup: install ## Alias for install
	@echo "$(BOLD)Setup complete!$(RESET) Run 'make up' to start all services."
