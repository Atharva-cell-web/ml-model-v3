import pandas as pd
import joblib

print("Loading dataset...")

df = pd.read_parquet("new_processed_data/cleaned_dataset_v4.parquet")

# remove target column
features = [c for c in df.columns if c not in ["future_scrap"]]

print("Number of features:", len(features))

joblib.dump(features, "models/model_features_v4.pkl")

print("Saved to models/model_features_v4.pkl")