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


# meteorologically salient inputs for the "on what basis" panel (display order)
SALIENT = [
    ("road_surface_temp_c", "Road surface temp", "°C"),
    ("air_temp_c", "Air temp", "°C"),
    ("dew_point_c", "Dew point", "°C"),
    ("humidity_pct", "Humidity", "%"),
    ("precipitation_mm_h", "Precipitation", "mm/h"),
    ("subsurface_temp_5cm_c", "Subsurface temp", "°C"),
    ("wind_speed_ms", "Wind", "m/s"),
]


def _num(features: dict, key: str):
    v = features.get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def signal(probabilities: dict) -> dict:
    """How decisive the prediction is: top probability + margin over runner-up."""
    vals = sorted(probabilities.values(), reverse=True)
    top = vals[0] if vals else 0.0
    margin = top - (vals[1] if len(vals) > 1 else 0.0)
    level = ("strong" if top >= 0.75 and margin >= 0.4
             else "moderate" if top >= 0.5 else "tentative")
    return {"level": level, "top": round(top, 3), "margin": round(margin, 3)}


def explain(features: dict, label: str) -> list[str]:
    """Plain-English indicators consistent with the predicted class, quoting the
    actual input values. Interpretive (rule-of-thumb per the published Decision
    Tree logic) — an aid for stakeholders, not the literal model tree path."""
    st, at = _num(features, "road_surface_temp_c"), _num(features, "air_temp_c")
    dp, hum = _num(features, "dew_point_c"), _num(features, "humidity_pct")
    pr = _num(features, "precipitation_mm_h")
    temp = st if st is not None else at            # prefer surface, fall back to air
    tname = "surface" if st is not None else "air"
    r: list[str] = []
    if label == "Ice":
        if temp is not None and temp <= 0.5:
            r.append(f"{tname} {temp:.1f}°C — at/below freezing")
        if hum is not None and hum >= 85:
            r.append(f"humidity {hum:.0f}% — moisture available to freeze")
        if st is not None and dp is not None and dp >= st - 0.5:
            r.append(f"dew point {dp:.1f}°C ≈ surface {st:.1f}°C — frost/condensation likely")
    elif label == "Snow":
        if pr and pr > 0:
            r.append(f"precipitation {pr:.2f} mm/h falling")
        if at is not None and at <= 1:
            r.append(f"air {at:.1f}°C — cold enough for snow")
    elif label == "Wet":
        if pr and pr > 0:
            r.append(f"precipitation {pr:.2f} mm/h")
        if temp is not None and temp > 1:
            r.append(f"{tname} {temp:.1f}°C — above freezing, water stays liquid")
    elif label == "Damp":
        if hum is not None and hum >= 80:
            r.append(f"high humidity {hum:.0f}% with no precipitation")
        if temp is not None and temp > 0:
            r.append(f"{tname} {temp:.1f}°C — above freezing")
    elif label == "Dry":
        if hum is not None and hum < 80:
            r.append(f"humidity {hum:.0f}% — relatively dry air")
        if temp is not None and temp > 2:
            r.append(f"{tname} {temp:.1f}°C — well above freezing")
        if not pr:
            r.append("no precipitation")
    if not r:
        r.append("model weighed the combined atmospheric inputs (no single dominant signal)")
    return r


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
