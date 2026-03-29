import argparse
import json
import logging
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ManufacturingPreprocessor:
    """
    Clean, reproducible pipeline for preprocessing manufacturing data v4.
    Can be used for training, validation, or inference.
    """

    def __init__(self, cycle_look_ahead=10):
        self.cycle_look_ahead = cycle_look_ahead
        self.logs = []
        self.dead_sensors_removed = []
        self.high_missing_sensors_removed = []
        self.feature_columns = None

    def _log_step(self, step_name, details):
        log_entry = {
            "step": step_name,
            "details": details,
        }
        self.logs.append(log_entry)
        logging.info(f"Step '{step_name}': {details}")

    def load_data(self, parquet_path):
        """Step 1 - Raw Data Loading"""
        logging.info(f"Loading data from {parquet_path}")
        df = pd.read_parquet(parquet_path)

        # Ensure timestamps are parsed correctly
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        # Sort data by machine_id and timestamp
        df = df.sort_values(by=["machine_id", "timestamp"]).reset_index(drop=True)

        self._log_step(
            "Raw Data Loading",
            f"Loaded {len(df)} rows from {parquet_path}. Sorted by machine_id and timestamp.",
        )
        return df

    def clean_data(self, df):
        """Step 2 - Data Cleaning"""
        rows_before = len(df)
        df = df.drop_duplicates()
        rows_after = len(df)
        dups_removed = rows_before - rows_after

        # Identify sensors
        exclude_cols = ["machine_id", "timestamp", "is_scrap", "future_scrap"]
        sensor_cols = [c for c in df.columns if c not in exclude_cols]

        # Convert sensor values to numeric
        for col in sensor_cols:
            if df[col].dtype == object or str(df[col].dtype) == "string":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Handle missing values: fill with forward fill then backward fill per machine
        df[sensor_cols] = df.groupby("machine_id")[sensor_cols].transform(lambda x: x.ffill().bfill())

        # Remove sensors with >50% missing data
        missing_pct = df[sensor_cols].isnull().mean()
        high_missing = missing_pct[missing_pct > 0.5].index.tolist()
        df = df.drop(columns=high_missing)
        self.high_missing_sensors_removed = high_missing
        sensor_cols = [c for c in sensor_cols if c not in high_missing]

        # Remove dead sensors (constant columns)
        std_devs = df[sensor_cols].std()
        dead_sensors = std_devs[std_devs == 0].index.tolist()
        df = df.drop(columns=dead_sensors)
        self.dead_sensors_removed = dead_sensors

        self._log_step(
            "Data Cleaning",
            f"Dropped {dups_removed} duplicates. Removed high-missing sensors: {high_missing}. Removed dead (constant) sensors: {dead_sensors}.",
        )
        return df

    def encode_machine_id(self, df):
        """Step 3 - Machine Context Encoding"""
        if "machine_id" not in df.columns:
            self._log_step("Machine Context Encoding", "No 'machine_id' column found, skipping encoding.")
            return df

        df["machine_id_encoded"] = df["machine_id"].astype("category").cat.codes
        self._log_step("Machine Context Encoding", "Created 'machine_id_encoded' from machine_id category codes.")
        return df

    def filter_sensors(self, df):
        """Step 4 - Sensor Filtering"""
        sensors_to_remove = ["Cyl_tmp_z2", "Cyl_tmp_z6", "Cyl_tmp_z7"]
        present_sensors = [c for c in sensors_to_remove if c in df.columns]
        df = df.drop(columns=present_sensors)
        self._log_step("Sensor Filtering", f"Removed explicitly requested dead sensors: {present_sensors}")
        return df

    def engineer_features(self, df):
        """Step 5 - Feature Engineering"""
        exclude_cols = ["machine_id", "timestamp", "is_scrap", "future_scrap"]
        numeric_cols = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]

        logging.info("Engineering features... this may take some time.")

        # Ensure sorted
        df = df.sort_values(["machine_id", "timestamp"]).reset_index(drop=True)

        grouped = df.groupby("machine_id")[numeric_cols]

        # 1. Rolling features
        rolling_5 = grouped.rolling(window=5, min_periods=1)
        r_mean = rolling_5.mean().reset_index(level=0, drop=True)
        r_std = rolling_5.std().reset_index(level=0, drop=True).fillna(0)
        r_min = rolling_5.min().reset_index(level=0, drop=True)
        r_max = rolling_5.max().reset_index(level=0, drop=True)

        for c in numeric_cols:
            df[f"{c}_rolling_mean_5"] = r_mean[c]
            df[f"{c}_rolling_std_5"] = r_std[c]
            df[f"{c}_rolling_min_5"] = r_min[c]
            df[f"{c}_rolling_max_5"] = r_max[c]

        # 2. Lag features
        lag_1 = grouped.shift(1)
        lag_3 = grouped.shift(3)
        lag_5 = grouped.shift(5)
        for c in numeric_cols:
            df[f"{c}_lag_1"] = lag_1[c]
            df[f"{c}_lag_3"] = lag_3[c]
            df[f"{c}_lag_5"] = lag_5[c]

        # 3. Rate of change features
        roc_5 = grouped.pct_change(periods=5)
        roc_30 = grouped.pct_change(periods=30)
        for c in numeric_cols:
            df[f"{c}_rate_of_change_5"] = roc_5[c]
            df[f"{c}_rate_of_change_30"] = roc_30[c]

        # Handle newly created NaNs
        new_cols = [c for c in df.columns if any(suffix in c for suffix in ["_rolling_", "_lag_", "_rate_of_change_"])]
        # For pct_change containing inf, replace with NaN
        df[new_cols] = df[new_cols].replace([np.inf, -np.inf], np.nan)
        # Fill remaining NaNs with bfill/ffill per machine, then robust 0 fallback
        df[new_cols] = df.groupby("machine_id")[new_cols].transform(lambda x: x.bfill().ffill()).fillna(0)

        self._log_step(
            "Feature Engineering",
            f"Generated rolling (5), lags (1,3,5) and ROC (5,30) features for {len(numeric_cols)} numeric base columns.",
        )
        return df

    def create_labels(self, df):
        """Step 6 - Target Label Creation"""
        if "is_scrap" not in df.columns:
            self._log_step("Target Label Creation", "No 'is_scrap' column found, skipping label creation.")
            return df

        # future_scrap = 1 if scrap occurs within next N cycles
        def check_future_scrap(group):
            group = group.sort_values("timestamp")
            group["future_scrap"] = (
                group["is_scrap"][::-1]
                .rolling(window=self.cycle_look_ahead, min_periods=1)
                .max()[::-1]
            )
            return group

        df = df.groupby("machine_id", group_keys=False).apply(check_future_scrap)
        df["future_scrap"] = df["future_scrap"].fillna(0).astype(int)

        pos_ratio = df["future_scrap"].mean() * 100
        self._log_step(
            "Target Label Creation",
            f"Created 'future_scrap' label predicting scrap within next {self.cycle_look_ahead} cycles. Positive class ratio: {pos_ratio:.2f}%",
        )
        return df

    def select_features(self, df):
        """Step 7 - Feature Selection"""
        exclude_cols = ["machine_id", "timestamp", "is_scrap", "future_scrap"]

        # Feature columns are everything else
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        # Sort to ensure stable order
        feature_cols = sorted(feature_cols)

        self.feature_columns = feature_cols
        self._log_step("Feature Selection", f"Selected {len(feature_cols)} features for modeling.")
        return df

    def drop_unused_columns(self, df):
        """Step 8 - Drop Non-Model Columns"""
        drop_cols = ["machine_id", "timestamp", "is_scrap"]
        present_cols = [c for c in drop_cols if c in df.columns]
        df = df.drop(columns=present_cols)
        self._log_step("Drop Non-Model Columns", f"Dropped columns: {present_cols}")
        return df

    def export_pipeline(self, df, output_dir="."):
        """Step 9 - Feature Schema Export"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        out_parquet = output_dir / "cleaned_dataset_v4.parquet"
        df.to_parquet(out_parquet, index=False)
        self._log_step("Feature Schema Export", f"Saved cleaned dataset to {out_parquet}")

        out_pkl = output_dir / "model_features_v4.pkl"
        with open(out_pkl, "wb") as f:
            pickle.dump(self.feature_columns, f)
        self._log_step("Feature Schema Export", f"Saved ordered feature list to {out_pkl}")

        out_log = output_dir / "preprocessing_log_v4.json"
        with open(out_log, "w") as f:
            json.dump(self.logs, f, indent=4)
        self._log_step("Feature Schema Export", f"Saved preprocessing log to {out_log}")

        logging.info(f"Pipeline execution complete! Outputs saved to {output_dir}")

    def run_pipeline(self, parquet_path, output_dir="."):
        """Run all steps sequentially"""
        df = self.load_data(parquet_path)
        df = self.clean_data(df)
        df = self.encode_machine_id(df)
        df = self.filter_sensors(df)
        df = self.engineer_features(df)
        df = self.create_labels(df)
        df = self.select_features(df)
        df = self.drop_unused_columns(df)
        self.export_pipeline(df, output_dir)
        return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Manufacturing Data Preprocessing Pipeline v4")
    parser.add_argument(
        "--input",
        type=str,
        default="D:/teit04/te connectivity 3/new_processed_data/FINAL_TRAINING_MASTER_V3.parquet",
        help="Path to raw parquet file",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="D:/teit04/te connectivity 3/new_processed_data",
        help="Output directory",
    )
    args = parser.parse_args()

    # Check if input file exists
    if not Path(args.input).exists():
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)

    preprocessor = ManufacturingPreprocessor(cycle_look_ahead=10)
    _ = preprocessor.run_pipeline(args.input, output_dir=args.outdir)
