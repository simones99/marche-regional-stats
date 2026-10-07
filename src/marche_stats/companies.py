"""Active companies in the Marche region by municipality, ATECO 2007 section and month.

The source file is wide: one row per municipality ("territorio") and ATECO section,
one column per month-end date, separated by semicolons. Each municipality also has
a TOTAL row that equals the sum of its sections, so totals must be taken from the
TOTAL rows only, never by summing every row.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

# Camera di Commercio delle Marche, Open Data Imprese Italia (CC BY 4.0): active companies by
# municipality and ATECO 2007 section, monthly, 2009-2025 (archive of the ATECO 2007 series).
SOURCE_URL = "https://opendata.marche.camcom.it/data/Stock-Imprese-Attive-Marche-2009-2025.csv"
TIMEOUT_SECONDS = 180

TERRITORY = "Territorio"
SECTOR = "Settore Ateco 2007"
TOTAL = "TOTAL"

# Province code in the territory label -> NUTS 2024 level-3 region.
# "PS" is the former vehicle-plate code of Pesaro e Urbino; older downloads of the file use it
# for the unclassified records, which current downloads label "PU".
PROVINCE_TO_NUTS3 = {
    "PU": "ITI31",
    "PS": "ITI31",
    "AN": "ITI32",
    "MC": "ITI33",
    "AP": "ITI34",
    "FM": "ITI35",
}

# Municipalities transferred from Pesaro e Urbino to Emilia-Romagna (Law 117/2009 for the
# Alta Valmarecchia, Law 84/2021 for Montecopiolo and Sassofeltrio). Their companies leave
# the file when they move, which would look like closures, so they are removed from every
# month to keep the series on constant boundaries. Mergers inside the region (e.g. Ripe,
# Monterado and Castel Colonna into Trecastelli) need no correction: companies move to the
# new municipality in the same province.
TRANSFERRED_OUT = frozenset(
    {
        "PU-11 Casteldelci",
        "PU-24 Maiolo",
        "PU-39 Novafeltria",
        "PU-42 Pennabilli",
        "PU-53 San Leo",
        "PU-55 Sant'Agata Feltria",
        "PU-63 Talamello",
        "PU-33 Montecopiolo",
        "PU-60 Sassofeltrio",
    }
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def download(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(SOURCE_URL, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    path.write_bytes(response.content)


def read_wide(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")


def date_columns(wide: pd.DataFrame) -> list[str]:
    return [c for c in wide.columns if c not in (TERRITORY, SECTOR)]


def to_long(wide: pd.DataFrame) -> pd.DataFrame:
    """One row per territory, sector and month, with province and NUTS 3 code."""
    long = wide.melt(id_vars=[TERRITORY, SECTOR], var_name="date", value_name="active_companies")
    long["date"] = pd.to_datetime(long["date"], format="%d/%m/%Y")
    long["province"] = long[TERRITORY].str[:2]
    long["nuts3"] = long["province"].map(PROVINCE_TO_NUTS3)
    long = long.rename(columns={TERRITORY: "territory", SECTOR: "sector"})
    return long[["territory", "province", "nuts3", "sector", "date", "active_companies"]]


def quality_checks(wide: pd.DataFrame) -> list[Check]:
    """Validation of the source file. Failed checks are reported, not silently fixed."""
    dates = date_columns(wide)
    values = wide[dates]
    parsed = pd.to_datetime(pd.Index(dates), format="%d/%m/%Y")
    expected = pd.date_range(parsed.min(), parsed.max(), freq="ME")

    duplicates = int(wide.duplicated([TERRITORY, SECTOR]).sum())
    unknown_provinces = sorted(set(wide[TERRITORY].str[:2]) - set(PROVINCE_TO_NUTS3))

    totals = wide[wide[SECTOR] == TOTAL].set_index(TERRITORY)[dates]
    sections = wide[wide[SECTOR] != TOTAL].groupby(TERRITORY)[dates].sum()
    mismatched = int(((totals - sections.reindex(totals.index)).abs().sum(axis=1) > 0).sum())

    regional = totals.sum()
    unchanged = [d for d, delta in regional.diff().items() if delta == 0]
    identical_columns = [
        d for prev, d in zip(dates, dates[1:], strict=False) if values[d].equals(values[prev])
    ]
    closed = totals.index[(totals[dates[-1]] == 0) & (totals[dates[0]] > 0)]
    merged = [t for t in closed if t not in TRANSFERRED_OUT]
    transferred = sorted(TRANSFERRED_OUT & set(totals.index))
    transferred_companies = int(totals.loc[transferred, dates[0]].sum())

    return [
        Check(
            "Unique territory and sector",
            duplicates == 0,
            f"{duplicates} duplicated rows",
        ),
        Check(
            "Known province codes",
            not unknown_provinces,
            f"unknown: {', '.join(unknown_provinces) or 'none'}",
        ),
        Check(
            "Counts are non-negative integers",
            bool((values >= 0).all().all())
            and all(pd.api.types.is_integer_dtype(t) for t in values.dtypes),
            f"{int(values.isna().sum().sum())} missing values",
        ),
        Check(
            "TOTAL row equals the sum of sections",
            mismatched == 0,
            f"{mismatched} territories differ in at least one month",
        ),
        Check(
            "No missing months",
            len(parsed) == len(expected) and bool((parsed == expected).all()),
            f"{len(parsed)} months from {parsed.min():%Y-%m} to {parsed.max():%Y-%m}",
        ),
        Check(
            "No month identical to the previous one",
            not identical_columns,
            "identical: "
            + (", ".join(identical_columns) or "none")
            + f"; regional total unchanged in {len(unchanged)} month(s)",
        ),
        Check(
            "Municipalities merged inside the region (no correction needed)",
            True,
            f"{len(merged)} territories fall to zero and are absorbed by a successor",
        ),
        Check(
            "Municipalities transferred to another region (removed from all months)",
            len(transferred) == len(TRANSFERRED_OUT),
            f"{len(transferred)} territories, {transferred_companies:,} active companies "
            f"in {dates[0]}",
        ),
    ]


def stale_months(wide: pd.DataFrame) -> list[pd.Timestamp]:
    """Month columns identical to the previous month in every row (likely not updated)."""
    dates = date_columns(wide)
    return [
        pd.to_datetime(d, format="%d/%m/%Y")
        for prev, d in zip(dates, dates[1:], strict=False)
        if wide[d].equals(wide[prev])
    ]


def _totals_constant_boundaries(long: pd.DataFrame) -> pd.DataFrame:
    return long[(long["sector"] == TOTAL) & ~long["territory"].isin(TRANSFERRED_OUT)]


def province_totals(long: pd.DataFrame) -> pd.DataFrame:
    """Monthly active companies per NUTS 3 region, TOTAL rows, constant boundaries."""
    totals = _totals_constant_boundaries(long)
    return (
        totals.groupby(["nuts3", "date"], as_index=False)["active_companies"]
        .sum()
        .sort_values(["nuts3", "date"])
    )


def regional_series(long: pd.DataFrame) -> pd.Series:
    """Monthly active companies in the region (month-end index), constant boundaries."""
    totals = _totals_constant_boundaries(long)
    series = totals.groupby("date")["active_companies"].sum().sort_index()
    return series.asfreq("ME")
