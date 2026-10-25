"""Pydantic request and response schemas for the PharmaLens API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health-check response including the currently loaded model version."""

    status: str
    model_version: str
    model_loaded: bool


class PredictRequest(BaseModel):
    """Request body for drug risk prediction."""
    drug_name: str = Field(..., min_length=1, description="Raw drug name, for example aspirin.")
    model_name: str | None = Field(
        default=None,
        description=(
            "Optional model key/name for report-level predictions. Accepted keys are "
            "'logistic_regression', 'random_forest', and 'gradient_boosting'; aliases "
            "'model_1', 'model_2', 'model_3' and the friendly notebook names are also accepted. "
            "If omitted, the API uses the notebook default model when its artifact is present."
        ),
    )


class SideEffect(BaseModel):
    """A reported side effect ranked by report-relative probability."""

    name: str
    count: int = Field(..., ge=0)
    probability: float = Field(..., ge=0.0)


class ConfidenceInterval(BaseModel):
    """Confidence interval for the observed serious-report percentage."""

    confidence_level: float = Field(default=0.95)
    lower: float | None
    upper: float | None
    method: str
    unit: str = "percent"


class PredictResponse(BaseModel):
    """Drug-level FAERS risk prediction response."""

    drug_name: str
    risk_level: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_interval: ConfidenceInterval
    serious_report_percentage: float | None
    report_count: int = Field(..., ge=0)
    side_effects: list[SideEffect]
    model: dict[str, Any]
    message: str


class LatencyPoint(BaseModel):
    """A latency series point for recent prediction calls."""

    label: str
    p50: float
    p95: float


class MetricsResponse(BaseModel):
    """Stored notebook evaluation metrics."""

    model_config = ConfigDict(extra="allow")
