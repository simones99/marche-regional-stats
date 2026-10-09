"""Eurostat data for the Marche provinces and regional comparisons, and GISCO boundaries."""

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

# v0.2: the Marche against its neighbouring regions, Italy and the EU27.
FOCUS_GEO = "ITI3"
COMPARISON_GEOS = ("ITI3", "ITH5", "ITI1", "ITI2", "ITI4", "ITF1", "IT", "EU27_2020")
REGIONS = COMPARISON_GEOS[:6]
GEO_NAMES = {
    "ITI3": "Marche",
    "ITH5": "Emilia-Romagna",
    "ITI1": "Toscana",
    "ITI2": "Umbria",
    "ITI4": "Lazio",
    "ITF1": "Abruzzo",
    "IT": "Italy",
    "EU27_2020": "European Union (27)",
}
REGIONAL_START = 2013

# File name -> (dataset, SDMX series key without geo). Keys follow each dataset's DSD order;
# an empty position selects every code of that dimension.
REGIONAL_DATASETS = {
    "regional_deaths.csv": ("demo_r_magec", "A.NR.T+M+F."),
    "regional_population.csv": ("demo_r_pjangroup", "A.NR.T+M+F."),
    "death_rate_benchmark.csv": ("hlth_cd_asdr2", "A.RT.T+M+F.TOTAL.A-R_V-Y"),
    "enrolment.csv": ("educ_uoe_enra11", "A.NR..T+M+F"),
    "early_leavers.csv": ("edat_lfse_16", "A.PC.T+M+F.Y18-24"),
    "tertiary_attainment.csv": ("edat_lfse_04", "A.T+M+F.ED5-8.Y25-34.PC"),
    "early_childhood.csv": ("educ_uoe_enra22", "A.PC"),
    "gdp.csv": ("nama_10r_2gdp", "A.PPS_HAB_EU27_2020"),
    "unemployment.csv": ("lfst_r_lfu3rt", "A.TOTAL.T+M+F.Y15-74.PC"),
}

# (file name, geo, year) combinations missing at the source, checked on 2026-10-09.
KNOWN_GAPS = {
    ("regional_deaths.csv", "EU27_2020", 2024),
    ("enrolment.csv", "EU27_2020", 2017),
}

METADATA_COLUMNS = ("DATAFLOW", "LAST UPDATE", "freq", "CONF_STATUS")


class DownloadError(RuntimeError):
    """A request to Eurostat or GISCO failed."""


class CoverageError(ValueError):
    """A downloaded dataset lacks a geography or year that the analysis needs."""


def dataset_url(code: str, key: str, start_period: int, geos: tuple[str, ...] = GEOS) -> str:
    return (
        f"{SDMX_BASE}/data/{code}/{key}.{'+'.join(geos)}?format=SDMX-CSV&startPeriod={start_period}"
    )


def _fetch(url: str, label: str) -> requests.Response:
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as error:
        raise DownloadError(f"{label}: download failed from {url} ({error})") from error
    return response


def _fetch_sdmx(url: str, code: str) -> bytes:
    """SDMX-CSV body; Eurostat reports some errors (e.g. EXTRACTION_TOO_BIG) as XML with 200."""
    content = _fetch(url, code).content
    if not content.startswith(b"DATAFLOW"):
        snippet = content[:200].decode("utf-8", errors="replace")
        raise DownloadError(f"{code}: expected SDMX-CSV from {url}, got: {snippet}")
    return content


def download(raw_dir: Path, start_period: int = 2009) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for filename, (code, key) in DATASETS.items():
        content = _fetch_sdmx(dataset_url(code, key, start_period), code)
        (raw_dir / filename).write_bytes(content)

    for filename, (code, key) in REGIONAL_DATASETS.items():
        url = dataset_url(code, key, REGIONAL_START, COMPARISON_GEOS)
        (raw_dir / filename).write_bytes(_fetch_sdmx(url, code))
        check_coverage(read_sdmx(raw_dir / filename), filename)

    response = _fetch(GISCO_NUTS3_URL, "GISCO NUTS 3")
    features = [f for f in response.json()["features"] if f["properties"]["NUTS_ID"] in NUTS3_NAMES]
    (raw_dir / "marche_nuts3.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8"
    )


def read_sdmx(path: Path) -> pd.DataFrame:
    """Every dimension column, plus year, value (NaN when missing) and flag ('' when none)."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame = frame.drop(columns=[c for c in METADATA_COLUMNS if c in frame.columns])
    frame = frame.rename(columns={"TIME_PERIOD": "year", "OBS_VALUE": "value", "OBS_FLAG": "flag"})
    frame["year"] = frame["year"].astype(int)
    frame["value"] = pd.to_numeric(frame["value"].where(~frame["value"].isin(["", ":"])))
    frame["flag"] = frame["flag"].astype(str).str.strip()
    return frame


def check_coverage(frame: pd.DataFrame, filename: str) -> None:
    """Every comparison geography must have every year the focus region has, bar KNOWN_GAPS."""
    observed = frame.dropna(subset=["value"])
    present = set(zip(observed["geo"], observed["year"], strict=True))
    focus_years = sorted({year for geo, year in present if geo == FOCUS_GEO})
    if not focus_years:
        raise CoverageError(f"{filename}: no data for {FOCUS_GEO}")
    missing = [
        (geo, year)
        for geo in COMPARISON_GEOS
        for year in focus_years
        if (geo, year) not in present and (filename, geo, year) not in KNOWN_GAPS
    ]
    if missing:
        listed = ", ".join(f"{geo} {year}" for geo, year in missing)
        raise CoverageError(f"{filename}: missing {listed}")


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
