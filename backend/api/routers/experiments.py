# backend/api/routers/experiments.py
# Urban Intelligence Framework v2.0.0
# REST router for A/B testing experiment management

"""
Experiments router.

Endpoints:
- GET  /api/v1/experiments              — list all experiments
- POST /api/v1/experiments              — create a new experiment
- GET  /api/v1/experiments/{id}         — get experiment details
- POST /api/v1/experiments/{id}/start   — start experiment
- POST /api/v1/experiments/{id}/pause   — pause experiment
- POST /api/v1/experiments/{id}/complete — complete and analyse
- GET  /api/v1/experiments/{id}/results — statistical results
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.modeling.ab_testing import ABTestingManager, Variant

router = APIRouter()
_ab_manager = ABTestingManager()


# ── Request models ────────────────────────────────────────────────────────


class VariantConfig(BaseModel):
    name: str
    model_id: str
    traffic_split: float = Field(..., gt=0.0, le=1.0)


class CreateExperimentRequest(BaseModel):
    name: str
    description: str = ""
    variants: list[VariantConfig] = Field(..., min_length=2, max_length=5)


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/")
async def list_experiments() -> dict[str, Any]:
    """Return all registered A/B experiments."""
    return {"experiments": _ab_manager.list_experiments()}


@router.post("/")
async def create_experiment(body: CreateExperimentRequest) -> dict[str, Any]:
    """Create and register a new A/B experiment."""
    try:
        variants = [
            Variant(
                name=v.name,
                model_id=v.model_id,
                traffic_split=v.traffic_split,
            )
            for v in body.variants
        ]
        exp_id = _ab_manager.create_experiment(
            name=body.name,
            variants=variants,
            description=body.description,
        )
        return {"experiment_id": exp_id, "name": body.name, "status": "draft"}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str) -> dict[str, Any]:
    """Return details of a single experiment."""
    try:
        exp = _ab_manager._get_experiment(experiment_id)
        return {
            "id": exp["id"],
            "name": exp["name"],
            "status": exp["status"].value,
            "created_at": exp["created_at"].isoformat(),
            "started_at": exp["started_at"].isoformat()
            if exp["started_at"]
            else None,
            "ended_at": exp["ended_at"].isoformat()
            if exp["ended_at"]
            else None,
            "variants": [
                {
                    "name": v.name,
                    "model_id": v.model_id,
                    "traffic_split": v.traffic_split,
                    "n_samples": v.n_samples,
                    "rmse": v.rmse,
                    "mae": v.mae,
                }
                for v in exp["variants"].values()
            ],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{experiment_id}/start")
async def start_experiment(experiment_id: str) -> dict[str, str]:
    """Transition an experiment from DRAFT to RUNNING."""
    try:
        _ab_manager.start_experiment(experiment_id)
        return {"message": f"Experiment {experiment_id} is now RUNNING"}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{experiment_id}/pause")
async def pause_experiment(experiment_id: str) -> dict[str, str]:
    """Pause a running experiment."""
    try:
        _ab_manager.pause_experiment(experiment_id)
        return {"message": f"Experiment {experiment_id} paused"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{experiment_id}/complete")
async def complete_experiment(experiment_id: str) -> dict[str, Any]:
    """Complete an experiment and return statistical analysis."""
    try:
        result = _ab_manager.complete_experiment(experiment_id)
        return {
            "experiment_id": result.experiment_id,
            "winner": result.winner,
            "p_value": result.p_value,
            "is_significant": result.is_significant,
            "confidence_level": result.confidence_level,
            "test_method": result.test_method,
            "variant_metrics": result.variant_metrics,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{experiment_id}/results")
async def get_results(experiment_id: str) -> dict[str, Any]:
    """Analyse a running or completed experiment without completing it."""
    try:
        result = _ab_manager.analyse(experiment_id)
        return {
            "experiment_id": result.experiment_id,
            "winner": result.winner,
            "p_value": result.p_value,
            "is_significant": result.is_significant,
            "test_method": result.test_method,
            "variant_metrics": result.variant_metrics,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
