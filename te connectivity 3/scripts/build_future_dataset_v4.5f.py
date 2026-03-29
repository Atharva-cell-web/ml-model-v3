import pandas as pd

print("Loading dataset...")
df = pd.read_parquet("new_processed_data/cleaned_dataset_v4.parquet")

# Recover timestamp and is_scrap from the raw dataset since they were dropped 
# in the final stage of the v4 preprocessing pipeline
df_raw = pd.read_parquet("new_processed_data/FINAL_TRAINING_MASTER_V3.parquet")
df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], errors="coerce")
df_raw = df_raw.sort_values(by=["machine_id", "timestamp"]).reset_index(drop=True)
df_raw = df_raw.drop_duplicates().reset_index(drop=True)

df["timestamp"] = df_raw["timestamp"]
df["is_scrap"] = df_raw["is_scrap"]

df = df.sort_values("timestamp")

print("Creating multi-horizon targets...")
horizons = {
    "scrap_5m": 5,
    "scrap_10m": 10,
    "scrap_15m": 15,
    "scrap_20m": 20,
    "scrap_25m": 25,
    "scrap_30m": 30
}

for label, minutes in horizons.items():
    df[label] = (
        df["is_scrap"]
        .rolling(minutes, min_periods=1)
        .max()
        .shift(-minutes)
    ).fillna(0).astype(int)

print("Saving dataset...")
df.to_parquet(
    "new_processed_data/cleaned_dataset_v4.5f.parquet",
    index=False
)

print("Done.")