"""
Anomaly Detection for consumption patterns
Uses Isolation Forest if sufficient historical data, else statistical fallback.
If insufficient data, returns clear limitation message per spec.
"""
from typing import List, Dict, Any
import numpy as np

MIN_HISTORY_FOR_ML = 12  # need 12 points for reliable ML per spec guidance (or 6 minimal)
MIN_HISTORY_FOR_STAT = 6

def detect_anomalies(historical_data: List[Dict[str, Any]], metric_key: str = "consumptionKwh") -> Dict[str, Any]:
    """
    historical_data: list of dicts with metric_key and month
    Returns dict with either anomalies or insufficient message
    """
    if not historical_data or len(historical_data) < MIN_HISTORY_FOR_STAT:
        return {
            "status": "insufficient_data",
            "message": "Insufficient historical data for reliable anomaly detection.",
            "detail": f"Provided {len(historical_data) if historical_data else 0} observations; requires at least {MIN_HISTORY_FOR_STAT} for statistical detection and {MIN_HISTORY_FOR_ML} for ML-based detection.",
            "anomalies": [],
            "method": "none",
            "historical_count": len(historical_data) if historical_data else 0
        }

    values = np.array([float(d.get(metric_key, 0)) for d in historical_data], dtype=float)

    # Try Isolation Forest if enough data
    if len(historical_data) >= MIN_HISTORY_FOR_ML:
        try:
            from sklearn.ensemble import IsolationForest
            X = values.reshape(-1, 1)
            clf = IsolationForest(contamination=0.15, random_state=42)
            preds = clf.fit_predict(X)
            scores = clf.decision_function(X)
            anomalies = []
            for i, (pred, score) in enumerate(zip(preds, scores)):
                if pred == -1:
                    anomalies.append({
                        "index": i,
                        "month": historical_data[i].get("month", f"Point {i}"),
                        "value": float(values[i]),
                        "anomaly_score": float(score),
                        "deviation": float(values[i] - np.mean(values))
                    })
            return {
                "status": "success",
                "message": f"Detected {len(anomalies)} anomalies using Isolation Forest (explainable).",
                "method": "IsolationForest",
                "contamination": 0.15,
                "historical_count": len(historical_data),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "anomalies": anomalies,
                "all_scores": [float(s) for s in scores]
            }
        except Exception as e:
            # fallback to statistical
            pass

    # Statistical anomaly detection (Z-score >2)
    mean = float(np.mean(values))
    std = float(np.std(values)) if np.std(values) != 0 else 1.0
    anomalies = []
    for i, v in enumerate(values):
        z = (v - mean) / std if std else 0
        if abs(z) > 2.0:
            anomalies.append({
                "index": i,
                "month": historical_data[i].get("month", f"Point {i}"),
                "value": float(v),
                "z_score": float(z),
                "mean": mean,
                "std": std
            })
    method = "statistical_zscore"
    msg = f"Detected {len(anomalies)} anomalies using statistical Z-score threshold 2.0." if anomalies else "No anomalies detected (statistical Z-score). All points within 2 std deviations."
    return {
        "status": "success" if anomalies or len(historical_data)>=MIN_HISTORY_FOR_STAT else "insufficient_data",
        "message": msg,
        "method": method,
        "threshold": 2.0,
        "historical_count": len(historical_data),
        "mean": mean,
        "std": std,
        "anomalies": anomalies
    }

def detect_energy_anomalies(monthly_series: List[Dict[str, Any]]):
    return detect_anomalies(monthly_series, metric_key="consumptionKwh")

def detect_water_anomalies(monthly_series: List[Dict[str, Any]]):
    return detect_anomalies(monthly_series, metric_key="totalLitres")
