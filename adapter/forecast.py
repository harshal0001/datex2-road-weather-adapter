"""Road-condition forecast inference.

Loads the model trained by scripts/train_forecast.py and predicts a road-surface
condition (+ probability) from fused atmospheric features — the same canonical
fields the fusion engine produces from non-SWS sources. This is the prototype's
prediction path: estimate road condition where there is no SWS road sensor.

Returns None throughout if the model file is absent, so the app runs without it.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "forecast_model.joblib"

# class code -> canonical condition label + DATEX II literal (mirrors segment_conditions.yaml)
_LABELS = {0: "Dry", 1: "Damp", 2: "Wet", 3: "Ice", 4: "Snow"}
_DATEX = {0: "dry", 1: "moist", 2: "wet", 3: "ice", 4: "snowOnTheRoad"}


@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        return None
    import joblib

    return joblib.load(MODEL_PATH)


def available() -> bool:
    return load_model() is not None


def predict(features: dict) -> dict | None:
    """Predict road condition from a dict of canonical features.

    features: {canonical_field: value} — missing fields are fine (NaN-tolerant).
    Returns {code, label, datex2, probability, probabilities, accuracy} or None.
    """
    bundle = load_model()
    if bundle is None:
        return None
    import numpy as np
    import pandas as pd

    cols = bundle["features"]
    row = pd.DataFrame([{c: (float(features[c]) if features.get(c) is not None else np.nan)
                         for c in cols}], columns=cols)
    model = bundle["model"]
    proba = model.predict_proba(row)[0]
    classes = list(model.classes_)
    top = int(classes[int(proba.argmax())])
    return {
        "code": top,
        "label": _LABELS.get(top, "Unknown"),
        "datex2": _DATEX.get(top, "other"),
        "probability": round(float(proba.max()), 3),
        "probabilities": {_LABELS.get(int(c), str(c)): round(float(p), 3)
                          for c, p in zip(classes, proba)},
        "accuracy": bundle.get("accuracy"),
    }
