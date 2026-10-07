"""Eurostat NUTS 3 demography for the Marche provinces and GISCO boundaries."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import requests

SDMX_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"
GISCO_NUTS3_URL = (
    "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/"
    "NUTS_RG_03M_2024_4326_LEVL_3.geojson"
)
TIMEOUT_SECONDS = 180

# Marche NUTS 3 regions, the region (NUTS 2) and Italy.
GEOS = ("ITI31", "ITI32", "ITI33", "ITI34", "ITI35", "ITI3", "IT")
NUTS3_NAMES = {
    "ITI31": "Pesaro e Urbino",
    "ITI32": "Ancona",
    "ITI33": "Macerata",
    "ITI34": "Ascoli Piceno",
    "ITI35": "Fermo",
}

# File name -> (dataset, SDMX series key without geo). Keys follow each dataset's DSD order.
DATASETS = {
    "population.csv": ("demo_r_pjanaggr3", "A.NR.T.TOTAL+Y_GE65"),
    "deaths.csv": ("demo_r_magec3", "A.T.NR.TOTAL"),
}


def dataset_url(code: str, key: str, start_period: int) -> str:
    return (
        f"{SDMX_BASE}/data/{code}/{key}.{'+'.join(GEOS)}?format=SDMX-CSV&startPeriod={start_period}"
    )


def download(raw_dir: Path, start_period: int = 2009) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for filename, (code, key) in DATASETS.items():
        response = requests.get(dataset_url(code, key, start_period), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        (raw_dir / filename).write_bytes(response.content)

    response = requests.get(GISCO_NUTS3_URL, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    features = [f for f in response.json()["features"] if f["properties"]["NUTS_ID"] in NUTS3_NAMES]
    (raw_dir / "marche_nuts3.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8"
    )


def read_sdmx_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(io.StringIO(path.read_text(encoding="utf-8")))
    return frame.rename(columns={"TIME_PERIOD": "year", "OBS_VALUE": "value", "OBS_FLAG": "flag"})[
        ["geo", "age", "year", "value", "flag"]
    ]


def demography(raw_dir: Path) -> pd.DataFrame:
    """One row per geo and year: population, share aged 65+, deaths, crude death rate."""
    population = read_sdmx_csv(raw_dir / "population.csv")
    deaths = read_sdmx_csv(raw_dir / "deaths.csv")

    wide = population.pivot_table(index=["geo", "year"], columns="age", values="value")
    wide = wide.rename(columns={"TOTAL": "population", "Y_GE65": "population_65_plus"})
    wide["share_65_plus"] = 100 * wide["population_65_plus"] / wide["population"]

    deaths_by_year = deaths.set_index(["geo", "year"])["value"].rename("deaths")
    out = wide.join(deaths_by_year, how="left").reset_index()
    # Crude death rate per 1,000 residents, using population on 1 January of the same year.
    out["crude_death_rate"] = 1000 * out["deaths"] / out["population"]
    return out.sort_values(["geo", "year"]).reset_index(drop=True)
