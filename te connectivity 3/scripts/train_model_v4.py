import json
from pathlib import Path
import gc

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

VERSION = "v4-machine-context"
RANDOM_STATE = 42


def main():
    np.random.seed(RANDOM_STATE)

    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "new_processed_data" / "cleaned_dataset_v4.parquet"
    model_path = project_root / "models" / "scrap_risk_model_v4.pkl"
    metrics_path = project_root / "metrics" / "training_metrics_v4.json"
    feature_importance_path = project_root / "features" / "feature_importance_v4.csv"

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    feature_importance_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(data_path)
    if "future_scrap" not in df.columns:
        raise ValueError("Expected label column 'future_scrap' in cleaned_dataset_v4.parquet")
    if "machine_id_encoded" not in df.columns:
        raise ValueError("Expected feature 'machine_id_encoded' in cleaned_dataset_v4.parquet")

    feature_drop = [c for c in ["future_scrap", "machine_id", "timestamp", "is_scrap"] if c in df.columns]
    feature_cols = [c for c in df.columns if c not in feature_drop]

    row_count = int(len(df))
    dataset_shape = df.shape
    scrap_ratio = float(df["future_scrap"].mean())
    y = df["future_scrap"].astype(np.uint8).to_numpy()
    indices = np.arange(len(df))

    idx_train, idx_test = train_test_split(
        indices,
        test_size=0.2,
        stratify=y,
        random_state=RANDOM_STATE,
    )
    X_train = df.iloc[idx_train][feature_cols].to_numpy(dtype=np.float32, na_value=0.0)
    X_test = df.iloc[idx_test][feature_cols].to_numpy(dtype=np.float32, na_value=0.0)
    y_train = y[idx_train]
    y_test = y[idx_test]
    del df
    gc.collect()

    params = {
        "objective": "binary",
        "metric": "auc",
        "learning_rate": 0.03,
        "num_leaves": 64,
        "max_depth": 8,
        "min_data_in_leaf": 80,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "scale_pos_weight": 25,
        "seed": RANDOM_STATE,
        "feature_fraction_seed": RANDOM_STATE,
        "bagging_seed": RANDOM_STATE,
        "data_random_seed": RANDOM_STATE,
        "verbose": -1,
    }

    train_data = lgb.Dataset(X_train, label=y_train, feature_name=feature_cols)
    valid_data = lgb.Dataset(X_test, label=y_test, feature_name=feature_cols, reference=train_data)

    model = lgb.train(
        params=params,
        train_set=train_data,
        num_boost_round=500,
        valid_sets=[valid_data],
        valid_names=["valid"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, first_metric_only=True),
            lgb.log_evaluation(period=50),
        ],
    )

    y_proba = model.predict(X_test, num_iteration=model.best_iteration)
    y_pred = (y_proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    joblib.dump(model, model_path)

    importance_df = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance_gain": model.feature_importance(importance_type="gain"),
            "importance_split": model.feature_importance(importance_type="split"),
        }
    ).sort_values("importance_gain", ascending=False)
    importance_df.to_csv(feature_importance_path, index=False)

    metrics = {
        "version": VERSION,
        "auc": float(auc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "feature_count": int(len(feature_cols)),
        "row_count": row_count,
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Dataset shape: {dataset_shape}")
    print(f"Scrap ratio (future_scrap=1): {scrap_ratio:.6f} ({scrap_ratio * 100:.2f}%)")
    print("Model metrics:")
    print(f"  AUC: {auc:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall: {recall:.4f}")
    print(f"  F1: {f1:.4f}")
    print("Top 20 feature importances (gain):")
    print(importance_df.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
