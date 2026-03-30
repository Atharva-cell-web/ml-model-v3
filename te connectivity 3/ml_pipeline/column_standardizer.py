import re


_ALIAS_PRIORITY = {
    "machine_id": ["machine_id", "machine_definition", "machine_def", "machine_id_normalized"],
    "timestamp": ["timestamp", "event_timestamp", "time_stamp", "datetime", "date_time"],
    "variable_name": ["variable_name", "variable", "sensor_name", "parameter_name", "tag_name"],
    "value": ["value", "value_numeric", "reading", "sensor_value", "measurement"],
}


def _clean_column_name(name):
    text = str(name).strip()
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"[^0-9A-Za-z_]", "", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def standardize_columns(df):
    """Normalize column names and map known aliases to canonical names."""
    cleaned_cols = [_clean_column_name(col) for col in df.columns]
    df = df.copy()
    df.columns = cleaned_cols

    lower_to_actual = {col.lower(): col for col in df.columns}
    rename_map = {}

    for canonical_name, alias_candidates in _ALIAS_PRIORITY.items():
        if canonical_name in df.columns:
            continue
        for alias in alias_candidates:
            alias_actual = lower_to_actual.get(alias.lower())
            if alias_actual and alias_actual not in rename_map:
                rename_map[alias_actual] = canonical_name
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    return df

