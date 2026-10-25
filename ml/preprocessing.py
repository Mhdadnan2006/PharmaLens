"""Reusable preprocessing helpers for openFDA FAERS adverse-event reports.

The functions in this module are direct, notebook-free extractions of the data
loading and report parsing logic from ``drug_risk_classifier_api.ipynb``. They
do not train models and do not depend on notebook state.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
import requests


NUMERIC_COLUMNS: list[str] = ["age", "weight", "num_reactions", "num_drugs"]
"""Numeric columns used by the fitted scikit-learn preprocessor."""

CATEGORICAL_COLUMNS: list[str] = ["sex", "route", "qualification", "country"]
"""Categorical columns used by the fitted scikit-learn preprocessor."""

FEATURE_COLUMNS: list[str] = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS
"""Raw feature columns expected before applying the fitted preprocessor."""

LOW_RISK_CUTOFF_PCT = 71.1
"""Rounded 33rd-percentile serious-report threshold printed by the notebook."""

HIGH_RISK_CUTOFF_PCT = 83.6
"""Rounded 66th-percentile serious-report threshold printed by the notebook."""

OPENFDA_DRUG_EVENT_URL = "https://api.fda.gov/drug/event.json"


def fetch_reports_for_drug(drug_name: str, limit: int = 200, timeout: int = 30) -> list[dict[str, Any]]:
    """Fetch FAERS adverse-event reports for a drug from openFDA.

    Args:
        drug_name: Medicinal product name to search for.
        limit: Maximum number of reports to fetch. The notebook used ``200``.
        timeout: HTTP timeout in seconds.

    Returns:
        A list of raw openFDA report dictionaries. Each report includes the
        notebook-compatible ``_queried_drug`` key.

    Raises:
        requests.HTTPError: If openFDA returns an unsuccessful response.
        requests.RequestException: If the request fails.
    """

    normalized_name = drug_name.strip()
    params = {
        "search": f'patient.drug.medicinalproduct:"{normalized_name}"',
        "limit": limit,
    }
    response = requests.get(OPENFDA_DRUG_EVENT_URL, params=params, timeout=timeout)
    response.raise_for_status()

    reports = response.json().get("results", [])
    for report in reports:
        report["_queried_drug"] = normalized_name
    return reports


def parse_report(report: dict[str, Any]) -> dict[str, Any]:
    """Flatten one raw openFDA FAERS report into the notebook's tabular shape."""

    patient = report.get("patient", {})
    reactions = patient.get("reaction", [])
    drugs = patient.get("drug", [])

    suspect_route = None
    for drug in drugs:
        if drug.get("drugcharacterization") == "1":
            suspect_route = drug.get("drugadministrationroute")
            break

    return {
        "safetyreportid": report.get("safetyreportid"),
        "queried_drug": report.get("_queried_drug"),
        "age": patient.get("patientonsetage"),
        "age_unit": patient.get("patientonsetageunit"),
        "sex": patient.get("patientsex"),
        "weight": patient.get("patientweight"),
        "num_reactions": len(reactions),
        "num_drugs": len(drugs),
        "route": suspect_route,
        "qualification": report.get("primarysource", {}).get("qualification"),
        "country": report.get("occurcountry"),
        "reaction_terms": [reaction.get("reactionmeddrapt") for reaction in reactions],
        "serious": report.get("serious"),
    }


def reports_to_frame(reports: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Parse raw FAERS reports and remove duplicate safety report IDs."""

    frame = pd.DataFrame([parse_report(report) for report in reports])
    if frame.empty:
        return frame
    return frame.drop_duplicates(subset="safetyreportid").copy()


def clean_report_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply notebook-compatible raw feature cleaning before transformation.

    This performs only deterministic fixes that the notebook applied before
    model preprocessing: numeric conversion, age-unit filtering, plausible age
    clipping, and constant fills for categorical values. Learned preprocessing
    steps such as median imputation, scaling, and one-hot encoding remain the
    responsibility of the serialized scikit-learn preprocessor.
    """

    cleaned = frame.copy()
    if cleaned.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    cleaned["age"] = pd.to_numeric(cleaned["age"], errors="coerce")
    cleaned.loc[cleaned["age_unit"] != "801", "age"] = pd.NA
    cleaned.loc[(cleaned["age"] < 0) | (cleaned["age"] > 110), "age"] = pd.NA

    cleaned["weight"] = pd.to_numeric(cleaned["weight"], errors="coerce")
    cleaned["sex"] = cleaned["sex"].fillna("0")
    cleaned["route"] = cleaned["route"].fillna("Unknown")
    cleaned["qualification"] = cleaned["qualification"].fillna("Unknown")
    cleaned["country"] = cleaned["country"].fillna("Unknown")

    return cleaned[FEATURE_COLUMNS].copy()


def clean_serious_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Map the notebook's openFDA serious labels to integers and drop missing targets."""

    cleaned = frame.copy()
    if cleaned.empty or "serious" not in cleaned:
        return cleaned

    cleaned["serious"] = cleaned["serious"].map({"1": 1, "2": 0})
    cleaned = cleaned.dropna(subset=["serious"]).copy()
    cleaned["serious"] = cleaned["serious"].astype(int)
    return cleaned


def classify_risk_level(percent_serious: float) -> str:
    """Map a serious-report percentage to the notebook's Low/Medium/High classes."""

    if percent_serious < LOW_RISK_CUTOFF_PCT:
        return "Low"
    if percent_serious < HIGH_RISK_CUTOFF_PCT:
        return "Medium"
    return "High"


def summarize_side_effects(frame: pd.DataFrame, top_n: int = 5) -> list[dict[str, float | int | str]]:
    """Return the most frequently reported reactions with report-relative probabilities."""

    total_reports = len(frame)
    if total_reports == 0 or "reaction_terms" not in frame:
        return []

    reactions: list[str] = []
    for terms in frame["reaction_terms"]:
        if not isinstance(terms, list):
            continue
        reactions.extend(term for term in terms if term)

    if not reactions:
        return []

    counts = pd.Series(reactions).value_counts().head(top_n)
    return [
        {
            "name": str(reaction),
            "count": int(count),
            "probability": round(float(count) / float(total_reports), 6),
        }
        for reaction, count in counts.items()
    ]

