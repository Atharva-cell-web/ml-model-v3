import pandas as pd

print("Loading feature importance file...")

fi = pd.read_csv("features/feature_importance_v4.csv")

print("\nTop 10 Most Important Features:\n")

top_features = fi.sort_values("importance_gain", ascending=False).head(10)

print(top_features)