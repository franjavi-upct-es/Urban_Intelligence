# backend/Dockerfile
# Urban Intelligence Framework v2.0.0
# Multi-stage Docker build for the Python FastAPI backend

# ———————————————————————————————————————————————————————————————
# Stage 1: builder — install dependencies with UV
# ———————————————————————————————————————————————————————————————
FROM python:3.11-slim AS builder

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml .

# Install dependencies into a virtual env at /app/.venv
RUN uv venv .venv && \
  uv sync --no-dev

# ———————————————————————————————————————————————————————————————
# Stage 2: runtime — lean production image
# ———————————————————————————————————————————————————————————————
FROM python:3.11-slim AS runtime

# System dependencies for ML libraries (libgomp for XGBoost/LightGBM)
RUN apt-get update && apt-get install -y --no-install-recommends \
  libgomp1 \
  curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy source code
COPY src/ ./src/
COPY api/ ./api/
COPY scripts/ ./scripts/

# Create data directories
RUN mkdir -p data/raw data/processed mlruns

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser && \
  chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
