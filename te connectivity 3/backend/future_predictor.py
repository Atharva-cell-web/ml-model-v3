from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models" / "future_models"

MODEL_FILES = {
    "5m": "model_scrap_5m.pkl",
    "10m": "model_scrap_10m.pkl",
    "15m": "model_scrap_15m.pkl",
    "20m": "model_scrap_20m.pkl",
    "25m": "model_scrap_25m.pkl",
    "30m": "model_scrap_30m.pkl",
}


@lru_cache(maxsize=1)
def _load_future_models():
    models = {}
    for horizon, filename in MODEL_FILES.items():
        model_path = MODEL_DIR / filename
        if model_path.exists():
            models[horizon] = joblib.load(model_path)
    return models


def predict_future_risk(feature_row: dict, feature_columns: list):
    if not feature_columns:
        return {}

    feature_columns = list(feature_columns)
    X = pd.DataFrame([feature_row]).reindex(columns=feature_columns, fill_value=0).fillna(0)
    models = _load_future_models()

    results = {}
    for horizon, model in models.items():
        prob = model.predict_proba(X)[0, 1]
        results[horizon] = float(prob)

    return results
