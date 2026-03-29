import numpy as np


def _map_feature_to_cause(feature_name: str) -> str:
    if "Cycle_time" in feature_name:
        return "Cycle Time Instability"
    if "Injection_pressure" in feature_name:
        return "Injection Pressure Instability"
    if "Switch_pressure" in feature_name:
        return "Switch Pressure Variation"
    if "Cyl_tmp" in feature_name:
        return "Cylinder Temperature Instability"
    if "Peak_pressure" in feature_name:
        return "Peak Pressure Position Drift"
    return "Other Sensor Variation"


def compute_root_causes(model, feature_row, feature_names):
    """
    Compute root causes from LightGBM feature contributions (SHAP-style).
    Returns top 3 causes sorted by absolute contribution impact.
    """

    contrib = model.predict(feature_row, pred_contrib=True)
    contrib = np.asarray(contrib)

    if contrib.ndim == 2:
        contrib = contrib[0]
    elif contrib.ndim > 2:
        contrib = contrib.reshape(-1)

    if contrib.size == 0:
        return []

    # Last contribution is model bias term for LightGBM.
    feature_contrib = contrib[:-1]

    causes = {}
    for name, value in zip(feature_names, feature_contrib):
        value = float(value)
        if abs(value) < 1e-4:
            continue
        cause_key = _map_feature_to_cause(name)
        causes[cause_key] = causes.get(cause_key, 0.0) + value

    sorted_causes = sorted(causes.items(), key=lambda item: abs(item[1]), reverse=True)
    return sorted_causes[:3]
