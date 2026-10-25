# Model Artifacts

The notebook trains three report-level classifiers with one shared fitted
preprocessor. Its save cell serializes them with:

```python
joblib.dump(log_model, artifact_dir / "logistic_regression.joblib")
joblib.dump(rf_model, artifact_dir / "random_forest.joblib")
joblib.dump(gb_model, artifact_dir / "gradient_boosting.joblib")
joblib.dump(best_model, artifact_dir / "best_model.joblib")
joblib.dump(preprocessor, artifact_dir / "preprocessor.joblib")
```

Those binary files are not embedded inside `drug_risk_classifier_api.ipynb`. To
avoid accidental retraining or synthetic artifacts, this directory is reserved
for the exact notebook-generated files:

- `preprocessor.joblib`
- `logistic_regression.joblib`
- `random_forest.joblib`
- `gradient_boosting.joblib`
- `best_model.joblib` (backwards-compatible copy of the notebook-selected model)

`ml.inference.predict()` loads these files once at import time when they are
available. Until then, it still reproduces the notebook's final drug-level FAERS
lookup, which the notebook explicitly documents as a direct statistic rather
than a trained-model prediction.
