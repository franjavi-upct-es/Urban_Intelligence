# src/modeling/__init__.py
# Urban Intelligence Framework - Modeling Module
# XGBoost training with MLflow tracking and Optuna optimization

"""
Modeling module for the Urban Intelligence Framework.

Classes:
    ModelTrainer: Main training class with MLflow integration
"""

from src.modeling.trainer import ModelTrainer

__all__ = [
    "ModelTrainer",
]
