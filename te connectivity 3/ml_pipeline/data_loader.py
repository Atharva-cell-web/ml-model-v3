from pathlib import Path

import pandas as pd


def load_raw_data(file_path):
    """Load raw input data from csv/parquet/excel into a pandas DataFrame."""
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        # Keep pipeline resilient to malformed rows in CSV inputs.
        return pd.read_csv(file_path, on_bad_lines="skip")
    if suffix == ".parquet":
        return pd.read_parquet(file_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)

    raise ValueError(f"Unsupported file type: {suffix}. Expected one of: .csv, .parquet, .xlsx, .xls")

