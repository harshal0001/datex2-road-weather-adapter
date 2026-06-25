"""Train the road-condition forecast model.

Predicts the SWS road-condition class (0 dry · 1 moist · 2 wet · 3 ice · 4 snow)
from atmospheric features only (DWD/LoRaWAN/OpenWeather), i.e. WITHOUT a road
sensor — the prototype's "predict ice where there is no SWS station" path.

HistGradientBoostingClassifier handles missing features natively (sources are
often partial). Reports a held-out accuracy / macro-F1 / per-class report and
saves model + feature list + classes to data/forecast_model.joblib.

Run:  .venv/bin/python scripts/train_forecast.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / "data" / "_training.parquet"
MODEL = ROOT / "data" / "forecast_model.joblib"


def main() -> int:
    import joblib
    import pandas as pd
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score, classification_report, f1_score
    from sklearn.model_selection import train_test_split

    if not TRAIN.exists():
        print(f"{TRAIN} not found — run scripts/build_training.py first.")
        return 1

    df = pd.read_parquet(TRAIN)
    df = df.dropna(subset=["y"])
    y = df["y"].astype(int)
    X = df.drop(columns=["y"])
    features = list(X.columns)
    print(f"{len(df):,} rows · {len(features)} features · classes {sorted(y.unique())}")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = HistGradientBoostingClassifier(
        max_iter=400, learning_rate=0.08, max_depth=8,
        l2_regularization=1.0, class_weight="balanced", random_state=42,
    )
    clf.fit(Xtr, ytr)

    pred = clf.predict(Xte)
    acc = accuracy_score(yte, pred)
    f1 = f1_score(yte, pred, average="macro")
    LABELS = {0: "dry", 1: "moist", 2: "wet", 3: "ice", 4: "snow"}
    print(f"\nHeld-out accuracy: {acc:.3f} · macro-F1: {f1:.3f}\n")
    print(classification_report(yte, pred, target_names=[LABELS.get(c, str(c)) for c in sorted(y.unique())]))

    joblib.dump(
        {"model": clf, "features": features, "classes": [int(c) for c in clf.classes_],
         "accuracy": float(acc), "macro_f1": float(f1)},
        MODEL,
    )
    print(f"Saved → {MODEL}  ({MODEL.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
