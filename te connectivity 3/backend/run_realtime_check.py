from backend.data_access import build_realtime_model_vector, get_recent_window
from backend.config_limits import SAFE_LIMITS, ML_THRESHOLDS
from backend.ml_inference_v4 import predict_scrap_probability

def run(machine_id: str):
    """
    The 'Judge': Decides if machine is Safe (Green) or Critical (Red).
    Now supports intelligent column matching.
    """
    try:
        # 1. Get the latest data (1 row)
        df = get_recent_window(machine_id, minutes=60)
        
        if df.empty:
            return {
                "machine_id": machine_id,
                "timestamp": None,
                "ml_risk_probability": 0.0,
                "alert_level": "LOW",
                "decision_reason": "NO DATA",
                "violations": []
            }

        # Get the absolute last row (The "Now" point)
        latest_row = df.iloc[-1]
        timestamp = str(latest_row['event_timestamp']) if 'event_timestamp' in latest_row else str(latest_row.name)

        # 2. Check for Safety Violations
        violations = []
        
        # Iterate through every rule in config_limits.py
        for param, limits in SAFE_LIMITS.items():
            
            # --- INTELLIGENT MATCHING START ---
            # Try to find the correct column in the dataframe
            col_name = None
            
            # Case A: Exact Match (e.g. "Injection_pressure")
            if param in latest_row:
                col_name = param
            
            # Case B: Suffix Match (e.g. "Injection_pressure__last_5m")
            else:
                # Look for columns that start with the param name
                candidates = [c for c in latest_row.index if c.startswith(param + "__")]
                if candidates:
                    col_name = candidates[0] # Pick the first match
            
            # If we still can't find it, skip this rule
            if not col_name:
                continue
            # --- INTELLIGENT MATCHING END ---

            # Get the value
            current_val = float(latest_row[col_name])
            
            # Check Max Limit
            if "max" in limits and current_val > limits["max"]:
                violations.append({
                    "parameter": param, # Send the clean name to Frontend
                    "current": round(current_val, 2),
                    "limit": limits["max"],
                    "unit": limits.get("unit", ""),
                    "deviation": round(current_val - limits["max"], 2),
                    "direction": "above"
                })

            # Check Min Limit
            if "min" in limits and current_val < limits["min"]:
                violations.append({
                    "parameter": param,
                    "current": round(current_val, 2),
                    "limit": limits["min"],
                    "unit": limits.get("unit", ""),
                    "deviation": round(limits["min"] - current_val, 2),
                    "direction": "below"
                })

        # 3. Run ML inference using the trained v4 model
        machine_norm = str(latest_row.get("machine_id_normalized", "")).upper()
        sensor_input = build_realtime_model_vector(df, machine_norm=machine_norm, strict=True)
        ml_risk = float(predict_scrap_probability(sensor_input))
        
        if len(violations) > 0:
            status = "CRITICAL"
            reason = "SAFETY VIOLATION"
        elif ml_risk >= ML_THRESHOLDS["HIGH"]:
            status = "HIGH"
            reason = "AI RISK PREDICTION"
        elif ml_risk >= ML_THRESHOLDS["MEDIUM"]:
            status = "MEDIUM"
            reason = "AI RISK PREDICTION"
        elif ml_risk >= ML_THRESHOLDS["LOW"]:
            status = "LOW"
            reason = "AI WARNING"
        else:
            status = "NORMAL"
            reason = "OPTIMAL"

        return {
            "machine_id": machine_id,
            "timestamp": timestamp,
            "ml_risk_probability": ml_risk,
            "alert_level": status,
            "decision_reason": reason,
            "violations": violations,
        }

    except Exception as e:
        print(f"Checker Error: {e}")
        return {
            "machine_id": machine_id,
            "alert_level": "CRITICAL",
            "decision_reason": f"SYSTEM ERROR: {str(e)}",
            "violations": []
        }
