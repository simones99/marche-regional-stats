"""Seasonal decomposition and SARIMA forecasting of monthly company counts.

Model choice is made on a training period only. The last `holdout` months are kept
aside and used once, to compare SARIMA with two naive baselines out of sample.
"""

from __future__ import annotations

import itertools
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.statespace.sarimax import SARIMAX

SEASON = 12


@dataclass(frozen=True)
class Evaluation:
    order: tuple[int, int, int]
    seasonal_order: tuple[int, int, int, int]
    aic: float
    errors: pd.DataFrame  # one row per method: MAE, MAPE
    interval_coverage: float  # share of test months inside SARIMA's 95 % interval
    holdout_forecast: pd.DataFrame  # actual and each method's forecast


def seasonal_strength(series: pd.Series) -> float:
    """Strength of seasonality in [0, 1] (Wang, Smith and Hyndman, 2006), from STL."""
    stl = STL(series, period=SEASON, robust=True).fit()
    detrended = stl.seasonal + stl.resid
    return float(max(0.0, 1 - np.var(stl.resid) / np.var(detrended)))


def decompose(series: pd.Series) -> pd.DataFrame:
    stl = STL(series, period=SEASON, robust=True).fit()
    return pd.DataFrame(
        {"observed": series, "trend": stl.trend, "seasonal": stl.seasonal, "resid": stl.resid}
    )


def _fit(series: pd.Series, order, seasonal_order):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return SARIMAX(
            series,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)


def select_order(train: pd.Series) -> tuple[tuple, tuple, float]:
    """Small grid search by AIC: d=1, p,q in 0..2, seasonal P,Q in 0..1, D in 0..1."""
    best = None
    for p, q, seasonal_p, seasonal_d, seasonal_q in itertools.product(
        range(3), range(3), range(2), range(2), range(2)
    ):
        order, seasonal_order = (p, 1, q), (seasonal_p, seasonal_d, seasonal_q, SEASON)
        try:
            aic = _fit(train, order, seasonal_order).aic
        except (ValueError, np.linalg.LinAlgError):
            continue
        if np.isfinite(aic) and (best is None or aic < best[2]):
            best = (order, seasonal_order, aic)
    if best is None:
        raise RuntimeError("no SARIMA specification could be fitted")
    return best


def _errors(actual: pd.Series, forecast: pd.Series) -> dict[str, float]:
    error = actual - forecast
    return {
        "MAE": float(error.abs().mean()),
        "MAPE (%)": float(100 * (error.abs() / actual).mean()),
    }


def evaluate(series: pd.Series, holdout: int = 24) -> Evaluation:
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    order, seasonal_order, aic = select_order(train)
    prediction = _fit(train, order, seasonal_order).get_forecast(holdout)
    sarima = prediction.predicted_mean
    sarima.index = test.index
    interval = prediction.conf_int(alpha=0.05).set_axis(test.index)
    inside = (test >= interval.iloc[:, 0]) & (test <= interval.iloc[:, 1])

    naive = pd.Series(train.iloc[-1], index=test.index)
    # Seasonal naive: same month of the last training year, repeated.
    last_year = train.iloc[-SEASON:].to_numpy()
    seasonal_naive = pd.Series(np.resize(last_year, holdout), index=test.index)

    forecasts = {"SARIMA": sarima, "Naive (last value)": naive, "Seasonal naive": seasonal_naive}
    errors = pd.DataFrame({name: _errors(test, f) for name, f in forecasts.items()}).T
    holdout_forecast = pd.DataFrame({"actual": test, **forecasts})
    return Evaluation(order, seasonal_order, aic, errors, float(inside.mean()), holdout_forecast)


def forecast(series: pd.Series, order, seasonal_order, steps: int = 12) -> pd.DataFrame:
    """Refit on the full series and forecast with a 95 % interval."""
    result = _fit(series, order, seasonal_order).get_forecast(steps)
    interval = result.conf_int(alpha=0.05)
    return pd.DataFrame(
        {
            "forecast": result.predicted_mean,
            "lower_95": interval.iloc[:, 0],
            "upper_95": interval.iloc[:, 1],
        }
    )
