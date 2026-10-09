"""Star schema for the Power BI report: dimension and fact tables in data/model/."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from marche_stats import economy, education, indicators, mortality
from marche_stats.eurostat import COMPARISON_GEOS, GEO_NAMES, REGIONAL_START

TABLES: dict[str, list[str]] = {
    "dim_geo": ["geo_code", "geo_name", "geo_level", "role", "sort_order"],
    "dim_year": ["year"],
    "dim_sex": ["sex_code", "sex_label"],
    "dim_isced": ["isced_code", "isced_label", "isced_group", "sort_order"],
    "dim_indicator": [
        "indicator_code",
        "indicator_name",
        "unit",
        "source_dataset",
        "higher_is_better",
        "eu_2030_target",
    ],
    "fact_indicator": indicators.FACT_INDICATOR_COLUMNS,
    "fact_mortality": mortality.FACT_MORTALITY_COLUMNS,
    "fact_mortality_5y": mortality.FACT_MORTALITY_5Y_COLUMNS,
    "fact_enrolment": education.FACT_ENROLMENT_COLUMNS,
}
KEYS: dict[str, list[str]] = {
    "dim_geo": ["geo_code"],
    "dim_year": ["year"],
    "dim_sex": ["sex_code"],
    "dim_isced": ["isced_code"],
    "dim_indicator": ["indicator_code"],
    "fact_indicator": ["geo_code", "year", "sex_code", "indicator_code"],
    "fact_mortality": ["geo_code", "year", "sex_code"],
    "fact_mortality_5y": ["geo_code", "sex_code"],
    "fact_enrolment": ["geo_code", "year", "sex_code", "isced_code"],
}
# Fact key column -> (dimension table, dimension column).
REFERENCES = {
    "geo_code": ("dim_geo", "geo_code"),
    "year": ("dim_year", "year"),
    "sex_code": ("dim_sex", "sex_code"),
    "indicator_code": ("dim_indicator", "indicator_code"),
    "isced_code": ("dim_isced", "isced_code"),
}
NUMERIC = {
    "sort_order",
    "year",
    "eu_2030_target",
    "value",
    "deaths",
    "population_avg",
    "crude_rate",
    "std_rate",
    "ci_low",
    "ci_high",
    "eurostat_std_rate",
    "period_start",
    "period_end",
    "enrolled",
}
# Fixed rounding per column, so that a diff in git always means changed data.
DECIMALS = {
    "eu_2030_target": 1,
    "value": 2,
    "deaths": 1,
    "population_avg": 1,
    "crude_rate": 2,
    "std_rate": 2,
    "ci_low": 2,
    "ci_high": 2,
    "eurostat_std_rate": 2,
    "enrolled": 0,
}
SEX_LABELS = {"T": "Total", "M": "Males", "F": "Females"}
GEO_LEVELS = {"IT": "country", "EU27_2020": "eu"}
GEO_ROLES = {"ITI3": "focus", "IT": "benchmark", "EU27_2020": "benchmark"}


def _dimensions(last_year: int) -> dict[str, pd.DataFrame]:
    geo = pd.DataFrame(
        [
            (
                code,
                GEO_NAMES[code],
                GEO_LEVELS.get(code, "nuts2"),
                GEO_ROLES.get(code, "neighbour"),
                i,
            )
            for i, code in enumerate(COMPARISON_GEOS, start=1)
        ],
        columns=TABLES["dim_geo"],
    )
    isced = pd.DataFrame(
        [
            (code, label, group, i)
            for i, (code, (label, group)) in enumerate(education.ISCED_LEVELS.items(), start=1)
        ],
        columns=TABLES["dim_isced"],
    )
    indicator = pd.DataFrame(
        [
            (i.code, i.name, i.unit, i.source_dataset, i.higher_is_better, i.eu_2030_target)
            for i in indicators.INDICATORS
        ],
        columns=TABLES["dim_indicator"],
    )
    return {
        "dim_geo": geo,
        "dim_year": pd.DataFrame({"year": range(REGIONAL_START, last_year + 1)}),
        "dim_sex": pd.DataFrame(list(SEX_LABELS.items()), columns=TABLES["dim_sex"]),
        "dim_isced": isced,
        "dim_indicator": indicator,
    }


def build_tables(raw_dir: Path) -> dict[str, pd.DataFrame]:
    facts = {
        "fact_indicator": pd.concat(
            [education.education_indicators(raw_dir), economy.economy_indicators(raw_dir)],
            ignore_index=True,
        ),
        "fact_mortality": mortality.mortality_table(raw_dir),
        "fact_mortality_5y": mortality.five_year_table(raw_dir),
        "fact_enrolment": education.enrolment(raw_dir),
    }
    last_year = max(int(facts[name]["year"].max()) for name in facts if "year" in TABLES[name])
    return _dimensions(last_year) | facts


def write_tables(tables: dict[str, pd.DataFrame], out_dir: Path) -> None:
    """One CSV per table: columns in contract order, rows sorted by key, fixed rounding."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, columns in TABLES.items():
        frame = tables[name][columns].sort_values(KEYS[name]).reset_index(drop=True)
        for column, decimals in DECIMALS.items():
            if column in frame.columns:
                frame[column] = frame[column].round(decimals)
                if decimals == 0:
                    frame[column] = frame[column].astype("Int64")
        frame.to_csv(out_dir / f"{name}.csv", index=False, lineterminator="\n")


def read_tables(model_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(model_dir / f"{name}.csv", keep_default_na=False, na_values=[""])
        for name in TABLES
        if (model_dir / f"{name}.csv").exists()
    }


def check_contract(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Problems with columns, types, keys or references; an empty list means the model is sound."""
    problems = []
    for name, columns in TABLES.items():
        frame = tables.get(name)
        if frame is None:
            problems.append(f"{name}: missing")
            continue
        if list(frame.columns) != columns:
            problems.append(f"{name}: columns {list(frame.columns)}, expected {columns}")
            continue
        for column in NUMERIC.intersection(columns):
            if not pd.api.types.is_numeric_dtype(frame[column]):
                problems.append(f"{name}.{column}: not numeric")
        keys = KEYS[name]
        if frame[keys].isna().any().any():
            problems.append(f"{name}: empty key values in {keys}")
        duplicated = int(frame.duplicated(keys).sum())
        if duplicated:
            problems.append(f"{name}: {duplicated} duplicated keys {keys}")
        if name.startswith("fact_"):
            for column in keys:
                dimension, dimension_column = REFERENCES[column]
                if dimension_column not in tables.get(dimension, pd.DataFrame()).columns:
                    continue  # reported above as a missing table or wrong columns
                unknown = set(frame[column].dropna()) - set(tables[dimension][dimension_column])
                if unknown:
                    problems.append(f"{name}.{column}: {sorted(unknown)[:5]} not in {dimension}")
    return problems
