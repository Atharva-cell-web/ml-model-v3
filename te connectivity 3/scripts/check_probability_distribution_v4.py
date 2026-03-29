import pandas as pd
import joblib
import numpy as np

print("Loading dataset...")
df = pd.read_parquet("new_processed_data/cleaned_dataset_v4.parquet")

print("Loading model...")
model = joblib.load("models/scrap_risk_model_v4.pkl")

X = df.drop(columns=["future_scrap"])
y = df["future_scrap"]

print("Generating predictions...")

preds = model.predict(X)

print("\nProbability distribution:\n")

hist, bins = np.histogram(preds, bins=10)

for i in range(len(hist)):
    print(f"{bins[i]:.2f} - {bins[i+1]:.2f} : {hist[i]}")