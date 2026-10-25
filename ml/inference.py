"""Inference entry point for drug-level FAERS risk summaries.

The notebook trains three report-level classifiers with a shared fitted
preprocessor. Those binary artifacts are loaded once at import time when they
exist under ``ml/model_artifacts``. The public ``predict`` function preserves
the notebook's final drug-lookup behavior: it fetches live FAERS reports,
computes the observed serious-report percentage, maps it to a Low/Medium/High
risk class, and returns the most common reported reactions. When a classifier
artifact is available, the selected model is also run across those reports and
returned as an aggregate report-level summary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import requests

from .preprocessing import (
    HIGH_RISK_CUTOFF_PCT,
    LOW_RISK_CUTOFF_PCT,
    clean_report_features,
    clean_serious_labels,
    classify_risk_level,
    fetch_reports_for_drug,
    reports_to_frame,
    summarize_side_effects,
)


ARTIFACT_DIR = Path(__file__).resolve().parent / "model_artifacts"
MODEL_PATH = ARTIFACT_DIR / "best_model.joblib"
PREPROCESSOR_PATH = ARTIFACT_DIR / "preprocessor.joblib"
DEFAULT_REPORT_LIMIT = 200
DEFAULT_MODEL_KEY = "random_forest"

MODEL_SPECS: dict[str, dict[str, str]] = {
    "logistic_regression": {
        "name": "Logistic Regression",
        "artifact": "logistic_regression.joblib",
        "alias": "model_1",
    },
    "random_forest": {
        "name": "Random Forest",
        "artifact": "random_forest.joblib",
        "alias": "model_2",
    },
    "gradient_boosting": {
        "name": "Gradient Boosting",
        "artifact": "gradient_boosting.joblib",
        "alias": "model_3",
    },
}


class UnknownModelError(ValueError):
    """Raised when a requested model name/key is not part of the notebook."""


class ModelUnavailableError(ValueError):
    """Raised when a requested notebook model has no serialized artifact."""


def _load_artifact(path: Path) -> Any | None:
    """Load a joblib artifact if it exists."""

    if not path.exists():
        return None
    return joblib.load(path)


PREPROCESSOR = _load_artifact(PREPROCESSOR_PATH)


def _model_artifact_path(key: str, artifact_dir: Path = ARTIFACT_DIR) -> Path:
    """Return the configured artifact path for a notebook model key."""

    return artifact_dir / MODEL_SPECS[key]["artifact"]


def _normalize_model_identifier(value: str) -> str:
    """Normalize user-facing model keys/names to a stable lookup token."""

    return "_".join(value.strip().lower().replace("-", " ").split())


def _model_aliases() -> dict[str, str]:
    """Return accepted request identifiers for the three notebook models."""

    aliases: dict[str, str] = {}
    for key, spec in MODEL_SPECS.items():
        aliases[key] = key
        aliases[_normalize_model_identifier(spec["name"])] = key
        aliases[_normalize_model_identifier(spec["alias"])] = key
    aliases["best_model"] = DEFAULT_MODEL_KEY
    return aliases


def resolve_model_key(model_name: str | None, *, require_available: bool = True) -> str | None:
    """Resolve a request model identifier to a configured model key.

    ``None`` means use the default loaded model if one is available; if no
    artifacts are present, the caller can still return the notebook's direct
    FAERS statistic without a classifier summary.
    """

    if model_name is None or not model_name.strip():
        if DEFAULT_MODEL_KEY in MODELS:
            return DEFAULT_MODEL_KEY
        return next(iter(MODELS), None)

    key = _model_aliases().get(_normalize_model_identifier(model_name))
    if key is None:
        expected = ", ".join(spec["name"] for spec in MODEL_SPECS.values())
        raise UnknownModelError(f"Unknown model '{model_name}'. Choose one of: {expected}.")

    if require_available and key not in MODELS:
        artifact = MODEL_SPECS[key]["artifact"]
        raise ModelUnavailableError(
            f"{MODEL_SPECS[key]['name']} is configured but its artifact is missing: "
            f"ml/model_artifacts/{artifact}."
        )

    return key


def _load_models(artifact_dir: Path) -> dict[str, tuple[str, Any]]:
    """Load configured notebook model artifacts from the artifacts directory."""

    models: dict[str, Any] = {}
    if not artifact_dir.exists():
        return models

    for key, spec in MODEL_SPECS.items():
        path = artifact_dir / spec["artifact"]
        fallback_path = artifact_dir / MODEL_PATH.name
        if key == DEFAULT_MODEL_KEY and not path.exists() and fallback_path.exists():
            path = fallback_path
        if not path.exists():
            continue
        try:
            obj = joblib.load(path)
        except Exception:
            continue
        models[key] = (spec["name"], obj)

    return models


MODELS = _load_models(ARTIFACT_DIR)


def list_model_options() -> list[dict[str, Any]]:
    """Return the three notebook models with artifact availability metadata."""

    options: list[dict[str, Any]] = []
    for key, spec in MODEL_SPECS.items():
        options.append(
            {
                "key": key,
                "name": spec["name"],
                "alias": spec["alias"],
                "artifact": spec["artifact"],
                "available": key in MODELS,
                "selected_by_default": key == DEFAULT_MODEL_KEY,
            }
        )
    return options


def _model_report_summary_for(model, frame) -> dict[str, Any] | None:
    if model is None or PREPROCESSOR is None or frame.empty:
        return None

    raw_features = clean_report_features(frame)
    transformed = PREPROCESSOR.transform(raw_features)
    if hasattr(PREPROCESSOR, "get_feature_names_out"):
        import pandas as pd

        transformed = pd.DataFrame(
            transformed,
            columns=PREPROCESSOR.get_feature_names_out(),
            index=raw_features.index,
        )
    probabilities = model.predict_proba(transformed)
    positive_index = list(model.classes_).index(1)
    serious_probabilities = probabilities[:, positive_index]
    predicted_labels = model.predict(transformed)

    return {
        "mean_probability_serious": round(float(np.mean(serious_probabilities)), 6),
        "predicted_serious_report_fraction": round(float(np.mean(predicted_labels == 1)), 6),
        "mean_prediction_confidence": round(float(np.mean(np.max(probabilities, axis=1))), 6),
    }


def _empty_response(drug_name: str, message: str) -> dict[str, Any]:
    """Build a consistent response for missing-report cases."""
    # Choose a default model name if available
    loaded = bool(MODELS) and PREPROCESSOR is not None
    default_name = None
    if MODELS:
        # pick first friendly name
        default_name = next(iter(MODELS.values()))[0]

    return {
        "drug_name": drug_name,
        "source": "openFDA FAERS",
        "report_count": 0,
        "risk_level": "Unknown",
        "confidence": 0.0,
        "serious_report_percentage": None,
        "side_effects": [],
        "model": {
            "loaded": loaded,
            "name": default_name,
            "report_level_summary": None,
        },
        "message": message,
    }


def predict(drug_name: str, model_name: str | None = None) -> dict[str, Any]:
    """Return a drug-level FAERS risk summary for a raw drug-name string.

    Args:
        drug_name: Raw medicinal product name, for example ``"aspirin"``.

    Returns:
        A dictionary containing the Low/Medium/High risk class, the observed
        serious-report percentage, top side effects with report-relative
        probabilities, a confidence/support score, and optional aggregate
        report-level classifier outputs if the notebook's ``joblib`` artifacts
        are available.

    Raises:
        ValueError: If ``drug_name`` is empty.
        requests.RequestException: If openFDA cannot be reached or returns an
            unsuccessful response other than no matching reports.
    """

    normalized_name = drug_name.strip()
    if not normalized_name:
        raise ValueError("drug_name must be a non-empty string")

    try:
        reports = fetch_reports_for_drug(normalized_name, limit=DEFAULT_REPORT_LIMIT)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return _empty_response(normalized_name, "No FAERS reports found for this drug name.")
        raise

    frame = reports_to_frame(reports)
    frame_with_labels = clean_serious_labels(frame)
    if frame_with_labels.empty:
        return _empty_response(normalized_name, "No FAERS reports with usable serious labels were found.")

    total_reports = len(frame_with_labels)
    percent_serious = float(frame_with_labels["serious"].mean() * 100.0)
    risk_level = classify_risk_level(percent_serious)

    # Confidence is support-based for the notebook's direct statistic. The API
    # request caps at 200 reports, so a full notebook-sized response maps to 1.
    confidence = round(min(total_reports / float(DEFAULT_REPORT_LIMIT), 1.0), 6)

    # Determine selected model summary if requested and available.
    selected_model_name: str | None = None
    selected_summary = None

    selected_key = resolve_model_key(model_name, require_available=bool(model_name))
    if selected_key is not None:
        selected_model_name, model_obj = MODELS[selected_key]
        selected_summary = _model_report_summary_for(model_obj, frame_with_labels)

    return {
        "drug_name": normalized_name,
        "source": "openFDA FAERS",
        "report_count": total_reports,
        "risk_level": risk_level,
        "confidence": confidence,
        "serious_report_percentage": round(percent_serious, 6),
        "risk_thresholds": {
            "low_below_percentage": LOW_RISK_CUTOFF_PCT,
            "medium_below_percentage": HIGH_RISK_CUTOFF_PCT,
        },
        "side_effects": summarize_side_effects(frame_with_labels, top_n=5),
        "model": {
            "loaded": bool(MODELS) and PREPROCESSOR is not None,
            "name": selected_model_name,
            "report_level_summary": selected_summary,
        },
        "message": (
            "Percentages reflect voluntary FAERS adverse-event reports, not confirmed "
            "causation or individual medical risk."
        ),
    }
