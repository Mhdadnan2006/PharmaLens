import json
import io

from fastapi.testclient import TestClient
import joblib
import numpy as np
import pytest

import ml.inference as inference
from backend import main as backend_main


client = TestClient(backend_main.app)


def _make_mock_reports():
    return [
        {
            "safetyreportid": "1",
            "patient": {
                "patientonsetage": "30",
                "patientonsetageunit": "801",
                "patientsex": "1",
                "patientweight": "70",
                "reaction": [{"reactionmeddrapt": "Nausea"}, {"reactionmeddrapt": "Headache"}],
                "drug": [{"drugcharacterization": "1", "drugadministrationroute": "ORAL"}],
            },
            "primarysource": {"qualification": "Physician"},
            "occurcountry": "US",
            "serious": "1",
        },
        {
            "safetyreportid": "2",
            "patient": {
                "patientonsetage": "50",
                "patientonsetageunit": "801",
                "patientsex": "2",
                "patientweight": "80",
                "reaction": [{"reactionmeddrapt": "Dizziness"}],
                "drug": [{"drugcharacterization": "1", "drugadministrationroute": "ORAL"}],
            },
            "primarysource": {"qualification": "Consumer"},
            "occurcountry": "US",
            "serious": "2",
        },
    ]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "model_loaded" in data


def test_predict_and_report(monkeypatch):
    # Patch network fetch to return deterministic reports
    monkeypatch.setattr(inference, "fetch_reports_for_drug", lambda name, limit=200, timeout=30: _make_mock_reports())

    r = client.post("/predict", json={"drug_name": "TestDrug"})
    assert r.status_code == 200, r.text
    pred = r.json()
    assert pred["drug_name"].lower() == "testdrug"
    assert pred["report_count"] == 2
    assert isinstance(pred.get("side_effects"), list)

    # Generate PDF report from prediction
    r2 = client.post("/report", json=pred)
    assert r2.status_code == 200, r2.text
    ct = r2.headers.get("content-type", "")
    assert ct.startswith("application/pdf")
    content = r2.content
    assert len(content) > 100
    assert content[:4] == b"%PDF"


class _FakePreprocessor:
    def transform(self, frame):
        return np.zeros((len(frame), 2))


class _FakeClassifier:
    classes_ = np.array([0, 1])

    def __init__(self, serious_probability: float):
        self.serious_probability = serious_probability

    def predict_proba(self, transformed):
        rows = transformed.shape[0]
        return np.array([[1.0 - self.serious_probability, self.serious_probability]] * rows)

    def predict(self, transformed):
        value = 1 if self.serious_probability >= 0.5 else 0
        return np.array([value] * transformed.shape[0])


def test_predict_selects_each_configured_model(monkeypatch):
    monkeypatch.setattr(inference, "fetch_reports_for_drug", lambda name, limit=200, timeout=30: _make_mock_reports())
    monkeypatch.setattr(inference, "PREPROCESSOR", _FakePreprocessor())
    monkeypatch.setattr(backend_main, "PREPROCESSOR", inference.PREPROCESSOR)
    monkeypatch.setattr(
        inference,
        "MODELS",
        {
            "logistic_regression": ("Logistic Regression", _FakeClassifier(0.25)),
            "random_forest": ("Random Forest", _FakeClassifier(0.75)),
            "gradient_boosting": ("Gradient Boosting", _FakeClassifier(0.6)),
        },
    )
    monkeypatch.setattr(backend_main, "MODELS", inference.MODELS)

    cases = [
        ("model_1", "Logistic Regression", 0.25),
        ("random_forest", "Random Forest", 0.75),
        ("Gradient Boosting", "Gradient Boosting", 0.6),
    ]

    for requested, expected_name, expected_probability in cases:
        response = client.post("/predict", json={"drug_name": "TestDrug", "model_name": requested})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["model"]["name"] == expected_name
        assert payload["model"]["report_level_summary"]["mean_probability_serious"] == expected_probability


def test_predict_rejects_unknown_and_unavailable_models(monkeypatch):
    monkeypatch.setattr(inference, "MODELS", {})
    monkeypatch.setattr(backend_main, "MODELS", inference.MODELS)

    unknown = client.post("/predict", json={"drug_name": "TestDrug", "model_name": "svm"})
    assert unknown.status_code == 400
    assert "Unknown model" in unknown.json()["detail"]

    unavailable = client.post("/predict", json={"drug_name": "TestDrug", "model_name": "model_1"})
    assert unavailable.status_code == 503
    assert "artifact is missing" in unavailable.json()["detail"]


def test_load_models_uses_notebook_artifact_names(tmp_path):
    for key, (_, classifier) in {
        "logistic_regression": ("Logistic Regression", _FakeClassifier(0.25)),
        "random_forest": ("Random Forest", _FakeClassifier(0.75)),
        "gradient_boosting": ("Gradient Boosting", _FakeClassifier(0.6)),
    }.items():
        artifact = inference.MODEL_SPECS[key]["artifact"]
        joblib.dump(classifier, tmp_path / artifact)

    loaded = inference._load_models(tmp_path)

    assert set(loaded) == {"logistic_regression", "random_forest", "gradient_boosting"}
    assert loaded["logistic_regression"][0] == "Logistic Regression"
    assert loaded["random_forest"][0] == "Random Forest"
    assert loaded["gradient_boosting"][0] == "Gradient Boosting"


def test_best_model_artifact_is_random_forest_compatibility(tmp_path):
    joblib.dump(_FakeClassifier(0.75), tmp_path / "best_model.joblib")

    loaded = inference._load_models(tmp_path)

    assert set(loaded) == {"random_forest"}
    assert loaded["random_forest"][0] == "Random Forest"


def test_select_model_persistence():
    # Read metrics first
    r = client.get("/metrics")
    assert r.status_code == 200
    metrics = r.json()
    models = list(metrics.get("test_set", {}).keys())
    assert models, "No models found in metrics"

    # Pick a different model (if available) and set it
    current = metrics.get("selected_model")
    new = models[0] if models[0] != current else (models[1] if len(models) > 1 else models[0])

    r2 = client.post("/metrics/select", json={"selected_model": new})
    assert r2.status_code == 200
    assert r2.json().get("selected_model") == new

    # Ensure persisted
    r3 = client.get("/metrics")
    assert r3.status_code == 200
    assert r3.json().get("selected_model") == new

    # Restore the prior dashboard default so this test does not rewrite a tracked fixture.
    if current:
        restore = client.post("/metrics/select", json={"selected_model": current})
        assert restore.status_code == 200


def test_llm_summary_in_pdf(monkeypatch):
    # Ensure LLM text from Groq is embedded in generated PDF
    llm_text = "Groq professional summary: This medication shows elevated signal for serious events, exercise caution. Recommendations: review case narratives and consult safety team."  

    # Monkeypatch the backend LLM call to return our long professional summary
    import backend.main as backend_main
    monkeypatch.setattr(backend_main, "_call_groq", lambda prompt: llm_text)

    # Also patch the fetch to return deterministic reports
    monkeypatch.setattr(inference, "fetch_reports_for_drug", lambda name, limit=200, timeout=30: _make_mock_reports())

    r = client.post("/predict", json={"drug_name": "TestDrug"})
    assert r.status_code == 200
    pred = r.json()

    r2 = client.post("/report", json=pred)
    assert r2.status_code == 200
    content = r2.content
    # Use pypdf to extract text from the PDF and assert the LLM text is present
    try:
        from pypdf import PdfReader
    except Exception:
        raise RuntimeError("pypdf required for this test; install in test venv")

    reader = PdfReader(io.BytesIO(content))
    full_text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Groq professional summary" in full_text


class _FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_llm_provider_payloads_and_parsing(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if "groq" in url:
            return _FakeHTTPResponse({"choices": [{"message": {"content": "Groq summary"}}]})
        return _FakeHTTPResponse({"candidates": [{"content": {"parts": [{"text": "Gemini summary"}]}}]})

    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(backend_main._requests, "post", fake_post)

    assert backend_main._call_groq("prompt") == "Groq summary"
    assert backend_main._call_gemini("prompt") == "Gemini summary"
    assert calls[0][0] == "https://api.groq.com/openai/v1/chat/completions"
    assert calls[0][1]["json"]["messages"][0]["content"] == "prompt"
    assert calls[1][0].startswith("https://generativelanguage.googleapis.com/v1beta/models/")
    assert calls[1][1]["json"]["contents"][0]["parts"][0]["text"] == "prompt"
    assert "test-groq-key" not in calls[0][1]["json"]["messages"][0]["content"]
    assert "test-gemini-key" not in calls[1][1]["json"]["contents"][0]["parts"][0]["text"]


def test_empty_llm_response_is_rejected(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(backend_main._requests, "post", lambda *args, **kwargs: _FakeHTTPResponse({"choices": []}))

    with pytest.raises(RuntimeError, match="empty response"):
        backend_main._call_groq("prompt")


def test_report_escapes_content_and_exposes_summary(monkeypatch):
    monkeypatch.setattr(backend_main, "_call_groq", lambda prompt: "<b>unsafe & summary</b>")
    prediction = {
        "drug_name": "Aspirin/<script>",
        "risk_level": "Low & stable",
        "confidence": 0.5,
        "confidence_interval": {"confidence_level": 0.95, "lower": 1.0, "upper": 2.0, "method": "wilson_score", "unit": "percent"},
        "serious_report_percentage": 50.0,
        "report_count": 2,
        "side_effects": [{"name": "Nausea <x>", "count": 1, "probability": 0.5}],
        "model": {"loaded": True, "name": "Random Forest", "report_level_summary": None},
        "message": "message",
    }

    response = client.post("/report", json=prediction)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == "attachment; filename=pharmalens_report_Aspirin_script.pdf"
    assert response.headers.get("x-pharmalens-summary-base64")
    assert len(response.content) > 100


def test_latency_rejects_zero_bucket_count():
    response = client.get("/latency?n_points=0")
    assert response.status_code == 422
