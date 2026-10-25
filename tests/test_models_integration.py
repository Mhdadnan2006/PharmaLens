import os
import pytest
import requests

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")


def _artifact_path(name: str) -> str:
    root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(root, "ml", "model_artifacts", name)


def _required_artifacts_present() -> bool:
    needed = [
        _artifact_path("preprocessor.joblib"),
        _artifact_path("logistic_regression.joblib"),
        _artifact_path("random_forest.joblib"),
        _artifact_path("gradient_boosting.joblib"),
    ]
    return all(os.path.exists(p) for p in needed)


@pytest.mark.integration
def test_models_and_predict_integration():
    if not _required_artifacts_present():
        pytest.skip("Model artifacts not present in ml/model_artifacts; skip integration test.")

    # Check /models endpoint
    r = requests.get(f"{BASE}/models", timeout=10)
    assert r.status_code == 200
    payload = r.json()
    assert payload.get("preprocessor_loaded") is True
    models = payload.get("models") or []
    names = [m.get("name") for m in models]
    for expected in ["Logistic Regression", "Random Forest", "Gradient Boosting"]:
        assert expected in names, f"Expected model {expected} to be available"

    # Try predict with each model
    for model in models:
        name = model.get("name")
        resp = requests.post(f"{BASE}/predict", json={"drug_name": "aspirin", "model_name": name}, timeout=30)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["drug_name"] == "aspirin"
        assert data["model"]["name"] == name
