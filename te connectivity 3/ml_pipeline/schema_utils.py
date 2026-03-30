from __future__ import annotations

import logging

import pandas as pd

REQUIRED_COLUMNS = ["machine_id", "timestamp"]
RECOMMENDED_SENSOR_COLUMNS = ["Cycle_time", "Injection_pressure", "Switch_pressure"]


def detect_format(df):
    """Detect whether input is long or already wide."""
    columns = set(df.columns)
    if {"variable_name", "value"}.issubset(columns):
        return "long"
    return "wide"


def pivot_long_to_wide(df):
    """Convert long data (variable_name/value rows) into wide machine-cycle rows."""
    required_long = ["timestamp", "machine_id", "variable_name", "value"]
    missing = [c for c in required_long if c not in df.columns]
    if missing:
        raise ValueError(f"Long-format pivot failed. Missing columns: {missing}")

    work_df = df.copy()
    work_df["value"] = pd.to_numeric(work_df["value"], errors="coerce")

    # Keep only label-style passthrough columns that the v4 pipeline may use.
    passthrough_cols = [c for c in ["is_scrap", "future_scrap"] if c in work_df.columns]

    value_wide = work_df.pivot_table(
        index=["timestamp", "machine_id"],
        columns="variable_name",
        values="value",
        aggfunc="last",
    )

    if passthrough_cols:
        passthrough = (
            work_df.sort_values(["machine_id", "timestamp"])
            .drop_duplicates(subset=["machine_id", "timestamp"], keep="last")
            .set_index(["timestamp", "machine_id"])[passthrough_cols]
        )
        wide = passthrough.join(value_wide, how="outer")
    else:
        wide = value_wide

    wide = wide.reset_index()
    wide.columns.name = None
    return wide


def sanitize_rows(df):
    """Drop invalid rows and duplicate machine/timestamp keys before v4 processing."""
    df = df.copy()

    if "timestamp" in df.columns:
        ts_before = len(df)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        invalid_ts = int(df["timestamp"].isna().sum())
        if invalid_ts:
            logging.warning("Dropping %s rows with invalid timestamp values.", invalid_ts)
        df = df.dropna(subset=["timestamp"])
        logging.info("Timestamp parsing complete: %s -> %s rows", ts_before, len(df))

    if "machine_id" in df.columns:
        missing_machine = int(df["machine_id"].isna().sum())
        if missing_machine:
            logging.warning("Dropping %s rows with missing machine_id.", missing_machine)
        df = df.dropna(subset=["machine_id"])

    if {"machine_id", "timestamp"}.issubset(df.columns):
        dup_count = int(df.duplicated(subset=["machine_id", "timestamp"]).sum())
        if dup_count:
            logging.warning("Dropping %s duplicate machine_id/timestamp rows (keeping last).", dup_count)
            df = df.drop_duplicates(subset=["machine_id", "timestamp"], keep="last")

    return df.reset_index(drop=True)


def validate_schema(df, required_columns=None, recommended_columns=None):
    """Validate core schema and warn for missing recommended sensors."""
    required_columns = required_columns or REQUIRED_COLUMNS
    recommended_columns = recommended_columns or RECOMMENDED_SENSOR_COLUMNS

    missing_required = [c for c in required_columns if c not in df.columns]
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")

    missing_recommended = [c for c in recommended_columns if c not in df.columns]
    if missing_recommended:
        logging.warning("Recommended sensors missing (pipeline will continue): %s", missing_recommended)

    return {
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
    }


