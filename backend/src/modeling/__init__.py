# backend/src/modeling/__init__.py
# Urban Intelligence Framework v2.0.0
# Modeling module exports

"""ML modeling: training, transfer learning, and A/B testing."""

from src.modeling.ab_testing import ABTestingManager, ExperimentResult, Variant
from src.modeling.trainer import ModelTrainer, TrainingResult
from src.modeling.transfer_learning import (
    TransferLearningManager,
    TransferResult,
)

__all__ = [
    "ModelTrainer",
    "TrainingResult",
    "TransferLearningManager",
    "TransferResult",
    "ABTestingManager",
    "ExperimentResult",
    "Variant",
]
