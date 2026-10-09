"""Enrolment by ISCED level and the education indicators with EU 2030 targets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from marche_stats import indicators
from marche_stats.eurostat import read_sdmx

EDUCATION_INDICATORS = ("early_leavers", "tertiary_25_34", "early_childhood")
# ISCED 2011 level -> (label, group). Aggregates such as ED0-8 are left out.
ISCED_LEVELS = {
    "ED0": ("Early childhood education", "Early childhood"),
    "ED1": ("Primary education", "Primary"),
    "ED2": ("Lower secondary education", "Secondary"),
    "ED3": ("Upper secondary education", "Secondary"),
    "ED4": ("Post-secondary non-tertiary education", "Post-secondary non-tertiary"),
    "ED5": ("Short-cycle tertiary education", "Tertiary"),
    "ED6": ("Bachelor's or equivalent level", "Tertiary"),
    "ED7": ("Master's or equivalent level", "Tertiary"),
    "ED8": ("Doctoral or equivalent level", "Tertiary"),
}
FACT_ENROLMENT_COLUMNS = ["geo_code", "year", "sex_code", "isced_code", "enrolled", "flag"]


def enrolment(raw_dir: Path) -> pd.DataFrame:
    """fact_enrolment: pupils and students by geo, year, sex and single ISCED level."""
    frame = read_sdmx(raw_dir / "enrolment.csv")
    frame = frame[frame["isced11"].isin(ISCED_LEVELS)]
    frame = frame.rename(
        columns={"geo": "geo_code", "sex": "sex_code", "isced11": "isced_code", "value": "enrolled"}
    )
    return frame[FACT_ENROLMENT_COLUMNS].reset_index(drop=True)


def enrolment_index(fact: pd.DataFrame, base_year: int = 2013) -> pd.DataFrame:
    """Enrolment of both sexes as an index, base_year = 100, by geo and ISCED level."""
    total = fact[fact["sex_code"] == "T"]
    base = total[total["year"] == base_year].set_index(["geo_code", "isced_code"])["enrolled"]
    out = total.join(base.rename("base"), on=["geo_code", "isced_code"])
    out["index"] = 100 * out["enrolled"] / out["base"]
    return out[["geo_code", "year", "isced_code", "index"]].dropna().reset_index(drop=True)


def education_indicators(raw_dir: Path) -> pd.DataFrame:
    return indicators.load_many(raw_dir, EDUCATION_INDICATORS)
