"""
Simple forecasting for consumption
Uses linear regression if sufficient data, else returns limitation message.
Never fabricates predictions when insufficient data.
"""
from typing import List, Dict, Any
import numpy as np

MIN_HISTORY_FOR_FORECAST = 8

def forecast_consumption(historical_data: List[Dict[str, Any]], metric_key: str = "consumptionKwh", periods: int = 3) -> Dict[str, Any]:
    if not historical_data or len(historical_data) < MIN_HISTORY_FOR_FORECAST:
        return {
            "status": "insufficient_data",
            "message": "Insufficient historical data for reliable forecasting.",
            "detail": f"Provided {len(historical_data) if historical_data else 0} observations; requires at least {MIN_HISTORY_FOR_FORECAST} for trend forecasting.",
            "forecast": [],
            "method": "none",
            "historical_count": len(historical_data) if historical_data else 0
        }

    values = np.array([float(d.get(metric_key, 0)) for d in historical_data], dtype=float)
    X = np.arange(len(values)).reshape(-1, 1)
    y = values

    try:
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)
        future_X = np.arange(len(values), len(values)+periods).reshape(-1, 1)
        preds = model.predict(future_X)
        # Clip negative to 0
        preds = np.maximum(preds, 0)
        # Confidence interval simple: std *1.2
        std = float(np.std(values))
        trend = "increasing" if model.coef_[0] > 0 else "decreasing" if model.coef_[0] < 0 else "stable"
        return {
            "status": "success",
            "message": f"Forecast generated using linear regression trend ({trend}).",
            "method": "LinearRegression",
            "historical_count": len(historical_data),
            "trend_slope": float(model.coef_[0]),
            "intercept": float(model.intercept_),
            "r_squared": float(model.score(X, y)) if len(values)>2 else 0,
            "forecast": [
                {
                    "period": f"Month +{i+1}",
                    "predicted_value": float(round(pred, 2)),
                    "lower_bound": float(round(max(0, pred - std),2)),
                    "upper_bound": float(round(pred + std,2))
                } for i, pred in enumerate(preds)
            ],
            "assumptions": [
                "Simple linear trend; not weather or seasonality adjusted.",
                "Confidence bounds approximated as ±1 std of historical data.",
                "Not a certified forecast – decision support only."
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Forecasting failed: {str(e)}",
            "forecast": [],
            "method": "failed",
            "historical_count": len(historical_data)
        }

def forecast_energy(monthly_series: List[Dict[str, Any]], periods: int = 3):
    return forecast_consumption(monthly_series, metric_key="consumptionKwh", periods=periods)

def forecast_water(monthly_series: List[Dict[str, Any]], periods: int = 3):
    return forecast_consumption(monthly_series, metric_key="totalLitres", periods=periods)
