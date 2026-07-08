"""
ml/training/train_model.py
==========================
Trains, evaluates, and serialises the symptom-disease classification model.

Architecture
------------
  Primary   : Random Forest  (fast, interpretable, no GPU needed)
  Secondary : Gradient Boosting (XGBoost if available, else sklearn GBM)
  Fallback  : Logistic Regression (baseline)

All three are trained; the best by validation macro-F1 is saved as
  ml/saved_models/disease_model.pkl
  (symlinked into backend/app/models/disease_model.pkl)

Run
---
  cd ai-medical-assistant/
  python ml/training/train_model.py

Requirements (see ml/requirements.txt)
  scikit-learn>=1.4
  numpy, pandas, joblib, matplotlib, seaborn
  xgboost>=2.0   (optional — auto-detected)
"""

import json
import time
import logging
import warnings
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import cross_val_score

try:
    # from xgboost import XGBClassifier
    HAS_XGB = False
except ImportError:
    HAS_XGB = False

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

from preprocess import run_preprocessing, SAVED_DIR, BASE_DIR

warnings.filterwarnings("ignore")

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Output paths ───────────────────────────────────────────────────────────────
MODEL_PATH   = SAVED_DIR / "disease_model.pkl"
ENCODER_PATH = SAVED_DIR / "label_encoder.pkl"
MLB_PATH     = SAVED_DIR / "symptom_binarizer.pkl"
REPORT_PATH  = SAVED_DIR / "training_report.json"
BACKEND_MODEL_PATH = BASE_DIR / "backend" / "app" / "models" / "disease_model.pkl"


# ──────────────────────────────────────────────────────────────────────────────
# Model definitions
# ──────────────────────────────────────────────────────────────────────────────

def _build_candidates() -> Dict[str, Any]:
    """Return a dict of {name: estimator} to evaluate."""
    candidates = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features="sqrt",
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        ),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=2000,
                C=1.0,
                class_weight="balanced",
                solver="lbfgs",
                multi_class="multinomial",
                random_state=42,
            )),
        ]),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            subsample=0.8,
            random_state=42,
        ),
    }

    if False and HAS_XGB:
        log.info("XGBoost detected — adding XGBClassifier to candidates.")
        candidates["XGBoost"] = XGBClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="mlogloss",
            n_jobs=-1,
            random_state=42,
        )

    return candidates


# ──────────────────────────────────────────────────────────────────────────────
# Training & evaluation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _train_and_evaluate(
    name: str,
    model: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val:   np.ndarray,
    y_val:   np.ndarray,
) -> Tuple[Any, Dict]:
    """Fit model on train split, evaluate on val split."""
    log.info("[%s] Training …", name)
    t0 = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - t0

    y_pred    = model.predict(X_val)
    acc       = accuracy_score(y_val, y_pred)
    macro_f1  = f1_score(y_val, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_val, y_pred, average="weighted", zero_division=0)

    log.info(
        "[%s] val_acc=%.4f  macro_f1=%.4f  weighted_f1=%.4f  (%.1fs)",
        name, acc, macro_f1, weighted_f1, elapsed,
    )

    metrics = {
        "val_accuracy":    round(acc, 4),
        "val_macro_f1":    round(macro_f1, 4),
        "val_weighted_f1": round(weighted_f1, 4),
        "train_time_s":    round(elapsed, 2),
    }
    return model, metrics


def _cross_validate_best(
    model: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    cv: int = 5,
) -> Dict:
    """Run k-fold CV on the combined train set."""
    log.info("Running %d-fold cross-validation on best model …", cv)
    scores = cross_val_score(
        model, X_train, y_train,
        cv=cv, scoring="f1_macro", n_jobs=-1,
    )
    result = {
        "cv_folds":   cv,
        "cv_mean_f1": round(float(scores.mean()), 4),
        "cv_std_f1":  round(float(scores.std()), 4),
    }
    log.info("CV macro-F1: %.4f ± %.4f", result["cv_mean_f1"], result["cv_std_f1"])
    return result


def _final_test_eval(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: List[str],
) -> Dict:
    """Evaluate the final model on the held-out test set."""
    y_pred = model.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    macro_f1  = f1_score(y_test, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    log.info(
        "TEST RESULTS — acc=%.4f  macro_f1=%.4f  weighted_f1=%.4f",
        acc, macro_f1, weighted_f1,
    )
    report = classification_report(
        y_test, y_pred,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    return {
        "test_accuracy":    round(acc, 4),
        "test_macro_f1":    round(macro_f1, 4),
        "test_weighted_f1": round(weighted_f1, 4),
        "per_class_report": report,
    }


def _plot_confusion_matrix(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: List[str],
) -> None:
    """Save a confusion matrix heatmap (requires matplotlib + seaborn)."""
    if not HAS_PLOT:
        return
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(max(10, len(class_names)), max(8, len(class_names) - 2)))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
    )
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("Actual", fontsize=11)
    ax.set_title("Confusion Matrix — Test Set", fontsize=13)
    plt.tight_layout()
    out = SAVED_DIR / "confusion_matrix.png"
    plt.savefig(out, dpi=120)
    plt.close()
    log.info("Confusion matrix saved → %s", out)


def _plot_feature_importance(
    model: Any,
    feature_names: List[str],
    top_n: int = 25,
) -> None:
    """Save a feature importance bar chart for tree-based models."""
    if not HAS_PLOT:
        return
    clf = model.named_steps["clf"] if hasattr(model, "named_steps") else model
    if not hasattr(clf, "feature_importances_"):
        return
    importances = clf.feature_importances_
    indices     = np.argsort(importances)[::-1][:top_n]
    top_feats   = [feature_names[i] for i in indices]
    top_vals    = importances[indices]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top_feats[::-1], top_vals[::-1], color="#2196F3", edgecolor="none")
    ax.set_xlabel("Importance", fontsize=11)
    ax.set_title(f"Top-{top_n} Symptom Importances", fontsize=13)
    plt.tight_layout()
    out = SAVED_DIR / "feature_importances.png"
    plt.savefig(out, dpi=120)
    plt.close()
    log.info("Feature importance chart saved → %s", out)


# ──────────────────────────────────────────────────────────────────────────────
# Calibration wrapper
# ──────────────────────────────────────────────────────────────────────────────

def _calibrate(model: Any, X_val: np.ndarray, y_val: np.ndarray) -> Any:
    """
    Wrap the best model with Platt/isotonic calibration so predict_proba()
    returns well-calibrated confidence scores for the agent pipeline.
    """
    log.info("Calibrating probability estimates (method=sigmoid) …")
    calibrated = CalibratedClassifierCV(model, method="sigmoid", cv="prefit")
    calibrated.fit(X_val, y_val)
    return calibrated


# ──────────────────────────────────────────────────────────────────────────────
# Inference utility (used by backend prediction_service.py)
# ──────────────────────────────────────────────────────────────────────────────

def predict_diseases(
    symptoms: List[str],
    model:    Any,
    mlb:      Any,
    le:       Any,
    top_k:    int = 3,
) -> List[Dict]:
    """
    Parameters
    ----------
    symptoms : list of normalised symptom strings
    model    : trained calibrated classifier
    mlb      : fitted MultiLabelBinarizer
    le       : fitted LabelEncoder
    top_k    : number of top predictions to return

    Returns
    -------
    list of dicts: [{"disease": str, "probability": float, "rank": int}]
    """
    # Encode input symptoms (unknown symptoms → silently ignored)
    known = [s for s in symptoms if s in mlb.classes_]
    if not known:
        return []

    X       = mlb.transform([known])
    proba   = model.predict_proba(X)[0]          # shape: (n_classes,)
    top_idx = np.argsort(proba)[::-1][:top_k]

    return [
        {
            "disease":     le.classes_[i],
            "probability": round(float(proba[i]), 4),
            "confidence":  _confidence_label(proba[i]),
            "rank":        rank + 1,
        }
        for rank, i in enumerate(top_idx)
        if proba[i] > 0.01
    ]


def _confidence_label(prob: float) -> str:
    if prob >= 0.70:
        return "high"
    elif prob >= 0.40:
        return "medium"
    return "low"


# ──────────────────────────────────────────────────────────────────────────────
# Main training entry point
# ──────────────────────────────────────────────────────────────────────────────

def train() -> None:
    print("\n" + "=" * 60)
    print("  AI Medical Assistant — Model Training Pipeline")
    print("=" * 60 + "\n")

    # ── 1. Preprocess ──────────────────────────────────────────────────────────
    data = run_preprocessing()
    X_train, y_train = data["X_train"], data["y_train"]
    X_val,   y_val   = data["X_val"],   data["y_val"]
    X_test,  y_test  = data["X_test"],  data["y_test"]
    mlb, le          = data["mlb"],     data["le"]
    class_names      = list(le.classes_)
    symptom_names    = list(mlb.classes_)

    # ── 2. Train all candidates ────────────────────────────────────────────────
    candidates    = _build_candidates()
    all_metrics: Dict[str, Dict] = {}
    trained_models: Dict[str, Any] = {}

    for name, estimator in candidates.items():
        model, metrics = _train_and_evaluate(
            name, estimator, X_train, y_train, X_val, y_val
        )
        all_metrics[name]    = metrics
        trained_models[name] = model

    # ── 3. Select best model by val macro-F1 ──────────────────────────────────
    best_name = max(all_metrics, key=lambda n: all_metrics[n]["val_macro_f1"])
    best_model = trained_models[best_name]
    log.info("Best model: %s  (val macro-F1 = %.4f)", best_name, all_metrics[best_name]["val_macro_f1"])

    # ── 4. Cross-validate best ─────────────────────────────────────────────────
    cv_metrics = _cross_validate_best(best_model, X_train, y_train)

    # ── 5. Calibrate probabilities ─────────────────────────────────────────────
    calibrated = _calibrate(best_model, X_val, y_val)

    # ── 6. Final test evaluation ───────────────────────────────────────────────
    test_metrics = _final_test_eval(calibrated, X_test, y_test, class_names)

    # ── 7. Plots ───────────────────────────────────────────────────────────────
    _plot_confusion_matrix(calibrated, X_test, y_test, class_names)
    _plot_feature_importance(best_model, symptom_names)

    # ── 8. Persist artefacts ───────────────────────────────────────────────────
    joblib.dump(calibrated, MODEL_PATH)
    joblib.dump(mlb, MLB_PATH)
    joblib.dump(le,  ENCODER_PATH)
    log.info("Model saved          → %s", MODEL_PATH)
    log.info("Symptom binarizer    → %s", MLB_PATH)
    log.info("Label encoder        → %s", ENCODER_PATH)

    # Copy model into backend for immediate use
    BACKEND_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MODEL_PATH, BACKEND_MODEL_PATH)
    log.info("Backend model copy   → %s", BACKEND_MODEL_PATH)

    # ── 9. Training report ─────────────────────────────────────────────────────
    report = {
        "best_model":        best_name,
        "dataset_info": {
            "n_samples":  data["n_samples"],
            "n_features": data["n_features"],
            "n_classes":  data["n_classes"],
        },
        "candidate_metrics": all_metrics,
        "cross_validation":  cv_metrics,
        "test_metrics":      {k: v for k, v in test_metrics.items() if k != "per_class_report"},
        "per_class_f1": {
            cls: round(test_metrics["per_class_report"].get(cls, {}).get("f1-score", 0), 4)
            for cls in class_names
        },
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    log.info("Training report      → %s", REPORT_PATH)

    # ── 10. Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Best model   : {best_name}")
    print(f"  Diseases     : {data['n_classes']}")
    print(f"  Symptoms     : {data['n_features']}")
    print(f"  Val macro-F1 : {all_metrics[best_name]['val_macro_f1']:.4f}")
    print(f"  Test acc     : {test_metrics['test_accuracy']:.4f}")
    print(f"  Test macro-F1: {test_metrics['test_macro_f1']:.4f}")
    print(f"  CV F1        : {cv_metrics['cv_mean_f1']:.4f} ± {cv_metrics['cv_std_f1']:.4f}")
    print("=" * 60 + "\n")

    # ── 11. Quick smoke-test ────────────────────────────────────────────────────
    test_symptoms = ["fever", "headache", "muscle_pain", "chills"]
    predictions   = predict_diseases(test_symptoms, calibrated, mlb, le, top_k=3)
    print("Smoke-test — symptoms:", test_symptoms)
    print("Top predictions:")
    for p in predictions:
        print(f"  [{p['rank']}] {p['disease']:<35} {p['probability']:.2%}  ({p['confidence']})")
    print()


if __name__ == "__main__":
    train()
