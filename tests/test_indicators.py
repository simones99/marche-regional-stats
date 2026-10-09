import math

import pandas as pd
import pytest
from regional_fixtures import BASE

from marche_stats import economy, education, indicators
from marche_stats.eurostat import COMPARISON_GEOS


def test_every_indicator_loads_in_long_format(eurostat_dir):
    fact = pd.concat(
        [education.education_indicators(eurostat_dir), economy.economy_indicators(eurostat_dir)]
    )
    assert list(fact.columns) == indicators.FACT_INDICATOR_COLUMNS
    assert set(fact["indicator_code"]) == set(indicators.BY_CODE)
    assert set(fact["geo_code"]) == set(COMPARISON_GEOS)
    assert not fact.duplicated(["geo_code", "year", "sex_code", "indicator_code"]).any()


def test_dataset_without_sex_dimension_gets_total(eurostat_dir):
    gdp = indicators.load(eurostat_dir, "gdp_pps_index")
    assert set(gdp["sex_code"]) == {"T"}


def test_flags_are_kept(eurostat_dir):
    leavers = indicators.load(eurostat_dir, "early_leavers").set_index(
        ["geo_code", "sex_code", "year"]
    )
    assert leavers.loc[("ITI3", "F", 2024), "flag"] == "u"
    assert leavers.loc[("ITI3", "T", 2024), "flag"] == ""


def _fact(values: dict[str, float], code: str = "early_leavers", year: int = 2024):
    return pd.DataFrame(
        [(geo, year, "T", code, value, "") for geo, value in values.items()],
        columns=indicators.FACT_INDICATOR_COLUMNS,
    )


def test_comparison_gaps_rank_and_target_when_lower_is_better():
    values = {"ITI3": 8.0, "ITH5": 7.0, "ITI1": 9.0, "ITI2": 8.0, "ITI4": 12.0, "ITF1": 10.0}
    values |= {"IT": 10.0, "EU27_2020": 9.5}
    row = indicators.comparisons(_fact(values)).iloc[0]
    assert row["gap_vs_italy"] == pytest.approx(-2.0)
    assert row["gap_vs_eu27"] == pytest.approx(-1.5)
    assert row["rank_among_regions"] == 2  # only Emilia-Romagna is lower; Umbria ties
    assert row["regions_ranked"] == 6
    assert row["distance_to_eu_target"] == pytest.approx(1.0)  # 1 point below the 9 % cap


def test_comparison_when_higher_is_better_and_no_target():
    values = {"ITI3": 95.0, "ITH5": 120.0, "ITI1": 105.0, "ITI2": 85.0, "ITI4": 110.0}
    values |= {"ITF1": 80.0, "IT": 98.0, "EU27_2020": 100.0}
    row = indicators.comparisons(_fact(values, "gdp_pps_index")).iloc[0]
    assert row["rank_among_regions"] == 4
    assert math.isnan(row["distance_to_eu_target"])


def test_comparison_uses_the_latest_marche_year_for_everyone():
    early = _fact({"ITI3": 10.0, "IT": 12.0, "EU27_2020": 11.0}, year=2023)
    late = _fact({"IT": 99.0, "EU27_2020": 99.0}, year=2024)  # no Marche value in 2024
    row = indicators.comparisons(pd.concat([early, late])).iloc[0]
    assert row["year"] == 2023
    assert row["gap_vs_italy"] == pytest.approx(-2.0)


def test_change_since_first_year(eurostat_dir):
    fact = education.education_indicators(eurostat_dir)
    table = indicators.comparisons(fact).set_index("indicator_code")
    assert table.loc["early_childhood", "first_year"] == 2014
    assert table.loc["early_leavers", "first_year"] == 2013
    assert table.loc["early_leavers", "change_since_first_year"] == pytest.approx(1.1)
    assert table.loc["early_leavers", "marche"] == pytest.approx(BASE["ITI3"] + 1.1)


def test_enrolment_keeps_single_levels_and_flags(eurostat_dir):
    fact = education.enrolment(eurostat_dir)
    assert list(fact.columns) == education.FACT_ENROLMENT_COLUMNS
    assert set(fact["isced_code"]) == set(education.ISCED_LEVELS)
    flagged = fact[(fact["geo_code"] == "ITI3") & (fact["isced_code"] == "ED3")]
    assert flagged.loc[flagged["year"] == 2016, "flag"].unique().tolist() == ["d"]


def test_enrolment_index_is_100_in_the_base_year(eurostat_dir):
    index = education.enrolment_index(education.enrolment(eurostat_dir))
    base = index[index["year"] == 2013]
    assert base["index"].to_numpy() == pytest.approx(100.0)
    marche = index[(index["geo_code"] == "ITI3") & (index["isced_code"] == "ED1")]
    assert marche.set_index("year")["index"][2024] == pytest.approx(100 * 0.99**11, rel=1e-3)
