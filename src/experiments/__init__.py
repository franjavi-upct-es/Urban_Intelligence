# src/experiments/__init__.py
# Urban Intelligence Framework - Experiments Module
# A/B testing and experimentation framework

"""
Experiments module for the Urban Intelligence Framework.

This module provides:
    - A/B testing for model comparison
    - Traffic splitting
    - Statistical significance testing
    - Experiment management
"""

from src.experiments.ab_testing import (
    ABTestingManager,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    Variant,
)

__all__ = [
    "ABTestingManager",
    "Experiment",
    "ExperimentResult",
    "ExperimentStatus",
    "Variant",
]
