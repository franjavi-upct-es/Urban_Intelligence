# api/routers/__init__.py
# Urban Intelligence Framework - API Routers
# Modular API route definitions

"""
API Routers for the Urban Intelligence Framework.

Routers:
    - experiments: A/B testing endpoints
    - monitoring: Performance and drift monitoring
"""

from api.routers.experiments import router as experiments_router
from api.routers.monitoring import router as monitoring_router

__all__ = ["experiments_router", "monitoring_router"]
