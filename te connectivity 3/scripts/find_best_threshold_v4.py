import pandas as pd
import numpy as np
import joblib
import json
from sklearn.metrics import f1_score

print("Loading dataset...")

df = pd.read_parquet("new_processed_data/cleaned_dataset_v4.parquet")

# same split used in validation
split_index = int(len(df) * 0.8)

train_df = df.iloc[:split_index]
val_df = df.iloc[split_index:]

X_val = val_df.drop(columns=["future_scrap"])
y_val = val_df["future_scrap"]

print("Loading model...")

model = joblib.load("models/scrap_risk_model_v4.pkl")

print("Generating predictions...")

preds = model.predict(X_val)

print("Searching best threshold...")

best_f1 = 0
best_threshold = 0

for t in np.arange(0.05, 0.60, 0.01):

    pred_labels = (preds > t).astype(int)
    f1 = f1_score(y_val, pred_labels)

    if f1 > best_f1:
        best_f1 = f1
        best_threshold = t

print("\nBest threshold:", best_threshold)
print("Best F1 score:", best_f1)

# -------------------------
# Save threshold to metrics
# -------------------------

metrics_file = "metrics/training_metrics_v4.json"

with open(metrics_file, "r") as f:
    metrics = json.load(f)

metrics["best_threshold"] = float(best_threshold)
metrics["best_f1"] = float(best_f1)

with open(metrics_file, "w") as f:
    json.dump(metrics, f, indent=4)

print("\nThreshold saved to training_metrics_v4.json")