import joblib
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = PROJECT_ROOT / "models" / "scrap_risk_model_v4.pkl"
FEATURES_PATH = PROJECT_ROOT / "models" / "model_features_v4.pkl"

print("[v4] Loading model:", MODEL_PATH)

model = joblib.load(MODEL_PATH)
model_features = joblib.load(FEATURES_PATH)

print("[v4] Feature count:", len(model_features))


def predict_scrap_probability(sensor_row: dict):

    row = {}

    for f in model_features:
        row[f] = sensor_row.get(f, 0.0)

    X = pd.DataFrame([row])[model_features].fillna(0)

    if hasattr(model, "predict_proba"):
        prob = model.predict_proba(X)[:, 1][0]
    else:
        prob = model.predict(X)[0]

    return float(prob)