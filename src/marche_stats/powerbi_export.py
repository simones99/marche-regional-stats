"""Tables for the Power BI report: forecast, accuracy, reconciliation, seasonality, map.

Power BI cleans the business register itself, in Power Query. These files carry what the
report cannot compute well (the SARIMA model validated in Python) and the totals that its
own cleaning must reproduce exactly.
"""

from __future__ import annotations

import json
import math
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


MAP_BOX = 400


def _polygons(geometry: dict) -> list:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    return geometry["coordinates"]


def _ring_centroid(ring: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Area and centroid of a closed ring (shoelace formula)."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    if area == 0:
        return 0.0, ring[0][0], ring[0][1]
    return abs(area), cx / (6 * area), cy / (6 * area)


def province_shapes_table(geojson_path: Path, box: int = MAP_BOX) -> pd.DataFrame:
    """SVG path and label point of each NUTS 3 province, in a box x box square.

    Equirectangular projection scaled by the cosine of the mean latitude, north up. The
    label point is the centroid of the province's largest ring. The report's Map SVG
    measure draws these paths, so the map needs no map service.
    """
    features = json.loads(geojson_path.read_text(encoding="utf-8"))["features"]
    rings = {
        f["properties"]["NUTS_ID"]: [ring for poly in _polygons(f["geometry"]) for ring in poly]
        for f in features
    }
    points = [p for geo_rings in rings.values() for ring in geo_rings for p in ring]
    lon0, lon1 = min(p[0] for p in points), max(p[0] for p in points)
    lat0, lat1 = min(p[1] for p in points), max(p[1] for p in points)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    scale = box / max((lon1 - lon0) * k, lat1 - lat0)

    rows = []
    for geo in sorted(rings):
        projected = [
            [((p[0] - lon0) * k * scale, (lat1 - p[1]) * scale) for p in ring]
            for ring in rings[geo]
        ]
        path = "".join(
            "M" + " ".join(f"{x:.0f},{y:.0f}" for x, y in ring) + "Z" for ring in projected
        )
        _, label_x, label_y = max((_ring_centroid(ring) for ring in projected), key=lambda c: c[0])
        rows.append((geo, path, round(label_x), round(label_y)))
    return pd.DataFrame(rows, columns=["geo", "path", "label_x", "label_y"])


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
