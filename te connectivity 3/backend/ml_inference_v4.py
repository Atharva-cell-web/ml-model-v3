from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = PROJECT_ROOT / "models" / "scrap_risk_model_v4.pkl"
FEATURES_PATH = PROJECT_ROOT / "models" / "model_features_v4.pkl"
FEATURES_FALLBACK_PATH = PROJECT_ROOT / "new_processed_data" / "model_features_v4.pkl"

model = None
model_features = []
_missing_model_warned = False

print("[v4] Loading model:", MODEL_PATH)
if MODEL_PATH.exists():
    model = joblib.load(MODEL_PATH)
else:
    print(f"[v4] Warning: model file not found at {MODEL_PATH}. Using safe fallback risk=0.0")

if FEATURES_PATH.exists():
    model_features = joblib.load(FEATURES_PATH)
elif FEATURES_FALLBACK_PATH.exists():
    model_features = joblib.load(FEATURES_FALLBACK_PATH)
elif model is not None and hasattr(model, "feature_name_"):
    model_features = list(model.feature_name_)
else:
    model_features = []

print("[v4] Feature count:", len(model_features))


def predict_scrap_probability(sensor_row: dict):
    global _missing_model_warned

    if model is None:
        if not _missing_model_warned:
            print("[v4] Prediction fallback active: returning 0.0 because model is unavailable.")
            _missing_model_warned = True
        return 0.0

    row = {}

    if model_features:
        for f in model_features:
            row[f] = sensor_row.get(f, 0.0)
        ordered_features = model_features
    else:
        # If features file is missing, use incoming numeric keys as a best-effort fallback.
        row = {k: v for k, v in sensor_row.items()}
        ordered_features = list(row.keys())

    X = pd.DataFrame([row])[ordered_features].fillna(0)

    if hasattr(model, "predict_proba"):
        prob = model.predict_proba(X)[:, 1][0]
    else:
        prob = model.predict(X)[0]

    return float(prob)
