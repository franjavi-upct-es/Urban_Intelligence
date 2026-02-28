# api/routes/experiments.py
# Urban Intelligence Framework - Experiments API Router
# A/B Testing endpoints

"""
API router for A/B testing experiments.

Provides endpoints for:
    - Creating and managing experiments
    - Starting and stopping experiments
    - Getting experiment results
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

# Import experiment manager (will be initialized in main app)
from src.experiments import ABTestingManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experiments", tags=["experiments"])

# Global experiment manager (set from main app)
_manager: ABTestingManager | None = None
