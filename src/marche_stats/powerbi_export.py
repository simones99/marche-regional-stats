"""Tables for the Power BI report: SARIMA forecast, its accuracy and reconciliation totals.

Power BI cleans the business register itself, in Power Query. These files carry what the
report cannot compute well (the SARIMA model validated in Python) and the totals that its
own cleaning must reproduce exactly.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from marche_stats import companies, timeseries

FOCUS_REGION = "ITI3"
HOLDOUT_COLUMNS = {
    "SARIMA": "holdout_sarima",
    "Naive (last value)": "holdout_naive",
    "Seasonal naive": "holdout_seasonal_naive",
}


def forecast_table(
    series: pd.Series, evaluation: timeseries.Evaluation, future: pd.DataFrame
) -> pd.DataFrame:
    """One row per month-end: actual values, holdout forecasts and the future forecast."""
    holdout = evaluation.holdout_forecast.drop(columns="actual").rename(columns=HOLDOUT_COLUMNS)
    frame = pd.DataFrame({"actual": series}).join(holdout, how="outer").join(future, how="outer")
    frame.index.name = "date"
    return frame.reset_index()


def accuracy_table(evaluation: timeseries.Evaluation) -> pd.DataFrame:
    """Out-of-sample errors of SARIMA and the naive baselines on the holdout months."""
    table = evaluation.errors.rename(columns={"MAE": "mae", "MAPE (%)": "mape_pct"})
    table.index.name = "method"
    table = table.reset_index()
    order, seasonal = evaluation.order, evaluation.seasonal_order
    is_sarima = table["method"] == "SARIMA"
    table["specification"] = ""
    table.loc[is_sarima, "specification"] = f"SARIMA{order}{seasonal[:3]}[{seasonal[3]}]"
    table["interval_coverage_pct"] = None
    table.loc[is_sarima, "interval_coverage_pct"] = 100 * evaluation.interval_coverage
    table["interval_coverage_pct"] = table["interval_coverage_pct"].astype(float)
    table["holdout_start"] = evaluation.holdout_forecast.index.min()
    table["holdout_end"] = evaluation.holdout_forecast.index.max()
    return table


def reconciliation_table(wide: pd.DataFrame, series: pd.Series) -> pd.DataFrame:
    """Checkpoints the Power Query cleaning must match: region and provinces."""
    provinces = companies.province_totals(companies.to_long(wide))
    provinces = provinces[provinces["date"] <= series.index[-1]]
    december = provinces[provinces["date"].dt.month == 12]
    first_dec, last_dec = december["date"].min(), december["date"].max()

    rows = [
        ("Region, first month", FOCUS_REGION, series.index[0], series.iloc[0]),
        ("Region, last modelled month", FOCUS_REGION, series.index[-1], series.iloc[-1]),
    ]
    for row in december[december["date"].isin([first_dec, last_dec])].itertuples():
        rows.append((f"{row.nuts3}, {row.date:%b %Y}", row.nuts3, row.date, row.active_companies))
    table = pd.DataFrame(rows, columns=["checkpoint", "geo", "date", "active_companies"])
    table["active_companies"] = table["active_companies"].astype(int)
    return table


def build(companies_csv: Path, out_dir: Path, holdout: int = 24) -> dict[str, Path]:
    """Fit the model and write forecast.csv, forecast_accuracy.csv and reconciliation.csv."""
    wide = companies.read_wide(companies_csv)
    series = companies.modelling_series(wide)
    evaluation = timeseries.evaluate(series, holdout=holdout)
    future = timeseries.forecast(series, evaluation.order, evaluation.seasonal_order, steps=12)
    tables = {
        "forecast.csv": forecast_table(series, evaluation, future),
        "forecast_accuracy.csv": accuracy_table(evaluation),
        "reconciliation.csv": reconciliation_table(wide, series),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, frame in tables.items():
        path = out_dir / name
        frame.to_csv(
            path, index=False, date_format="%Y-%m-%d", float_format="%.4f", lineterminator="\n"
        )
        paths[name] = path
    return paths
