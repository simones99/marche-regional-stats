"""Rate-type indicators in long format and their comparisons with Italy, the EU and regions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from marche_stats.eurostat import FOCUS_GEO, REGIONS, read_sdmx

FACT_INDICATOR_COLUMNS = ["geo_code", "year", "sex_code", "indicator_code", "value", "flag"]


@dataclass(frozen=True)
class Indicator:
    code: str
    name: str
    unit: str
    source_dataset: str
    source_file: str
    higher_is_better: bool
    eu_2030_target: float | None


INDICATORS = (
    Indicator(
        "early_leavers",
        "Early leavers from education and training, 18-24",
        "%",
        "edat_lfse_16",
        "early_leavers.csv",
        False,
        9.0,
    ),
    Indicator(
        "tertiary_25_34",
        "Tertiary attainment, 25-34",
        "%",
        "edat_lfse_04",
        "tertiary_attainment.csv",
        True,
        45.0,
    ),
    Indicator(
        "early_childhood",
        "Early childhood education, age 3 to compulsory school age",
        "%",
        "educ_uoe_enra22",
        "early_childhood.csv",
        True,
        96.0,
    ),
    Indicator(
        "gdp_pps_index",
        "GDP per inhabitant in PPS (EU27 = 100)",
        "index",
        "nama_10r_2gdp",
        "gdp.csv",
        True,
        None,
    ),
    Indicator(
        "unemployment_15_74",
        "Unemployment rate, 15-74",
        "%",
        "lfst_r_lfu3rt",
        "unemployment.csv",
        False,
        None,
    ),
)
BY_CODE = {indicator.code: indicator for indicator in INDICATORS}


def load(raw_dir: Path, code: str) -> pd.DataFrame:
    """One indicator in long format; datasets without a sex dimension get sex_code T."""
    frame = read_sdmx(raw_dir / BY_CODE[code].source_file)
    if "sex" not in frame.columns:
        frame = frame.assign(sex="T")
    frame = frame.rename(columns={"geo": "geo_code", "sex": "sex_code"})
    return frame.assign(indicator_code=code)[FACT_INDICATOR_COLUMNS]


def load_many(raw_dir: Path, codes: tuple[str, ...]) -> pd.DataFrame:
    return pd.concat([load(raw_dir, code) for code in codes], ignore_index=True)


def comparisons(fact: pd.DataFrame) -> pd.DataFrame:
    """For each indicator (both sexes), the Marche in its latest year against the others.

    Every geography is read in the latest year with a Marche value. Rank 1 is the best of
    the six regions, following higher_is_better; ties share the best rank.
    """
    total = fact[fact["sex_code"] == "T"].dropna(subset=["value"])
    rows = []
    for indicator in INDICATORS:
        data = total[total["indicator_code"] == indicator.code]
        marche = data[data["geo_code"] == FOCUS_GEO].set_index("year")["value"]
        if marche.empty:
            continue
        year, first_year = int(marche.index.max()), int(marche.index.min())
        at_year = data[data["year"] == year].set_index("geo_code")["value"]
        value = at_year[FOCUS_GEO]
        italy, eu27 = at_year.get("IT", np.nan), at_year.get("EU27_2020", np.nan)
        regions = at_year.reindex(list(REGIONS)).dropna()
        better = regions > value if indicator.higher_is_better else regions < value
        target = indicator.eu_2030_target
        if target is None:
            distance = np.nan
        else:
            distance = value - target if indicator.higher_is_better else target - value
        rows.append(
            {
                "indicator_code": indicator.code,
                "year": year,
                "marche": value,
                "italy": italy,
                "eu27": eu27,
                "gap_vs_italy": value - italy,
                "gap_vs_eu27": value - eu27,
                "rank_among_regions": 1 + int(better.sum()),
                "regions_ranked": len(regions),
                "first_year": first_year,
                "change_since_first_year": value - marche[first_year],
                "distance_to_eu_target": distance,
            }
        )
    return pd.DataFrame(rows)
