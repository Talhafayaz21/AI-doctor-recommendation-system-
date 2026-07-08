"""
backend/app/services/prediction_service.py
==========================================
Loads the trained disease_model.pkl and exposes a clean prediction API
consumed by diagnosis_agent.py.

This is the bridge between the ML layer and the LLM agent pipeline.
"""

import json
import logging
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parents[3]        # ai-medical-assistant/
MODELS_DIR    = BASE_DIR / "backend" / "app" / "models"
ML_SAVED      = BASE_DIR / "ml" / "saved_models"


\
# ──────────────────────────────────────────────────────────────────────────────
# Model loading  (singleton via lru_cache)
# ──────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_artifacts():
    """Load model, binarizer, encoder, and metadata exactly once."""
    model_path = MODELS_DIR / "disease_model.pkl"
    mlb_path   = ML_SAVED / "symptom_binarizer.pkl"
    le_path    = ML_SAVED / "label_encoder.pkl"
    meta_path  = ML_SAVED / "metadata.json"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model not found at {model_path}. "
            "Run `python ml/training/train_model.py` first."
        )

    model    = joblib.load(model_path)
    mlb      = joblib.load(mlb_path)
    le       = joblib.load(le_path)
    metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    log.info(
        "Model loaded — %d diseases, %d symptom features",
        len(le.classes_), len(mlb.classes_),
    )
    return model, mlb, le, metadata


# ──────────────────────────────────────────────────────────────────────────────
# Symptom normalisation (mirrors preprocess.py but standalone)
# ──────────────────────────────────────────────────────────────────────────────

import re

_SYNONYM_MAP: Dict[str, str] = {
    "high fever":           "fever",
    "low fever":            "mild_fever",
    "mild fever":           "mild_fever",
    "head ache":            "headache",
    "runny nose":           "runny_nose",
    "sore throat":          "sore_throat",
    "throat pain":          "sore_throat",
    "stomach ache":         "stomach_pain",
    "abdominal pain":       "stomach_pain",
    "shortness of breath":  "breathlessness",
    "chest tightness":      "chest_pain",
    "lower back pain":      "back_pain",
    "body ache":            "muscle_pain",
    "diarrhea":             "diarrhoea",
    "weakness":             "fatigue",
    "lethargy":             "fatigue",
    "skin rash":            "skin_rash",
    "yellowish skin":       "yellowing_of_skin",
    "jaundice":             "yellowing_of_skin",
    "dry cough":            "cough",
    "blurred vision":       "blurred_and_distorted_vision",
    "shivering":            "chills",
    "swollen glands":       "swollen_lymph_nodes",
}


def _normalise(raw: str) -> str:
    s = str(raw).lower().strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return _SYNONYM_MAP.get(s.replace("_", " "), s)


# ──────────────────────────────────────────────────────────────────────────────
# Core prediction function
# ──────────────────────────────────────────────────────────────────────────────

def predict(
    symptoms:          List[str],
    top_k:             int = 3,
    min_probability:   float = 0.02,
) -> Dict:
    """
    Parameters
    ----------
    symptoms        : raw symptom strings from the Symptom Extraction Agent
    top_k           : number of top predictions to return
    min_probability : filter out predictions below this threshold

    Returns
    -------
    {
        "predictions": [
            {"disease": str, "probability": float, "confidence": str, "rank": int}
        ],
        "risk_level":       "low" | "medium" | "high",
        "known_symptoms":   [str],
        "unknown_symptoms": [str],
        "model_version":    str,
    }
    """
    model, mlb, le, metadata = _load_artifacts()

    # Normalise and split into known / unknown
    normalised     = [_normalise(s) for s in symptoms]
    known_symptoms = [s for s in normalised if s in mlb.classes_]
    unknown        = [s for s in normalised if s not in mlb.classes_]

    if not known_symptoms:
        log.warning("No recognisable symptoms in input: %s", symptoms)
        return {
            "predictions":      [],
            "risk_level":       "low",
            "known_symptoms":   [],
            "unknown_symptoms": normalised,
            "model_version":    metadata.get("model_version", "1.0"),
        }

    # Encode → predict
    X     = mlb.transform([known_symptoms])
    proba = model.predict_proba(X)[0]           # shape: (n_classes,)

    top_indices = np.argsort(proba)[::-1][:top_k]
    predictions = [
        {
            "disease":     le.classes_[i],
            "probability": round(float(proba[i]), 4),
            "confidence":  _confidence_label(proba[i]),
            "rank":        rank + 1,
        }
        for rank, i in enumerate(top_indices)
        if proba[i] >= min_probability
    ]

    risk_level = _compute_risk(predictions)

    return {
        "predictions":      predictions,
        "risk_level":       risk_level,
        "known_symptoms":   known_symptoms,
        "unknown_symptoms": unknown,
        "model_version":    metadata.get("model_version", "1.0"),
    }


def _confidence_label(prob: float) -> str:
    if prob >= 0.65:
        return "high"
    elif prob >= 0.35:
        return "medium"
    return "low"


# High-risk conditions that trigger elevated risk_level regardless of probability
_HIGH_RISK_DISEASES = {
    "COVID-19", "Pneumonia", "Tuberculosis", "Heart Attack",
    "Dengue", "Malaria", "Hepatitis B", "Hepatitis C",
}

_MEDIUM_RISK_DISEASES = {
    "Influenza", "Typhoid", "Hypertension", "Diabetes",
    "Asthma", "Hepatitis A",
}


def _compute_risk(predictions: List[Dict]) -> str:
    if not predictions:
        return "low"

    top_disease = predictions[0]["disease"]
    top_prob    = predictions[0]["probability"]

    if top_disease in _HIGH_RISK_DISEASES and top_prob >= 0.25:
        return "high"
    if top_disease in _MEDIUM_RISK_DISEASES and top_prob >= 0.35:
        return "medium"
    if top_prob >= 0.70:
        return "medium"

    return "low"


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI route helper (called from backend/app/routes/diagnosis.py)
# ──────────────────────────────────────────────────────────────────────────────

def get_model_info() -> Dict:
    """Return metadata about the loaded model (for a /health or /model-info endpoint)."""
    _, _, le, metadata = _load_artifacts()
    return {
        "n_diseases":  len(le.classes_),
        "diseases":    list(le.classes_),
        "n_features":  metadata.get("n_features", "unknown"),
        "n_samples":   metadata.get("n_samples", "unknown"),
        "model_version": metadata.get("model_version", "1.0"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI smoke-test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        ["fever", "cough", "fatigue", "breathlessness"],
        ["joint pain", "fatigue", "fever", "swelling joints"],
        ["excessive thirst", "increased urination", "blurred vision"],
        ["headache", "nausea", "blurred vision"],
        ["skin rash", "itching", "fever"],
    ]

    print("\n── Prediction Service Smoke Test ───────────────────────")
    for symptoms in test_cases:
        result = predict(symptoms, top_k=3)
        print(f"\nSymptoms : {symptoms}")
        print(f"Risk     : {result['risk_level'].upper()}")
        print(f"Known    : {result['known_symptoms']}")
        for p in result["predictions"]:
            bar = "█" * int(p["probability"] * 20)
            print(f"  [{p['rank']}] {p['disease']:<30} {bar:<20} {p['probability']:.1%}")
    print("\n────────────────────────────────────────────────────────\n")
