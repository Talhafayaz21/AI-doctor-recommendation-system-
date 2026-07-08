"""
ml/training/preprocess.py
=========================
Preprocessing pipeline for the symptom-disease classification model.

Handles:
  - Raw CSV ingestion (Kaggle-style symptom dataset)
  - Symptom column normalization & deduplication
  - Binary MultiLabelBinarizer encoding
  - Train / validation / test splitting (stratified)
  - Serialised artefact export  →  ml/saved_models/
"""

import os
import re
import json
import logging
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, List, Dict

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer, LabelEncoder

warnings.filterwarnings("ignore")

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parents[1]          # ai-medical-assistant/care-companion-main/
DATASET_DIR = BASE_DIR / "ml" / "dataset"
SAVED_DIR   = BASE_DIR / "ml" / "saved_models"
SAVED_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
SYMPTOM_COLS = [f"Symptom_{i}" for i in range(1, 18)]     # up to 17 symptom cols
TEST_SIZE    = 0.15
VAL_SIZE     = 0.15
RANDOM_STATE = 42

# Curated symptom synonyms – normalise free-text variations to canonical names
SYNONYM_MAP: Dict[str, str] = {
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


# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────

def _normalise_symptom(raw: str) -> str:
    """Lower-case, strip whitespace, collapse spaces → underscores."""
    s = str(raw).lower().strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    readable = s.replace("_", " ")
    return SYNONYM_MAP.get(readable, s)


def _load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV, accepting either semicolon or comma delimiters."""
    try:
        df = pd.read_csv(path)
    except Exception:
        df = pd.read_csv(path, sep=";")
    log.info("Loaded %s  →  %d rows, %d cols", path.name, *df.shape)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Synthetic dataset generator (fallback when no CSV is present)
# ──────────────────────────────────────────────────────────────────────────────

def generate_synthetic_dataset(n_samples: int = 4800) -> pd.DataFrame:
    """
    Generate a synthetic symptom-disease dataset when no real CSV is present.
    Produces a Kaggle-compatible wide format:
        Disease | Symptom_1 | Symptom_2 | ... | Symptom_17

    For production, replace with the Kaggle 'Disease Symptom Prediction' dataset:
    https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset
    """
    log.info("Generating synthetic dataset (%d samples) …", n_samples)

    DISEASE_PROFILES: Dict[str, Dict] = {
        "Common Cold": {
            "required": ["cough", "runny_nose", "sore_throat"],
            "optional": ["headache", "mild_fever", "fatigue", "chills", "sneezing"],
        },
        "Influenza": {
            "required": ["fever", "cough", "fatigue"],
            "optional": ["headache", "chills", "muscle_pain", "sore_throat", "loss_of_appetite"],
        },
        "Pneumonia": {
            "required": ["fever", "cough", "breathlessness"],
            "optional": ["chest_pain", "fatigue", "chills", "nausea", "sweating"],
        },
        "Dengue": {
            "required": ["fever", "muscle_pain", "headache"],
            "optional": ["skin_rash", "nausea", "vomiting", "fatigue", "chills"],
        },
        "Malaria": {
            "required": ["fever", "chills", "sweating"],
            "optional": ["headache", "nausea", "vomiting", "fatigue", "muscle_pain"],
        },
        "Typhoid": {
            "required": ["fever", "stomach_pain", "loss_of_appetite"],
            "optional": ["headache", "nausea", "vomiting", "fatigue", "diarrhoea"],
        },
        "Diabetes": {
            "required": ["excessive_thirst", "increased_urination", "fatigue"],
            "optional": ["blurred_and_distorted_vision", "weight_loss", "dizziness", "itching"],
        },
        "Hypertension": {
            "required": ["headache", "dizziness", "chest_pain"],
            "optional": ["breathlessness", "fatigue", "anxiety", "blurred_and_distorted_vision"],
        },
        "Migraine": {
            "required": ["headache", "nausea", "blurred_and_distorted_vision"],
            "optional": ["vomiting", "dizziness", "irritability", "fatigue"],
        },
        "Gastroenteritis": {
            "required": ["nausea", "vomiting", "diarrhoea"],
            "optional": ["stomach_pain", "fever", "fatigue", "loss_of_appetite"],
        },
        "Hepatitis A": {
            "required": ["yellowing_of_skin", "fatigue", "loss_of_appetite"],
            "optional": ["nausea", "vomiting", "stomach_pain", "fever", "itching"],
        },
        "Hepatitis B": {
            "required": ["yellowing_of_skin", "fatigue", "stomach_pain"],
            "optional": ["nausea", "vomiting", "loss_of_appetite", "joint_pain", "itching"],
        },
        "Tuberculosis": {
            "required": ["cough", "weight_loss", "fatigue"],
            "optional": ["fever", "sweating", "chest_pain", "breathlessness", "loss_of_appetite"],
        },
        "Asthma": {
            "required": ["breathlessness", "cough", "chest_pain"],
            "optional": ["fatigue", "anxiety", "sweating"],
        },
        "Urinary Tract Infection": {
            "required": ["increased_urination", "burning_micturition", "fatigue"],
            "optional": ["fever", "back_pain", "stomach_pain", "nausea"],
        },
        "Anxiety Disorder": {
            "required": ["anxiety", "irritability", "fatigue"],
            "optional": ["headache", "dizziness", "sweating", "chest_pain", "depression"],
        },
        "Depression": {
            "required": ["depression", "fatigue", "loss_of_appetite"],
            "optional": ["anxiety", "irritability", "weight_loss", "dizziness"],
        },
        "Chickenpox": {
            "required": ["skin_rash", "itching", "fever"],
            "optional": ["fatigue", "loss_of_appetite", "headache", "muscle_pain"],
        },
        "COVID-19": {
            "required": ["fever", "cough", "fatigue"],
            "optional": ["breathlessness", "loss_of_smell", "sore_throat", "muscle_pain", "diarrhoea"],
        },
        "Arthritis": {
            "required": ["joint_pain", "swelling_joints", "fatigue"],
            "optional": ["fever", "muscle_pain", "back_pain", "weight_loss"],
        },
    }

    rng        = np.random.default_rng(RANDOM_STATE)
    rows: List = []
    per_disease = n_samples // len(DISEASE_PROFILES)

    for disease, profile in DISEASE_PROFILES.items():
        req = profile["required"]
        opt = profile["optional"]
        for _ in range(per_disease):
            k        = rng.integers(1, len(opt) + 1)
            selected = req + list(rng.choice(opt, size=min(k, len(opt)), replace=False))
            rng.shuffle(selected)
            row = {"Disease": disease}
            for idx, sym in enumerate(selected[:17], start=1):
                row[f"Symptom_{idx}"] = sym
            rows.append(row)

    df = pd.DataFrame(rows)
    for c in SYMPTOM_COLS:
        if c not in df.columns:
            df[c] = np.nan
    df = df[["Disease"] + SYMPTOM_COLS]

    out = DATASET_DIR / "symptoms_dataset.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    log.info("Synthetic dataset saved → %s", out)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Core preprocessing steps
# ──────────────────────────────────────────────────────────────────────────────

def build_symptom_lists(df: pd.DataFrame) -> pd.Series:
    """
    Collapse wide symptom columns into a deduplicated list per row.
    Returns a pd.Series of List[str], aligned with df.index.
    """
    def _row(row: pd.Series) -> List[str]:
        seen, syms = set(), []
        for col in SYMPTOM_COLS:
            val = row.get(col, np.nan)
            if pd.notna(val) and str(val).strip():
                n = _normalise_symptom(val)
                if n and n not in seen:
                    syms.append(n)
                    seen.add(n)
        return syms

    return df.apply(_row, axis=1)


def encode_features(
    symptom_lists: pd.Series,
) -> Tuple[np.ndarray, MultiLabelBinarizer]:
    mlb = MultiLabelBinarizer()
    X   = mlb.fit_transform(symptom_lists)
    log.info("Feature matrix: %d samples × %d unique symptoms", *X.shape)
    return X, mlb


def encode_labels(
    disease_series: pd.Series,
) -> Tuple[np.ndarray, LabelEncoder]:
    le = LabelEncoder()
    y  = le.fit_transform(disease_series)
    log.info("Label encoder: %d unique diseases", len(le.classes_))
    return y, le


def split_data(X: np.ndarray, y: np.ndarray) -> Dict[str, np.ndarray]:
    """Stratified 70 / 15 / 15 split."""
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(
        X, y,
        test_size=TEST_SIZE + VAL_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
    )
    val_ratio = VAL_SIZE / (TEST_SIZE + VAL_SIZE)
    X_val, X_te, y_val, y_te = train_test_split(
        X_tmp, y_tmp,
        test_size=1 - val_ratio,
        stratify=y_tmp,
        random_state=RANDOM_STATE,
    )
    log.info(
        "Split → train %d | val %d | test %d",
        len(y_tr), len(y_val), len(y_te),
    )
    return {
        "X_train": X_tr,  "y_train": y_tr,
        "X_val":   X_val, "y_val":   y_val,
        "X_test":  X_te,  "y_test":  y_te,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def run_preprocessing() -> Dict:
    """
    Full preprocessing pipeline.

    Returns
    -------
    dict with keys:
        X_train, y_train, X_val, y_val, X_test, y_test,
        mlb, le, n_samples, n_features, n_classes,
        all_symptoms, all_diseases, class_counts
    """
    # 1. Load or generate dataset
    csv_candidates = list(DATASET_DIR.glob("dataset.csv"))
    if not csv_candidates:
        csv_candidates = list(DATASET_DIR.glob("*.csv"))
    if csv_candidates:
        df = _load_csv(csv_candidates[0])
    else:
        log.warning("No CSV found in %s — generating synthetic data.", DATASET_DIR)
        df = generate_synthetic_dataset()

    if "Disease" not in df.columns:
        raise ValueError("Dataset must contain a 'Disease' column.")

    df = df.dropna(subset=["Disease"]).reset_index(drop=True)

    # 2. Build symptom lists
    symptom_lists = build_symptom_lists(df)
    empty_mask    = symptom_lists.apply(lambda s: len(s) == 0)
    if empty_mask.any():
        log.warning("Dropping %d rows with zero extractable symptoms.", empty_mask.sum())
        df            = df[~empty_mask].reset_index(drop=True)
        symptom_lists = symptom_lists[~empty_mask].reset_index(drop=True)

    # 3. Encode features & labels
    X, mlb = encode_features(symptom_lists)
    y, le  = encode_labels(df["Disease"])

    # 4. Split
    splits = split_data(X, y)

    # 5. Persist metadata
    meta = {
        "n_samples":   int(len(df)),
        "n_features":  int(X.shape[1]),
        "n_classes":   int(len(le.classes_)),
        "all_symptoms": list(mlb.classes_),
        "all_diseases": list(le.classes_),
        "class_counts": {d: int((y == i).sum()) for i, d in enumerate(le.classes_)},
    }
    with open(SAVED_DIR / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    log.info("Metadata saved → %s/metadata.json", SAVED_DIR)

    return {**splits, "mlb": mlb, "le": le, **meta}


if __name__ == "__main__":
    data = run_preprocessing()
    print("\n── Preprocessing complete ──────────────────────────────")
    print(f"  Symptoms  : {data['n_features']}")
    print(f"  Diseases  : {data['n_classes']}")
    print(f"  Train/Val/Test : {len(data['y_train'])} / {len(data['y_val'])} / {len(data['y_test'])}")
    print("────────────────────────────────────────────────────────\n")
