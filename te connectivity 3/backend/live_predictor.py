"""
Live predictor module for real-time scrap-risk scoring.

Uses the global v4 model inference helper and buffers incoming raw sensor
readings per machine_id.

Includes an "offline / frozen" detector: if the machine's sensor readings
are identical to the previous reading OR Cycle_time <= 0.1, the model is
bypassed and risk_score is returned as 0.0.
"""

from collections import deque
from typing import Any, Dict, Optional
from backend.ml_inference_v4 import predict_scrap_probability

# ── Model & feature list ────────────────────────────────────────────

# ── Per-machine sensor buffer ───────────────────────────────────────
live_buffer: Dict[str, Dict[str, float]] = {}

import pandas as pd
from backend.data_access import build_realtime_model_vector

# ── Per-machine state tracker (last 35 snapshots for rolling/lags) ──
_state_history: Dict[str, deque] = {}
_STATE_HISTORY_SIZE = 35

def _is_frozen_or_offline(machine_id: str, current_state: Dict[str, float]) -> bool:
    """
    Return True if the machine appears offline or frozen:
      1. Cycle_time <= 0.1  (machine not cycling)
      2. Current sensor snapshot is identical to the previous one (frozen PLC)
    """
    cycle_time = current_state.get("Cycle_time", None)
    if cycle_time is not None and cycle_time <= 0.1:
        return True

    if machine_id not in _state_history:
        _state_history[machine_id] = deque(maxlen=_STATE_HISTORY_SIZE)

    history = _state_history[machine_id]
    if len(history) > 0:
        prev = history[-1]
        shared_keys = set(current_state.keys()) & set(prev.keys())
        if shared_keys and all(current_state[k] == prev[k] for k in shared_keys):
            return True

    # Record current snapshot into history
    history.append(dict(current_state))
    return False

def predict_from_raw(machine_id: str, raw_data: Dict[str, Any]) -> dict:
    """
    Accept one incoming sensor reading, buffer it, and return a live risk score.
    """
    var_name = raw_data.get("variable_name")
    val = raw_data.get("value")

    if machine_id not in live_buffer:
        live_buffer[machine_id] = {}

    if var_name is not None and val is not None:
        live_buffer[machine_id][var_name] = float(val)

    current_state = live_buffer[machine_id]

    # ── Frozen / offline check ──────────────────────────────────
    if _is_frozen_or_offline(machine_id, current_state):
        return {
            "machine_id": machine_id,
            "risk_score": 0.0,
            "sensors_buffered": len(current_state),
            "status": "offline",
        }

    # ── Build feature row and score ─────────────────────────────
    # Convert history buffer into a DataFrame to compute rolling/lag features mathematically
    history_df = pd.DataFrame(list(_state_history[machine_id]))
    
    # Calculate the exact features the Kaggle model expects (includes all rolling means/stds)
    full_feature_vector = build_realtime_model_vector(history_df, machine_norm=machine_id)
    
    # Predict using the fully expanded vector
    risk_score = float(predict_scrap_probability(full_feature_vector))

    return {
        "machine_id": machine_id,
        "risk_score": round(risk_score, 4),
        "sensors_buffered": len(current_state),
        "status": "success",
    }


# ── Helper endpoints ────────────────────────────────────────────────

def get_buffer_status(machine_id: Optional[str] = None) -> dict:
    """Return buffer sizes for one or all machines."""
    if machine_id:
        return {
            "machine_id": machine_id,
            "buffer_size": len(live_buffer.get(machine_id, {})),
        }
    return {
        "machines": list(live_buffer.keys()),
        "sizes": {k: len(v) for k, v in live_buffer.items()},
    }


def clear_buffer(machine_id: Optional[str] = None) -> None:
    """Clear the buffer for one or all machines."""
    if machine_id and machine_id in live_buffer:
        live_buffer[machine_id].clear()
    elif not machine_id:
        live_buffer.clear()
