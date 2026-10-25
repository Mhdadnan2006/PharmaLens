"""FastAPI application wrapping ``ml.inference.predict``."""

from __future__ import annotations

import json
import os
import re
import time
import base64
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from requests import RequestException

from ml.inference import (
    MODELS,
    PREPROCESSOR,
    ModelUnavailableError,
    UnknownModelError,
    list_model_options,
    predict,
    resolve_model_key,
)
import sqlite3
import numpy as np

from .logging_db import init_db, log_predict_call
from .schemas import (
    ConfidenceInterval,
    HealthResponse,
    MetricsResponse,
    PredictRequest,
    PredictResponse,
    LatencyPoint,
)

import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import requests as _requests


APP_DIR = Path(__file__).resolve().parent
METRICS_PATH = APP_DIR / "metrics.json"
MODEL_VERSION = os.getenv("MODEL_VERSION", "random-forest-faers-notebook-v1")
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
    "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
)


def _allowed_origins() -> list[str]:
    """Read allowed CORS origins from a comma-separated environment variable."""

    raw_value = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def _wilson_confidence_interval(
    percent: float | None,
    count: int,
    confidence_level: float = 0.95,
) -> ConfidenceInterval:
    """Compute a Wilson interval for the observed serious-report percentage."""

    if percent is None or count <= 0:
        return ConfidenceInterval(
            confidence_level=confidence_level,
            lower=None,
            upper=None,
            method="wilson_score",
        )

    z = 1.959963984540054
    proportion = percent / 100.0
    denominator = 1.0 + (z**2 / count)
    center = (proportion + (z**2 / (2.0 * count))) / denominator
    margin = (
        z
        * ((proportion * (1.0 - proportion) / count) + (z**2 / (4.0 * count**2))) ** 0.5
        / denominator
    )

    return ConfidenceInterval(
        confidence_level=confidence_level,
        lower=round(max(0.0, (center - margin) * 100.0), 6),
        upper=round(min(100.0, (center + margin) * 100.0), 6),
        method="wilson_score",
    )


def _load_metrics() -> dict[str, Any]:
    """Load stored notebook metrics from ``metrics.json``."""

    with METRICS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize local storage used by the backend."""

    init_db()
    yield


app = FastAPI(
    title="PharmaLens API",
    version="1.0.0",
    description="FastAPI backend for notebook-extracted FAERS drug risk summaries.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-PharmaLens-Summary-Base64"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health and loaded model status."""
    model_loaded = bool(MODELS) and PREPROCESSOR is not None
    model_version = MODEL_VERSION if model_loaded else f"{MODEL_VERSION}:artifacts-missing"
    return HealthResponse(status="ok", model_version=model_version, model_loaded=model_loaded)


@app.post("/predict", response_model=PredictResponse)
def predict_drug(request: PredictRequest) -> PredictResponse:
    """Run a drug-name prediction and record structured latency metadata."""

    drug_name = request.drug_name.strip()
    start_time = time.perf_counter()

    try:
        model_name = request.model_name
        if model_name:
            resolve_model_key(model_name)
        result = predict(drug_name, model_name)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        log_predict_call(drug_name=drug_name, latency_ms=latency_ms)

        side_effects = sorted(
            result["side_effects"],
            key=lambda item: item["probability"],
            reverse=True,
        )

        return PredictResponse(
            drug_name=result["drug_name"],
            risk_level=result["risk_level"],
            confidence=result["confidence"],
            confidence_interval=_wilson_confidence_interval(
                result["serious_report_percentage"],
                result["report_count"],
            ),
            serious_report_percentage=result["serious_report_percentage"],
            report_count=result["report_count"],
            side_effects=side_effects,
            model=result["model"],
            message=result["message"],
        )
    except UnknownModelError as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        log_predict_call(drug_name=drug_name or "<empty>", latency_ms=latency_ms)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ModelUnavailableError as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        log_predict_call(drug_name=drug_name or "<empty>", latency_ms=latency_ms)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        log_predict_call(drug_name=drug_name or "<empty>", latency_ms=latency_ms)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RequestException as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        log_predict_call(drug_name=drug_name, latency_ms=latency_ms)
        raise HTTPException(status_code=502, detail=f"openFDA request failed: {exc}") from exc
    except (KeyError, ValidationError) as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        log_predict_call(drug_name=drug_name, latency_ms=latency_ms)
        raise HTTPException(status_code=500, detail=f"Unexpected prediction response: {exc}") from exc


@app.get("/metrics", response_model=MetricsResponse)
def metrics() -> dict[str, Any]:
    """Return stored evaluation metrics extracted from the notebook."""

    return _load_metrics()


@app.post("/metrics/select")
def select_metrics_model(selected: dict[str, str]):
    """Set the selected model in `metrics.json` to persist frontend choice.

    Expects JSON body: {"selected_model": "Random Forest"}
    """
    sel = selected.get("selected_model")
    if not sel:
        raise HTTPException(status_code=400, detail="selected_model must be provided")

    metrics = _load_metrics()
    if "test_set" not in metrics or sel not in metrics.get("test_set", {}):
        raise HTTPException(status_code=400, detail="selected_model is not a known model")

    metrics["selected_model"] = sel
    try:
        with METRICS_PATH.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not write metrics: {exc}") from exc

    return {"selected_model": sel}


@app.get("/latency", response_model=list[LatencyPoint])
def latency_series(n_points: int = Query(default=6, ge=1, le=100)) -> list[LatencyPoint]:
    """Return recent prediction latency percentiles grouped into `n_points` buckets.

    The function reads the `predict_logs` SQLite table, orders by timestamp
    (most recent first), splits the rows into `n_points` consecutive buckets,
    and computes the 50th and 95th percentiles for each bucket. If there are
    fewer rows than buckets, empty buckets will be omitted.
    """

    # Use the same DB path as the logging module.
    from .logging_db import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT timestamp, latency_ms FROM predict_logs ORDER BY timestamp DESC").fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    # Convert to list of latencies (most recent first) and split into buckets
    latencies = [row[1] for row in rows]
    # Determine bucket size (at least 1)
    bucket_size = max(1, len(latencies) // n_points)

    points: list[LatencyPoint] = []
    for i in range(0, len(latencies), bucket_size):
        chunk = latencies[i : i + bucket_size]
        if not chunk:
            continue
        p50 = float(np.percentile(chunk, 50))
        p95 = float(np.percentile(chunk, 95))
        label = f"T-{len(points) + 1}"
        points.append(LatencyPoint(label=label, p50=round(p50, 3), p95=round(p95, 3)))

    # Return up to n_points most recent buckets
    return points[:n_points]


@app.get("/models")
def list_models():
    """Return notebook model choices and whether each artifact is loaded."""

    return {
        "models": list_model_options(),
        "preprocessor_loaded": PREPROCESSOR is not None,
    }



def _call_groq(prompt: str) -> str:
    """Call Groq API with the prompt. Raises RequestException on failure."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not configured")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    resp = _requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Groq returned an empty response")
    return content.strip()


def _call_gemini(prompt: str) -> str:
    """Fallback to Gemini (Google) API using API key in GEMINI_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
    resp = _requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates") or []
    content = (candidates[0].get("content", {}).get("parts", [{}])[0].get("text") if candidates else None)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Gemini returned an empty response")
    return content.strip()


def _report_prompt_payload(pred: dict[str, Any]) -> dict[str, Any]:
    """Keep report prompts limited to aggregate prediction data."""

    model = pred.get("model") or {}
    return {
        "drug_name": pred.get("drug_name"),
        "risk_level": pred.get("risk_level"),
        "confidence": pred.get("confidence"),
        "serious_report_percentage": pred.get("serious_report_percentage"),
        "report_count": pred.get("report_count"),
        "side_effects": pred.get("side_effects", []),
        "model": {"name": model.get("name"), "report_level_summary": model.get("report_level_summary")},
    }


def _synthesize_summary(pred: dict[str, Any]) -> str:
    """Produce a short 3-4 sentence humanized summary using LLMs.

    Tries Groq first, then Gemini as fallback.
    """
    prompt = (
        f"Summarize the following drug risk prediction in 3-4 concise, human-friendly sentences. "
        f"Include the drug name, risk level, key side effects, selected model, and a short interpretation. "
        f"Do not provide medical advice.\n\nPrediction:\n{json.dumps(_report_prompt_payload(pred), ensure_ascii=False)}"
    )

    try:
        return _call_groq(prompt)
    except Exception:
        try:
            return _call_gemini(prompt)
        except Exception as exc:
            # As a last resort, return a simple programmatic summary
            drug = pred.get("drug_name", "Unknown")
            risk = pred.get("risk_level", "Unknown")
            effects = ", ".join([e.get("name", "") for e in pred.get("side_effects", [])[:3]])
            return (
                f"{drug} is flagged as {risk} risk. Top reported side effects include {effects}. "
                "This summary is autogenerated and not medical advice."
            )


def _build_pdf_bytes(pred: dict[str, Any], summary: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    # Header
    title = "PharmaLens Prediction Report"
    story.append(Paragraph(title, styles["Title"]))
    subtitle = f"{pred.get('drug_name', 'Unknown')} - Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(_escape_report_text(subtitle), styles["Normal"]))
    story.append(Spacer(1, 12))

    # Summary and risk
    risk = pred.get("risk_level", "Unknown")
    story.append(Paragraph(f"<b>Risk level:</b> {_escape_report_text(risk)}", styles["Heading2"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Humanized summary</b>", styles["Heading3"]))
    story.append(Paragraph(_escape_report_text(summary).replace("\n", "<br/>"), styles["BodyText"]))
    story.append(Spacer(1, 12))

    # Key statistics
    story.append(Paragraph("<b>Prediction details</b>", styles["Heading3"]))
    stats = [
        ["Report count", str(pred.get("report_count", "N/A"))],
        ["Confidence", str(pred.get("confidence", "N/A"))],
        ["Serious report %", str(pred.get("serious_report_percentage", "N/A"))],
    ]
    t = Table(stats, colWidths=[2.5 * inch, 3.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 12))

    # Side effects table
    story.append(Paragraph("<b>Ranked side effects</b>", styles["Heading3"]))
    side_effects = pred.get("side_effects", []) or []
    if side_effects:
        rows = [["Rank", "Side effect", "Count", "Probability"]]
        for i, s in enumerate(side_effects, start=1):
            rows.append([str(i), _escape_report_text(s.get("name", "")), str(s.get("count", "")), f"{float(s.get('probability',0))*100:.1f}%"])
        tbl = Table(rows, colWidths=[0.6 * inch, 3.4 * inch, 1.0 * inch, 1.0 * inch])
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 1), (3, -1), "RIGHT"),
                ]
            )
        )
        story.append(tbl)
    else:
        story.append(Paragraph("No side effects reported.", styles["BodyText"]))
    story.append(Spacer(1, 12))

    # Model metrics (if available)
    try:
        metrics = _load_metrics()
        sel = (pred.get("model") or {}).get("name") or metrics.get("selected_model")
        model_metrics = metrics.get("test_set", {}).get(sel)
        if model_metrics:
            story.append(Paragraph(f"<b>Model: {_escape_report_text(sel)}</b>", styles["Heading3"]))
            mm_rows = [["Metric", "Value"], ["Accuracy", str(model_metrics.get("accuracy", "N/A"))], ["F1", str(model_metrics.get("f1", "N/A"))], ["ROC-AUC", str(model_metrics.get("roc_auc", "N/A"))]]
            mm_table = Table(mm_rows, colWidths=[3 * inch, 3 * inch])
            mm_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke)]))
            story.append(mm_table)
            story.append(Spacer(1, 12))
    except Exception:
        pass

    story.append(Paragraph("<b>Disclaimer</b>", styles["Heading3"]))
    story.append(
        Paragraph(
            "This report is an automated summary of adverse event reports and is not medical advice. Consult a qualified professional for medical decisions.",
            styles["BodyText"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def _escape_report_text(value: Any) -> str:
    """Escape user/provider text before inserting it into ReportLab markup."""

    from xml.sax.saxutils import escape

    return escape(str(value), {"'": "&apos;", '"': "&quot;"})


def _safe_report_filename(drug_name: Any) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(drug_name or "report")).strip("._")
    return name[:80] or "report"


@app.post("/report")
def generate_report(prediction: PredictResponse):
    """Synthesize a short human-readable summary from a prediction and return a PDF."""
    pred_dict = prediction.model_dump() if hasattr(prediction, "model_dump") else prediction.dict()
    try:
        summary = _synthesize_summary(pred_dict)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM synthesis failed: {exc}") from exc

    pdf_bytes = _build_pdf_bytes(pred_dict, summary)
    filename = _safe_report_filename(pred_dict.get("drug_name"))
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=pharmalens_report_{filename}.pdf",
        "X-PharmaLens-Summary-Base64": base64.b64encode(summary.encode("utf-8")).decode("ascii"),
    })


@app.post("/report/summary")
def report_summary(prediction: PredictResponse) -> dict[str, str]:
    """Return the generated human-readable summary for on-screen display."""

    pred_dict = prediction.model_dump() if hasattr(prediction, "model_dump") else prediction.dict()
    return {"summary": _synthesize_summary(pred_dict)}
