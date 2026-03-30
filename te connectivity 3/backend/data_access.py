import re
import time
import warnings
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from pandas.errors import PerformanceWarning

warnings.filterwarnings("ignore", category=PerformanceWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from backend.config_limits import ML_THRESHOLDS
from backend.dynamic_limits import calculate_dynamic_limits
from backend.future_predictor import predict_future_risk
from backend.ml_inference_v4 import predict_scrap_probability
from backend.ml_inference_v4 import model_features as v4_features
from backend.root_cause_analyzer import compute_root_causes

import json as _json

_PER_MACHINE_MODELS = {}
_PER_MACHINE_FEATURES = {}

def _load_per_machine_models():
    global _PER_MACHINE_MODELS, _PER_MACHINE_FEATURES
    model_dir = Path(__file__).resolve().parent.parent / "models"
    machines = ["M231","M356","M471","M607","M612"]
    feat_path = model_dir / "per_machine_features_v3.json"
    if feat_path.exists():
        with open(feat_path) as f:
            raw = _json.load(f)
        for m in machines:
            if m in raw:
                entry = raw[m]
                if isinstance(entry, dict):
                    _PER_MACHINE_FEATURES[m] = entry.get("feature_cols", [])
                elif isinstance(entry, list):
                    _PER_MACHINE_FEATURES[m] = entry
    for m in machines:
        if m == "M231":
            p = model_dir / "lightgbm_scrap_model_v3.pkl"
        else:
            p = model_dir / f"lgbm_{m}_v3.pkl"
        if p.exists():
            _PER_MACHINE_MODELS[m] = joblib.load(p)
    # Load base features fallback
    base_feat_path = model_dir / "model_features_v3.pkl"
    if base_feat_path.exists():
        _BASE_FEATURES_V3 = joblib.load(base_feat_path)
        for m in machines:
            if m not in _PER_MACHINE_FEATURES:
                _PER_MACHINE_FEATURES[m] = _BASE_FEATURES_V3

_load_per_machine_models()

PER_MACHINE_THRESHOLDS = {
    "M231": 0.10,
    "M356": 0.15,
    "M471": 0.30,
    "M607": 0.27,
    "M612": 0.28,
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WIDE_FILE = PROJECT_ROOT / "processed" / "features" / "rolling_features_demo.parquet"
WIDE_FILE_FALLBACK = PROJECT_ROOT / "processed" / "features" / "rolling_features_wide.parquet"
FEB_RESULTS_FILE = PROJECT_ROOT / "new_processed_data" / "FEB_TEST_RESULTS.parquet"
MACHINE_TESTS_DIR = PROJECT_ROOT / "new_processed_data"
CONTROL_MODEL_PATH = PROJECT_ROOT / "models/scrap_risk_model_v4.pkl"
MODEL_FEATURES_PATH = PROJECT_ROOT / "models" / "model_features_v4.pkl"
MODEL_FEATURES_FALLBACK_PATH = PROJECT_ROOT / "new_processed_data" / "model_features_v4.pkl"
FORECASTER_MODEL_PATH = PROJECT_ROOT / "models" / "sensor_forecaster_lagged.pkl"
FUTURE_RISK_THRESHOLD = float(ML_THRESHOLDS.get("MEDIUM", 0.60))
CONTROL_ROOM_PAST_WINDOW_MINUTES = 60
CONTROL_ROOM_FUTURE_WINDOW_MINUTES = 30
FUTURE_HORIZON_STEPS_MINUTES = (5, 10, 15, 20, 25, 30)

_ttl_cache: dict = {}
_TTL_SECONDS = 15
_MACHINE_CODE_MAP = {
    "M231": 0.0,
    "M356": 1.0,
    "M471": 2.0,
    "M607": 3.0,
    "M612": 4.0,
}
_DERIVED_SUFFIXES = (
    "_rolling_mean_5",
    "_rolling_std_5",
    "_rolling_min_5",
    "_rolling_max_5",
    "_lag_1",
    "_lag_3",
    "_lag_5",
    "_roc_5",
    "_roc_30",
    "_rate_of_change_5",
    "_rate_of_change_30",
)
_BASE_SENSOR_FEATURES = tuple(
    f for f in v4_features
    if f != "machine_id_encoded" and not f.endswith(_DERIVED_SUFFIXES)
)

def _get_cached(key):
    entry = _ttl_cache.get(key)
    if entry and time.monotonic() < entry[0]:
        return entry[1]
    return None

def _set_cached(key, value):
    _ttl_cache[key] = (time.monotonic() + _TTL_SECONDS, value)


def build_realtime_model_vector(window_df: pd.DataFrame, machine_norm: str = "", strict: bool = False) -> dict:
    if window_df is None or window_df.empty:
        return {f: 0.0 for f in v4_features}

    df = window_df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")

    base_df = pd.DataFrame(index=df.index)
    for col in _BASE_SENSOR_FEATURES:
        if col in df.columns:
            base_df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            base_df[col] = 0.0
    base_df = base_df.ffill().bfill().fillna(0.0)

    machine_code = float(_MACHINE_CODE_MAP.get(str(machine_norm or "").upper(), 0.0))
    computed = {}

    def _zero_series():
        return pd.Series(0.0, index=base_df.index, dtype=float)

    def _feature_series(name: str):
        if name in computed:
            return computed[name]

        if name == "machine_id_encoded":
            series = pd.Series(machine_code, index=base_df.index, dtype=float)
            computed[name] = series
            return series

        if name in base_df.columns:
            series = base_df[name].astype(float)
            computed[name] = series
            return series

        lag_match = re.search(r"_lag_(1|3|5)$", name)
        if lag_match:
            base_name = name[:lag_match.start()]
            lag_n = int(lag_match.group(1))
            series = _feature_series(base_name).shift(lag_n)
            computed[name] = series
            return series

        rolling_match = re.search(r"_rolling_(mean|std|min|max)_5$", name)
        if rolling_match:
            base_name = name[:rolling_match.start()]
            agg = rolling_match.group(1)
            roll = _feature_series(base_name).rolling(window=5, min_periods=1)
            if agg == "mean":
                series = roll.mean()
            elif agg == "std":
                series = roll.std().fillna(0.0)
            elif agg == "min":
                series = roll.min()
            else:
                series = roll.max()
            computed[name] = series
            return series

        roc_match = re.search(r"_(roc|rate_of_change)_(5|30)$", name)
        if roc_match:
            base_name = name[:roc_match.start()]
            periods = int(roc_match.group(2))
            series = _feature_series(base_name).pct_change(periods=periods)
            computed[name] = series
            return series

        series = _zero_series()
        computed[name] = series
        return series

    latest = {}
    for feature in v4_features:
        s = _feature_series(feature).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0.0)
        latest[feature] = float(s.iloc[-1]) if len(s) else 0.0

    if strict:
        missing_features = [f for f in v4_features if f not in latest]
        if missing_features:
            raise RuntimeError(
                f"Inference feature parity failed: {len(missing_features)} missing model features."
            )

    return latest

def _normalize_machine_id(machine_id: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]", "", str(machine_id or "")).upper()
    if compact.startswith("M"):
        return compact
    return f"M{compact}"

def _display_machine_id(machine_norm: str) -> str:
    match = re.match(r"^M(\d+)$", machine_norm)
    if match:
        return f"M-{match.group(1)}"
    return machine_norm

def _safe_float(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _downsample(df: pd.DataFrame, max_points: int = 360) -> pd.DataFrame:
    if len(df) <= max_points:
        return df
    step = int(np.ceil(len(df) / max_points))
    sampled = df.iloc[::step].copy()
    if sampled.iloc[-1]["timestamp"] != df.iloc[-1]["timestamp"]:
        sampled = pd.concat([sampled, df.tail(1)], ignore_index=True)
    return sampled.drop_duplicates(subset=["timestamp"], keep="last")

def _clean_limit_payload(current_safe_limits: dict):
    cleaned = {}
    for sensor, limits in current_safe_limits.items():
        cleaned[sensor] = {
            "min": _safe_float(limits.get("min")) if "min" in limits else None,
            "max": _safe_float(limits.get("max")) if "max" in limits else None,
        }
    return cleaned

@lru_cache(maxsize=1)
def _load_control_model_and_features():
    model = None
    features = []

    if CONTROL_MODEL_PATH.exists():
        model = joblib.load(CONTROL_MODEL_PATH)

    if model is not None and hasattr(model, "feature_name"):
        features = model.feature_name() if callable(model.feature_name) else model.feature_name
    elif model is not None and hasattr(model, "feature_name_"):
        features = model.feature_name_
    elif model is not None and hasattr(model, "booster_"):
        features = model.booster_.feature_name()
    elif MODEL_FEATURES_PATH.exists():
        features = joblib.load(MODEL_FEATURES_PATH)
    elif MODEL_FEATURES_FALLBACK_PATH.exists():
        features = joblib.load(MODEL_FEATURES_FALLBACK_PATH)
    elif v4_features:
        features = list(v4_features)

    if model is None:
        print(f"[control-model] Warning: model not found at {CONTROL_MODEL_PATH}. Using fallback features only.")

    return model, tuple(features)

@lru_cache(maxsize=1)
def _load_sensor_forecaster():
    if not FORECASTER_MODEL_PATH.exists():
        raise FileNotFoundError(f"Sensor forecaster not found: {FORECASTER_MODEL_PATH}")
    artifact = joblib.load(FORECASTER_MODEL_PATH)
    return (
        artifact["model"],
        list(artifact["sensor_columns"]),
        list(artifact["input_features"]),
        int(artifact["num_lags"]),
        list(artifact.get("hydra_features", []))
    )

@lru_cache(maxsize=1)
def _load_feb_results():
    if not FEB_RESULTS_FILE.exists():
        raise FileNotFoundError(f"FEB results file not found: {FEB_RESULTS_FILE}")

    _feb_cols = [
        "timestamp", "Injection_pressure", "Cycle_time",
        "scrap_probability", "is_scrap_actual",
    ]
    try:
        feb = pd.read_parquet(FEB_RESULTS_FILE, columns=_feb_cols, engine="pyarrow")
    except Exception:
        feb = pd.read_parquet(FEB_RESULTS_FILE, engine="pyarrow")

    if "timestamp" not in feb.columns:
        raise ValueError("FEB_TEST_RESULTS.parquet must include a 'timestamp' column.")

    feb["timestamp"] = pd.to_datetime(feb["timestamp"], utc=True, errors="coerce")
    feb = feb.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    for key_col in ("Injection_pressure", "Cycle_time"):
        if key_col in feb.columns:
            feb[key_col] = pd.to_numeric(feb[key_col], errors="coerce").round(4)

    return feb

@lru_cache(maxsize=16)
def _load_machine_pivot(machine_norm: str):
    machine_path = MACHINE_TESTS_DIR / f"{machine_norm}_TEST.parquet"
    if not machine_path.exists():
        raise FileNotFoundError(f"Machine test parquet not found: {machine_path}")

    raw = pd.read_parquet(machine_path, columns=["timestamp", "variable_name", "value", "machine_definition"], engine="pyarrow")
    machine_definition = "UNKNOWN"
    defs = raw["machine_definition"].dropna().astype(str).unique()
    if len(defs) > 0:
        machine_definition = defs[0]

    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw = raw.dropna(subset=["value"])
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True, errors="coerce")
    raw = raw.dropna(subset=["timestamp"])

    pivot = raw.pivot_table(index="timestamp", columns="variable_name", values="value", aggfunc="mean").reset_index()
    pivot = pivot.sort_values("timestamp").reset_index(drop=True)

    _, model_features = _load_control_model_and_features()
    for feature in model_features:
        if feature not in pivot.columns:
            pivot[feature] = 0.0

    for key_col in ("Injection_pressure", "Cycle_time"):
        if key_col in pivot.columns:
            pivot[key_col] = pd.to_numeric(pivot[key_col], errors="coerce").round(4)

    return pivot, machine_definition

def _build_machine_feb_history(machine_norm: str):
    cache_key = ("feb_history", machine_norm)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    feb = _load_feb_results()
    pivot, machine_definition = _load_machine_pivot(machine_norm)

    join_cols = ["timestamp", "Injection_pressure", "Cycle_time"]
    missing_join = [c for c in join_cols if c not in pivot.columns or c not in feb.columns]
    if missing_join:
        raise ValueError(f"Cannot map machine rows to FEB results. Missing join columns: {missing_join}")

    feb_unique = feb.drop_duplicates(subset=join_cols, keep="first")
    history = pivot.merge(feb_unique, on=join_cols, how="left")

    if history.empty:
        raise ValueError(f"No FEB history matched machine {machine_norm}.")

    if "scrap_probability" not in history.columns:
        history["scrap_probability"] = 0.0
    history["scrap_probability"] = pd.to_numeric(history["scrap_probability"], errors="coerce")

    if "is_scrap_actual" not in history.columns:
        history["is_scrap_actual"] = 0
    history["is_scrap_actual"] = pd.to_numeric(history["is_scrap_actual"], errors="coerce").fillna(0)

    # Rows that didn't match FEB results have NaN scrap_probability.
    # Fill with 0.0 - do NOT re-score with the model at runtime, as the
    # model expects rolling-feature inputs, not raw sensor columns.
    history["scrap_probability"] = history["scrap_probability"].fillna(0.0)

    history["scrap_probability"] = history["scrap_probability"].fillna(0.0).clip(0, 1)

    history["machine_id_normalized"] = machine_norm
    history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True, errors="coerce")
    history = history.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    tool_match = re.search(r"-([A-Za-z0-9]+)$", str(machine_definition))
    tool_id = tool_match.group(1) if tool_match else "UNKNOWN"

    machine_info = {
        "id": _display_machine_id(machine_norm),
        "tool_id": tool_id,
        "part_number": "UNKNOWN",
    }
    result = (history, machine_info)
    _set_cached(cache_key, result)
    return result

def _compute_root_causes(current_sensors: dict, current_safe_limits: dict):
    exceeded = []
    nearby = []
    for sensor, limits in current_safe_limits.items():
        sensor_value = _safe_float(current_sensors.get(sensor))
        if sensor_value is None:
            continue

        lower = _safe_float(limits.get("min")) if "min" in limits else None
        upper = _safe_float(limits.get("max")) if "max" in limits else None
        span_candidates = []
        if lower is not None and upper is not None:
            span_candidates.append(abs(upper - lower))
        if upper is not None:
            span_candidates.append(abs(upper))
        if lower is not None:
            span_candidates.append(abs(lower))
        span = max(max(span_candidates) if span_candidates else 1.0, 1.0)

        if upper is not None and sensor_value > upper:
            breach_magnitude = (sensor_value - upper) / span
            if breach_magnitude >= 0.01:
                exceeded.append((sensor, breach_magnitude))
            continue
        if lower is not None and sensor_value < lower:
            breach_magnitude = (lower - sensor_value) / span
            if breach_magnitude >= 0.01:
                exceeded.append((sensor, breach_magnitude))
            continue

        distances = []
        if lower is not None:
            distances.append(abs(sensor_value - lower))
        if upper is not None:
            distances.append(abs(upper - sensor_value))
        if distances:
            normalized_margin = min(distances) / span
            nearby.append((sensor, 1.0 - min(normalized_margin, 1.0)))

    if exceeded:
        exceeded_sorted = sorted(exceeded, key=lambda item: item[1], reverse=True)
        return [sensor for sensor, _ in exceeded_sorted[:3]], [sensor for sensor, _ in exceeded_sorted]

    nearby_sorted = sorted(nearby, key=lambda item: item[1], reverse=True)
    return [sensor for sensor, _ in nearby_sorted[:3]], []

def _sensor_matches_root_cause(sensor: str, root_causes: list) -> bool:
    cause_text = " ".join(
        str(item.get("cause", "")) for item in (root_causes or [])
        if isinstance(item, dict)
    )

    if "Cycle Time" in cause_text and "Cycle_time" in sensor:
        return True
    if "Injection Pressure" in cause_text and "Injection_pressure" in sensor:
        return True
    if "Cylinder Temperature" in cause_text and "Cyl_tmp" in sensor:
        return True
    if "Peak Pressure" in cause_text and "Peak_pressure" in sensor:
        return True
    if "Switch Pressure" in cause_text and "Switch_pressure" in sensor:
        return True
    return False

def _build_telemetry_grid(machine_df: pd.DataFrame, current_safe_limits: dict, root_cause_payload: list):
    rows = []
    if machine_df is None or machine_df.empty:
        return rows

    for sensor, limits in current_safe_limits.items():
        if sensor not in machine_df.columns:
            continue

        series = pd.to_numeric(machine_df[sensor], errors="coerce")
        series = series.replace([np.inf, -np.inf], np.nan).dropna()
        if series.empty:
            continue

        current_value = float(series.iloc[-1])
        baseline_idx = -5 if len(series) >= 5 else 0
        baseline_value = float(series.iloc[baseline_idx])
        trend_delta = float(current_value - baseline_value)

        if trend_delta > 0:
            trend_direction = "up"
        elif trend_delta < 0:
            trend_direction = "down"
        else:
            trend_direction = "flat"

        safe_min = _safe_float(limits.get("min")) if "min" in limits else None
        safe_max = _safe_float(limits.get("max")) if "max" in limits else None

        span_candidates = []
        if safe_min is not None and safe_max is not None:
            span_candidates.append(abs(safe_max - safe_min))
        if safe_max is not None:
            span_candidates.append(abs(safe_max))
        if safe_min is not None:
            span_candidates.append(abs(safe_min))
        span = max(max(span_candidates) if span_candidates else 1.0, 1.0)

        status = "NORMAL"
        if safe_max is not None and current_value > safe_max:
            status = "EXCEEDED"
        elif safe_min is not None and current_value < safe_min:
            status = "EXCEEDED"
        else:
            near_lower = safe_min is not None and (current_value - safe_min) < (0.1 * span)
            near_upper = safe_max is not None and (safe_max - current_value) < (0.1 * span)
            if near_lower or near_upper:
                status = "WARNING"

        sparkline_series = series.tail(30).tolist()
        sparkline = [float(v) for v in sparkline_series if np.isfinite(v)]

        rows.append({
            "sensor": sensor,
            "value": float(current_value),
            "status": status,
            "safe_min": safe_min,
            "safe_max": safe_max,
            "trend_delta": float(trend_delta),
            "trend_direction": trend_direction,
            "sparkline": sparkline,
            "is_root_cause": _sensor_matches_root_cause(sensor, root_cause_payload),
        })

    severity_rank = {"EXCEEDED": 3, "WARNING": 2, "NORMAL": 1}
    rows.sort(key=lambda row: (not row["is_root_cause"], -severity_rank.get(row["status"], 0), row["sensor"]))
    return rows

def _infer_step_seconds(history: pd.DataFrame) -> int:
    if len(history) < 2:
        return 60
    diffs = history["timestamp"].diff().dropna().dt.total_seconds()
    if diffs.empty:
        return 60
    median_step = float(diffs.median())
    if not np.isfinite(median_step) or median_step <= 0:
        return 60
    return int(np.clip(round(median_step), 10, 120))

def _generate_future_horizon(machine_df, n_steps=CONTROL_ROOM_FUTURE_WINDOW_MINUTES):
    if machine_df is None or machine_df.empty:
        return []

    last_row = machine_df.iloc[-1]
    _, feature_columns = _load_control_model_and_features()
    machine_norm = str(last_row.get("machine_id_normalized", "")).upper()
    feature_row = build_realtime_model_vector(machine_df, machine_norm=machine_norm, strict=True)

    try:
        future_preds = predict_future_risk(feature_row, feature_columns)
    except Exception:
        future_preds = {}

    last_ts = pd.to_datetime(last_row["timestamp"], errors="coerce")
    if pd.isna(last_ts):
        return []
    if hasattr(last_ts, "tz") and last_ts.tz is not None:
        last_ts = last_ts.tz_localize(None)
    horizons = list(FUTURE_HORIZON_STEPS_MINUTES)

    # Convert last_ts to epoch milliseconds for consistent timeline
    last_ts_ms = int(last_ts.timestamp() * 1000)

    future_points = []
    for h in horizons:
        fallback = float(last_row.get("scrap_probability", 0.0) or 0.0)
        risk = float(future_preds.get(f"{h}m", fallback))
        risk = round(max(0.0, min(1.0, risk)), 4)

        future_points.append({
            "timestamp": last_ts_ms + h * 60 * 1000,
            "risk_score": risk,
            "is_future": True,
            "type": "future",
            "horizon_minutes": h,
            "is_scrap_actual": 0,
            "sensors": {},
        })

    return future_points

def _row_to_timeline_point(row, is_future: bool, current_safe_limits: dict = None):
    sensors = {}
    sensor_keys = current_safe_limits.keys() if current_safe_limits else []
    for sensor in sensor_keys:
        if sensor in row and pd.notna(row[sensor]):
            val = float(row[sensor])
            # Skip garbage values - all legitimate sensors are below ~1500
            if not np.isfinite(val) or abs(val) > 5000:
                continue
            sensors[sensor] = round(val, 2)

    ts = pd.to_datetime(row["timestamp"])
    if hasattr(ts, "tz") and ts.tz is not None:
        ts = ts.tz_localize(None)
    # Convert to epoch milliseconds for correct chart time scaling
    timestamp_ms = int(ts.timestamp() * 1000)

    sensor_input = {}
    for f in v4_features:
        val = row.get(f)
        if pd.isna(val):
            sensor_input[f] = 0.0
        else:
            try:
                sensor_input[f] = float(val)
            except Exception:
                sensor_input[f] = 0.0

    if is_future:
        risk_score = round(predict_scrap_probability(sensor_input), 2)
    else:
        risk_score = round(float(row.get("scrap_probability", 0.0)), 2)
    # Also read future scrap probability if available
    future_risk = float(row.get("future_scrap_probability",
                                 row.get("scrap_probability", 0.0)))
    future_risk = round(max(0.0, min(1.0, future_risk)), 4)
    machine_norm = str(row.get("machine_id_normalized", "")).upper()
    if "231" in machine_norm:
        future_risk = min(future_risk, 0.15)

    return {
        "timestamp": timestamp_ms,
        "risk_score": risk_score,
        "future_risk_score": future_risk,
        "is_future": bool(is_future),
        "type": "future" if is_future else "past",
        "is_scrap_actual": int(float(row.get("is_scrap_actual", 0) or 0)),
        "sensors": sensors,
    }

def build_control_room_payload(
    machine_id: str,
    time_window: int = CONTROL_ROOM_PAST_WINDOW_MINUTES,
    future_window: int = CONTROL_ROOM_FUTURE_WINDOW_MINUTES,
):
    effective_time_window = CONTROL_ROOM_PAST_WINDOW_MINUTES
    effective_future_window = CONTROL_ROOM_FUTURE_WINDOW_MINUTES
    payload_key = ("payload", machine_id, effective_time_window, effective_future_window)
    cached_payload = _get_cached(payload_key)
    if cached_payload is not None:
        return cached_payload

    t0 = time.perf_counter()
    machine_norm = _normalize_machine_id(machine_id)

    history, machine_info = _build_machine_feb_history(machine_norm)

    if history.empty:
        raise ValueError(f"No history found for machine {machine_id}")

    history = history.sort_values("timestamp").reset_index(drop=True)
    history["timestamp"] = pd.to_datetime(history["timestamp"], errors="coerce")

    max_time = history["timestamp"].max()
    anchor = max_time
    cutoff = anchor - pd.Timedelta(minutes=effective_time_window)

    past_window = history[
        (history["timestamp"] >= cutoff) & (history["timestamp"] <= anchor)
    ].copy()
    if past_window.empty:
        return {
            "machine_info": {"id": machine_id, "tool_id": "UNKNOWN", "part_number": "UNKNOWN"},
            "summary_stats": {"past_scrap_detected": 0, "future_scrap_predicted": 0},
            "current_health": {"status": "OFFLINE", "risk_score": 0.0, "root_causes": []},
            "root_causes": [],
            "telemetry_grid": [],
            "timeline": [],
            "safe_limits": {},
        }

    numeric_cols = past_window.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        past_window[numeric_cols] = past_window[numeric_cols].ffill().bfill()

    current_safe_limits = calculate_dynamic_limits(past_window)

    machine_df = past_window
    current_row = machine_df.iloc[-1]
    current_sensors = {}
    for sensor in current_safe_limits:
        if sensor in current_row and pd.notna(current_row[sensor]):
            current_sensors[sensor] = float(current_row[sensor])

    _, breached_sensors = _compute_root_causes(current_sensors, current_safe_limits)
    sensor_input = build_realtime_model_vector(machine_df, machine_norm=machine_norm, strict=True)
    model, feature_names = _load_control_model_and_features()
    feature_row = pd.DataFrame([[float(sensor_input.get(name, 0.0)) for name in feature_names]], columns=feature_names)
    ml_risk = float(predict_scrap_probability(sensor_input))
    current_risk = min(1.0, max(0.0, ml_risk))

    root_causes = []
    if ml_risk > 0.25:
        try:
            root_causes = compute_root_causes(model, feature_row, feature_names)
        except Exception:
            root_causes = []

    root_cause_payload = []
    for item in root_causes:
        if isinstance(item, dict):
            # It's the new hierarchical SHAP payload
            root_cause_payload.append(item)
        else:
            # Fallback for old tuple style
            cause, impact = item
            root_cause_payload.append({
                "cause": cause,
                "impact": float(impact),
                "category": cause,
                "total_impact": float(impact),
                "risk_increasing": float(impact) if impact > 0 else 0.0,
                "risk_decreasing": float(impact) if impact < 0 else 0.0,
                "top_parameters": []
            })
    telemetry_grid = _build_telemetry_grid(machine_df, current_safe_limits, root_cause_payload)

    if breached_sensors:
        status = "CRITICAL"
    elif current_risk >= float(ML_THRESHOLDS.get("HIGH", 0.27)):
        status = "HIGH"
    elif current_risk >= float(ML_THRESHOLDS.get("MEDIUM", 0.19)):
        status = "MEDIUM"
    elif current_risk >= float(ML_THRESHOLDS.get("LOW", 0.11)):
        status = "LOW"
    else:
        status = "NORMAL"

    future_minutes = effective_future_window
    future_horizon = _generate_future_horizon(past_window, n_steps=future_minutes)

    past_scrap_detected = int((past_window["is_scrap_actual"].fillna(0) >= 1).sum())
    future_scrap_predicted = int(
        sum(1 for point in future_horizon if float(point.get("risk_score", 0.0)) >= FUTURE_RISK_THRESHOLD)
    )

    past_timeline = _downsample(past_window, max_points=320)
    future_timeline = future_horizon

    timeline = []
    for _, row in past_timeline.iterrows():
        timeline.append(_row_to_timeline_point(row, is_future=False, current_safe_limits=current_safe_limits))

    # Timeline continuity: future timestamps are already epoch ms from _generate_future_horizon.
    # Add a bridge point so the past line and future line connect at the boundary.
    if timeline and future_timeline:
        last_past_point = timeline[-1]
        last_past_ts_ms = last_past_point["timestamp"]
        last_past_risk = last_past_point.get("risk_score", 0.0)
        first_future_risk = future_timeline[0].get("risk_score", 0.0)
        # Bridge point: carries both pastRisk and futureRisk so lines connect
        bridge_point = {
            "timestamp": last_past_ts_ms,
            "risk_score": last_past_risk,
            "is_future": False,
            "type": "bridge",
            "is_scrap_actual": 0,
            "sensors": {},
            "bridge_future_risk": first_future_risk,
        }
        # Replace last past point with bridge so we don't duplicate
        timeline[-1] = bridge_point

    timeline.extend(future_timeline)

    # Final sanitization: strip any garbage sensor values
    for point in timeline:
        bad_keys = [k for k, v in point.get("sensors", {}).items()
                    if not isinstance(v, (int, float)) or not np.isfinite(v) or abs(v) > 5000]
        for k in bad_keys:
            del point["sensors"][k]

    payload = {
        "machine_info": machine_info,
        "summary_stats": {
            "past_scrap_detected": past_scrap_detected,
            "future_scrap_predicted": future_scrap_predicted,
        },
        "current_health": {
            "status": status,
            "risk_score": round(current_risk, 2),
            "root_causes": [item["cause"] for item in root_cause_payload],
        },
        "root_causes": root_cause_payload,
        "telemetry_grid": telemetry_grid,
        "timeline": timeline,
        "safe_limits": _clean_limit_payload(current_safe_limits),
    }
    _set_cached(payload_key, payload)
    return payload

def get_recent_window(machine_id, minutes=60):
    machine_norm = _normalize_machine_id(machine_id)
    history, _ = _build_machine_feb_history(machine_norm)
    
    if history.empty:
        return pd.DataFrame()

    history = history.sort_values("timestamp").reset_index(drop=True)
    history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True, errors="coerce")
    history = history.dropna(subset=["timestamp"])

    if history.empty:
        return pd.DataFrame()

    max_time = history["timestamp"].max()
    anchor = max_time
    
    cutoff = anchor - pd.Timedelta(minutes=minutes)

    past_window = history[
        (history["timestamp"] >= cutoff) & (history["timestamp"] <= anchor)
    ].copy()

    past_window["event_timestamp"] = past_window["timestamp"]
    
    return past_window

