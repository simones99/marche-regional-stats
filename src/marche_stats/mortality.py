"""Crude and age-standardised death rates (European Standard Population 2013)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

from marche_stats.eurostat import FOCUS_GEO, REGIONS, read_sdmx

# ESP 2013 weights by Eurostat five-year age group. The population data end at the open
# group 85+, so the weights of 85-89 (1,500), 90-94 (800) and 95+ (200) are merged.
ESP_2013 = {
    "Y_LT5": 5000,
    "Y5-9": 5500,
    "Y10-14": 5500,
    "Y15-19": 5500,
    "Y20-24": 6000,
    "Y25-29": 6000,
    "Y30-34": 6500,
    "Y35-39": 7000,
    "Y40-44": 7000,
    "Y45-49": 7000,
    "Y50-54": 7000,
    "Y55-59": 6500,
    "Y60-64": 6000,
    "Y65-69": 5500,
    "Y70-74": 5000,
    "Y75-79": 4000,
    "Y80-84": 2500,
    "Y_GE85": 2500,
}
AGE_GROUPS = list(ESP_2013)
PER = 100_000
KEYS = ["geo", "sex", "year"]

FACT_MORTALITY_COLUMNS = [
    "geo_code",
    "year",
    "sex_code",
    "deaths",
    "population_avg",
    "crude_rate",
    "std_rate",
    "ci_low",
    "ci_high",
    "eurostat_std_rate",
]
FACT_MORTALITY_5Y_COLUMNS = [
    "geo_code",
    "sex_code",
    "period_start",
    "period_end",
    "std_rate",
    "ci_low",
    "ci_high",
]


def age_group(age: str) -> str | None:
    """Five-year group of a single-year age code (Y_LT1, Y1 ... Y99, Y_OPEN); None otherwise."""
    if age in ("TOTAL", "UNK"):
        return None
    years = 0 if age == "Y_LT1" else 100 if age == "Y_OPEN" else int(age.removeprefix("Y"))
    return AGE_GROUPS[min(years // 5, len(AGE_GROUPS) - 1)]


SINGLE_AGES = ["Y_LT1", *[f"Y{age}" for age in range(1, 100)], "Y_OPEN"]
# Single years of age in each group: 5, and 16 for 85+ (85 to 99 and 100+).
GROUP_SIZES = pd.Series([age_group(age) for age in SINGLE_AGES]).value_counts()


def deaths_by_group(deaths: pd.DataFrame) -> pd.DataFrame:
    """Deaths by geo, sex, year and age group; unknown-age deaths are redistributed.

    A group has deaths only when every single year of age in it has a value; otherwise its
    deaths are NaN, so `standardise` drops that geo, sex and year. Deaths of unknown age are
    spread in proportion to the known-age deaths of the same geo, sex and year, so the total
    is kept.
    """
    known = deaths[~deaths["age"].isin(["TOTAL", "UNK"])]
    known = known.assign(age_group=known["age"].map(age_group))
    grouped = known.groupby([*KEYS, "age_group"], as_index=False).agg(
        value=("value", "sum"), ages=("value", "count")
    )
    complete = grouped["ages"] == grouped["age_group"].map(GROUP_SIZES)
    grouped["value"] = grouped["value"].where(complete)
    unknown = deaths[deaths["age"] == "UNK"].groupby(KEYS)["value"].sum().rename("unknown")
    grouped = grouped.join(unknown, on=KEYS)
    known_total = grouped.groupby(KEYS)["value"].transform("sum")
    grouped["deaths"] = (
        grouped["value"] + grouped["unknown"].fillna(0) * grouped["value"] / known_total
    )
    return grouped[[*KEYS, "age_group", "deaths"]]


def unknown_age_share(deaths: pd.DataFrame) -> pd.DataFrame:
    """Share (%) of deaths with unknown age, by geo, sex and year."""
    totals = deaths[deaths["age"].isin(["TOTAL", "UNK"])].pivot_table(
        index=KEYS, columns="age", values="value", aggfunc="sum"
    )
    totals = totals.reindex(columns=["TOTAL", "UNK"]).fillna({"UNK": 0})
    return (100 * totals["UNK"] / totals["TOTAL"]).rename("unknown_share").reset_index()


def average_population(population: pd.DataFrame) -> pd.DataFrame:
    """Mean of the populations on 1 January of year t and t+1, by geo, sex, year t, age group."""
    groups = population[population["age"].isin(AGE_GROUPS)].rename(columns={"age": "age_group"})
    index = [*KEYS, "age_group"]
    current = groups.set_index(index)["value"]
    following = groups.assign(year=groups["year"] - 1).set_index(index)["value"]
    return ((current + following) / 2).dropna().rename("population").reset_index()


def dobson_limits(
    deaths: np.ndarray, rate: np.ndarray, variance: np.ndarray, level: float = 0.95
) -> tuple[np.ndarray, np.ndarray]:
    """Dobson et al. (1991): exact Poisson limits for the total deaths, scaled to the rate.

    With no deaths the lower limit is 0 and the upper limit is undefined (NaN).
    """
    deaths = np.asarray(deaths, dtype=float)
    rate = np.asarray(rate, dtype=float)
    variance = np.asarray(variance, dtype=float)
    alpha = 1 - level
    has_deaths = deaths > 0
    safe = np.where(has_deaths, deaths, 1.0)
    poisson_low = chi2.ppf(alpha / 2, 2 * safe) / 2
    poisson_high = chi2.ppf(1 - alpha / 2, 2 * (safe + 1)) / 2
    scale = np.sqrt(variance / safe)
    lower = np.where(has_deaths, rate + scale * (poisson_low - safe), 0.0)
    upper = np.where(has_deaths, rate + scale * (poisson_high - safe), np.nan)
    return lower, upper


def standardise(frame: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Crude and ESP 2013 rates per 100,000 with a Dobson 95 % interval.

    `frame` has one row per `by` key and age group, with `deaths` and `population`. Keys
    lacking any age group are dropped instead of being standardised on a partial age range.
    """
    complete = frame.dropna(subset=["deaths", "population"])
    groups = complete.groupby(by)["age_group"].transform("nunique")
    complete = complete[groups == len(AGE_GROUPS)]
    weight = complete["age_group"].map(ESP_2013)
    terms = complete[by].assign(
        deaths=complete["deaths"],
        population=complete["population"],
        weighted=weight * complete["deaths"] / complete["population"],
        variance=weight**2 * complete["deaths"] / complete["population"] ** 2,
    )
    sums = terms.groupby(by).sum()
    factor = PER / sum(ESP_2013.values())
    out = pd.DataFrame(index=sums.index)
    out["deaths"] = sums["deaths"]
    out["population"] = sums["population"]
    out["crude_rate"] = PER * sums["deaths"] / sums["population"]
    out["std_rate"] = factor * sums["weighted"]
    lower, upper = dobson_limits(
        sums["deaths"].to_numpy(),
        out["std_rate"].to_numpy(),
        factor**2 * sums["variance"].to_numpy(),
    )
    out["ci_low"] = lower
    out["ci_high"] = upper
    return out.reset_index()


def _deaths_and_population(raw_dir: Path) -> pd.DataFrame:
    deaths = deaths_by_group(read_sdmx(raw_dir / "regional_deaths.csv"))
    population = average_population(read_sdmx(raw_dir / "regional_population.csv"))
    return deaths.merge(population, on=[*KEYS, "age_group"], how="inner")


def mortality_table(raw_dir: Path) -> pd.DataFrame:
    """fact_mortality: one row per geo, year and sex, with Eurostat's own rate when published."""
    rates = standardise(_deaths_and_population(raw_dir), KEYS)
    benchmark = read_sdmx(raw_dir / "death_rate_benchmark.csv")[[*KEYS, "value"]]
    out = rates.merge(benchmark.rename(columns={"value": "eurostat_std_rate"}), on=KEYS, how="left")
    out = out.rename(columns={"geo": "geo_code", "sex": "sex_code", "population": "population_avg"})
    return out[FACT_MORTALITY_COLUMNS]


def five_year_table(raw_dir: Path, years: int = 5) -> pd.DataFrame:
    """fact_mortality_5y: pooled rate over the latest `years` years complete for the core areas.

    The window is the latest `years` years with complete data (every age group) for the six
    regions and Italy. An area lacking complete data in any year of the window, such as the
    EU27 aggregate, is left out rather than pooled over fewer years. Deaths and populations
    are summed over the window in each age group and then standardised: a pooled rate, not
    an average of annual rates.
    """
    merged = _deaths_and_population(raw_dir)
    annual = standardise(merged, KEYS)
    complete = annual[annual["sex"] == "T"].groupby("geo")["year"].agg(set)
    end = min(max(complete[geo]) for geo in (*REGIONS, "IT"))
    window = set(range(end - years + 1, end + 1))
    geos = [geo for geo, available in complete.items() if window <= available]
    rows = merged[merged["geo"].isin(geos) & merged["year"].isin(window)]
    pooled = rows.groupby(["geo", "sex", "age_group"], as_index=False)[
        ["deaths", "population"]
    ].sum()
    rates = standardise(pooled, ["geo", "sex"])
    rates = rates.assign(period_start=min(window), period_end=end)
    return rates.rename(columns={"geo": "geo_code", "sex": "sex_code"})[FACT_MORTALITY_5Y_COLUMNS]


def benchmark_differences(fact: pd.DataFrame, geos: tuple[str, ...] = (FOCUS_GEO,)) -> pd.DataFrame:
    """Years with a published Eurostat rate, by area and sex: ours, Eurostat's, difference in %.

    Rows are ordered by area (as in `geos`), year and sex (T, M, F).
    """
    rows = fact[fact["geo_code"].isin(geos)].dropna(subset=["eurostat_std_rate"])
    rows = rows.assign(
        geo_order=rows["geo_code"].map({geo: i for i, geo in enumerate(geos)}),
        sex_order=rows["sex_code"].map({"T": 0, "M": 1, "F": 2}),
    ).sort_values(["geo_order", "year", "sex_order"])
    columns = ["geo_code", "year", "sex_code", "std_rate", "eurostat_std_rate"]
    out = rows[columns].reset_index(drop=True)
    out["difference_pct"] = 100 * (out["std_rate"] / out["eurostat_std_rate"] - 1)
    return out
