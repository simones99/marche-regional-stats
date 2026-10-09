"""Synthetic Eurostat extracts for the eight comparison geographies, in SDMX-CSV layout.

Values are invented but consistent, so tests can work out expected results by hand:
- population is constant over time: 5,000 x scale per sex and five-year age group;
- deaths follow fixed age-specific rates (DEATH_RATES), all recorded at the first single
  year of each age group, with T = M + F;
- EU27 deaths stop in 2023 and EU27 enrolment skips 2017, as at the source.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from marche_stats.eurostat import COMPARISON_GEOS

# Kept independent of marche_stats.mortality, so the tests check the code against its own
# copy of the standard: Eurostat age group codes and ESP 2013 weights, 85+ merged.
AGE_GROUPS = ["Y_LT5", *[f"Y{a}-{a + 4}" for a in range(5, 85, 5)], "Y_GE85"]
ESP_2013 = dict(
    zip(
        AGE_GROUPS,
        [5000, 5500, 5500, 5500, 6000, 6000, 6500, 7000, 7000]
        + [7000, 7000, 6500, 6000, 5500, 5000, 4000, 2500, 2500],
        strict=True,
    )
)
YEARS = range(2013, 2025)
POPULATION_YEARS = range(2013, 2026)
SCALE = {
    "ITI3": 1.0,
    "ITH5": 3.0,
    "ITI1": 2.5,
    "ITI2": 0.6,
    "ITI4": 3.8,
    "ITF1": 0.9,
    "IT": 39.0,
    "EU27_2020": 300.0,
}
# Annual deaths per person, by five-year age group: 0.0005 at 0-4, rising 30 % per group.
DEATH_RATES = {group: 0.0005 * 1.3**i for i, group in enumerate(AGE_GROUPS)}
PER_SEX = 5_000
FIRST_AGE = {
    group: ("Y_LT1" if group == "Y_LT5" else f"Y{5 * i}") for i, group in enumerate(AGE_GROUPS)
}
SINGLE_AGES = ["Y_LT1", *[f"Y{age}" for age in range(1, 100)], "Y_OPEN"]
# Indicator base values by geography; each indicator adds a per-year drift.
BASE = {
    "ITI3": 10.0,
    "ITH5": 9.0,
    "ITI1": 11.0,
    "ITI2": 8.0,
    "ITI4": 12.0,
    "ITF1": 13.0,
    "IT": 12.5,
    "EU27_2020": 10.5,
}


def expected_std_rate() -> float:
    """ESP 2013 rate per 100,000 implied by DEATH_RATES, before rounding of deaths."""
    return sum(ESP_2013[group] * rate for group, rate in DEATH_RATES.items())


def _write(path: Path, code: str, dims: list[str], rows: list[tuple]) -> None:
    """rows: (*dimension values, geo, year, value, flag)."""
    columns = ["DATAFLOW", "LAST UPDATE", "freq", *dims, "geo"]
    columns += ["TIME_PERIOD", "OBS_VALUE", "OBS_FLAG", "CONF_STATUS"]
    data = [[f"ESTAT:{code.upper()}(1.0)", "01/10/26 23:00:00", "A", *row, ""] for row in rows]
    pd.DataFrame(data, columns=columns).to_csv(path, index=False)


def _deaths_rows() -> list[tuple]:
    rows = []
    for geo in COMPARISON_GEOS:
        for year in YEARS:
            if geo == "EU27_2020" and year == 2024:
                continue
            by_sex = {}
            for sex in ("M", "F"):
                by_sex[sex] = {
                    FIRST_AGE[g]: round(DEATH_RATES[g] * PER_SEX * SCALE[geo]) for g in AGE_GROUPS
                }
            by_sex["T"] = {age: by_sex["M"][age] + by_sex["F"][age] for age in by_sex["M"]}
            for sex, deaths in by_sex.items():
                for age in SINGLE_AGES:
                    rows.append(("NR", sex, age, geo, year, deaths.get(age, 0), ""))
                rows.append(("NR", sex, "TOTAL", geo, year, sum(deaths.values()), ""))
                rows.append(("NR", sex, "UNK", geo, year, 0, ""))
    return rows


def _population_rows() -> list[tuple]:
    rows = []
    for geo in COMPARISON_GEOS:
        for year in POPULATION_YEARS:
            for sex, factor in (("M", 1), ("F", 1), ("T", 2)):
                group_pop = PER_SEX * SCALE[geo] * factor
                for group in AGE_GROUPS:
                    rows.append(("NR", sex, group, geo, year, group_pop, ""))
                # Overlapping open groups and totals, as in the real extract: must be ignored.
                for extra, groups in (("Y_GE75", 3), ("Y_GE80", 2), ("TOTAL", len(AGE_GROUPS))):
                    rows.append(("NR", sex, extra, geo, year, group_pop * groups, ""))
                rows.append(("NR", sex, "UNK", geo, year, 0, ""))
    return rows


def _indicator_rows(dims_before: tuple, dims_after: tuple, base_shift: float, years) -> list:
    """Rows for a rate indicator by sex: T = base + 0.1 per year, M = T + 0.5, F = T - 0.5."""
    rows = []
    for geo in COMPARISON_GEOS:
        for year in years:
            total = BASE[geo] + base_shift + 0.1 * (year - 2013)
            for sex, value in (("T", total), ("M", total + 0.5), ("F", total - 0.5)):
                flag = "u" if (geo == "ITI3" and sex == "F" and year == 2024) else ""
                rows.append((*dims_before, sex, *dims_after, geo, year, round(value, 1), flag))
    return rows


def write_regional_fixtures(directory: Path) -> None:
    """Write the nine v0.2 raw files into `directory`."""
    _write(
        directory / "regional_deaths.csv",
        "demo_r_magec",
        ["unit", "sex", "age"],
        _deaths_rows(),
    )
    _write(
        directory / "regional_population.csv",
        "demo_r_pjangroup",
        ["unit", "sex", "age"],
        _population_rows(),
    )
    benchmark = [
        ("RT", sex, "TOTAL", "A-R_V-Y", geo, year, round(1.01 * expected_std_rate(), 2), "")
        for geo in COMPARISON_GEOS
        for year in range(2018, 2022)
        for sex in ("T", "M", "F")
    ]
    _write(
        directory / "death_rate_benchmark.csv",
        "hlth_cd_asdr2",
        ["unit", "sex", "age", "icd10"],
        benchmark,
    )
    enrolment = []
    for geo in COMPARISON_GEOS:
        for year in YEARS:
            if geo == "EU27_2020" and year == 2017:
                continue
            for level in range(9):
                males = round(1000 * SCALE[geo] * (9 - level) * 0.99 ** (year - 2013))
                flag = "d" if (geo == "ITI3" and level == 3 and year == 2016) else ""
                for sex, value in (("M", males), ("F", males), ("T", 2 * males)):
                    enrolment.append(("NR", f"ED{level}", sex, geo, year, value, flag))
            enrolment.append(("NR", "ED0-8", "T", geo, year, 0, ""))  # aggregate: ignored
    _write(directory / "enrolment.csv", "educ_uoe_enra11", ["unit", "isced11", "sex"], enrolment)
    _write(
        directory / "early_leavers.csv",
        "edat_lfse_16",
        ["unit", "sex", "age"],
        _indicator_rows(("PC",), ("Y18-24",), 0.0, YEARS),
    )
    _write(
        directory / "tertiary_attainment.csv",
        "edat_lfse_04",
        ["sex", "isced11", "age", "unit"],
        _indicator_rows((), ("ED5-8", "Y25-34", "PC"), 20.0, YEARS),
    )
    early_childhood = [
        ("PC", geo, year, round(90 + BASE[geo] / 4 + 0.1 * (year - 2014), 1), "")
        for geo in COMPARISON_GEOS
        for year in range(2014 if geo != "EU27_2020" else 2013, 2025)
    ]
    _write(directory / "early_childhood.csv", "educ_uoe_enra22", ["unit"], early_childhood)
    gdp = [
        ("PPS_HAB_EU27_2020", geo, year, 100 if geo == "EU27_2020" else 80 + 2 * BASE[geo], "")
        for geo in COMPARISON_GEOS
        for year in YEARS
    ]
    _write(directory / "gdp.csv", "nama_10r_2gdp", ["unit"], gdp)
    _write(
        directory / "unemployment.csv",
        "lfst_r_lfu3rt",
        ["isced11", "sex", "age", "unit"],
        _indicator_rows(("TOTAL",), ("Y15-74", "PC"), -2.0, YEARS),
    )
