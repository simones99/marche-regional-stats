import math

import numpy as np
import pandas as pd
import pytest
from regional_fixtures import DEATH_RATES, expected_std_rate
from scipy.stats import chi2

from marche_stats import mortality
from marche_stats.eurostat import COMPARISON_GEOS


def _groups(deaths: dict[str, float], population: float = 1000.0) -> pd.DataFrame:
    """One key (geo X), every age group, `population` each; deaths 0 unless given."""
    return pd.DataFrame(
        {
            "geo": "X",
            "age_group": mortality.AGE_GROUPS,
            "deaths": [deaths.get(g, 0.0) for g in mortality.AGE_GROUPS],
            "population": population,
        }
    )


def test_esp_weights_sum_to_100000_with_85_plus_merged():
    assert sum(mortality.ESP_2013.values()) == 100_000
    assert mortality.ESP_2013["Y_GE85"] == 1500 + 800 + 200
    assert len(mortality.AGE_GROUPS) == 18


@pytest.mark.parametrize(
    ("age", "group"),
    [
        ("Y_LT1", "Y_LT5"),
        ("Y4", "Y_LT5"),
        ("Y5", "Y5-9"),
        ("Y84", "Y80-84"),
        ("Y85", "Y_GE85"),
        ("Y99", "Y_GE85"),
        ("Y_OPEN", "Y_GE85"),
        ("TOTAL", None),
        ("UNK", None),
    ],
)
def test_single_years_map_to_five_year_groups(age, group):
    assert mortality.age_group(age) == group


def test_hand_computed_example_with_two_age_groups():
    # 2 deaths at 0-4 and 10 at 85+, 1,000 people in each of the 18 groups:
    # standardised = 5,000 x 2/1,000 + 2,500 x 10/1,000 = 10 + 25 = 35 per 100,000;
    # crude = 100,000 x 12 / 18,000 = 66.67 per 100,000.
    out = mortality.standardise(_groups({"Y_LT5": 2, "Y_GE85": 10}), ["geo"]).iloc[0]
    assert out["std_rate"] == pytest.approx(35.0)
    assert out["crude_rate"] == pytest.approx(66.6667, abs=1e-4)
    assert out["deaths"] == 12
    assert out["population"] == 18_000


def test_dobson_reduces_to_exact_poisson_when_deaths_sit_in_one_group():
    # Rate = 2.5 x deaths, so the interval is 2.5 x the exact Poisson interval for 10 deaths.
    out = mortality.standardise(_groups({"Y_GE85": 10}), ["geo"]).iloc[0]
    assert out["std_rate"] == pytest.approx(25.0)
    assert out["ci_low"] == pytest.approx(2.5 * chi2.ppf(0.025, 20) / 2)
    assert out["ci_high"] == pytest.approx(2.5 * chi2.ppf(0.975, 22) / 2)


def test_dobson_with_zero_deaths_starts_at_zero():
    out = mortality.standardise(_groups({}), ["geo"]).iloc[0]
    assert out["std_rate"] == 0
    assert out["ci_low"] == 0
    assert math.isnan(out["ci_high"])


def test_dobson_interval_contains_the_rate():
    rng = np.random.default_rng(1)
    for _ in range(50):
        deaths = {g: float(rng.integers(0, 200)) for g in mortality.AGE_GROUPS}
        out = mortality.standardise(_groups(deaths, 5000.0), ["geo"]).iloc[0]
        assert out["ci_low"] <= out["std_rate"] <= out["ci_high"]


def test_key_missing_an_age_group_is_dropped():
    frame = _groups({"Y_GE85": 10})
    partial = frame.assign(geo="Y").iloc[:-1]
    out = mortality.standardise(pd.concat([frame, partial]), ["geo"])
    assert out["geo"].tolist() == ["X"]


def _deaths(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [("ITI3", "T", 2020, age, value) for age, value in rows],
        columns=["geo", "sex", "year", "age", "value"],
    )


def test_unknown_age_deaths_are_redistributed_and_the_total_kept():
    # Complete 0-4 and 85+ groups: 30 deaths under 1 and 70 at 90, zero at the other ages.
    young = [("Y_LT1", 30), *[(f"Y{age}", 0) for age in range(1, 5)]]
    old = [(f"Y{age}", 70 if age == 90 else 0) for age in range(85, 100)] + [("Y_OPEN", 0)]
    deaths = _deaths([*young, *old, ("UNK", 10), ("TOTAL", 110)])
    grouped = mortality.deaths_by_group(deaths).set_index("age_group")["deaths"]
    assert grouped.sum() == pytest.approx(110)
    assert grouped["Y_LT5"] == pytest.approx(33)
    assert grouped["Y_GE85"] == pytest.approx(77)
    share = mortality.unknown_age_share(deaths)["unknown_share"].iloc[0]
    assert share == pytest.approx(100 * 10 / 110)


def test_group_missing_a_single_age_has_no_deaths():
    # 0-4 lacks Y3 entirely and 5-9 has Y7 as missing (":"): neither group is complete.
    rows = [(age, 1.0) for age in ("Y_LT1", "Y1", "Y2", "Y4")]
    rows += [("Y5", 1.0), ("Y6", 1.0), ("Y7", float("nan")), ("Y8", 1.0), ("Y9", 1.0)]
    rows += [(f"Y{age}", 2.0) for age in range(10, 15)]
    grouped = mortality.deaths_by_group(_deaths(rows)).set_index("age_group")["deaths"]
    assert math.isnan(grouped["Y_LT5"])
    assert math.isnan(grouped["Y5-9"])
    assert grouped["Y10-14"] == pytest.approx(10)


def test_open_group_needs_every_age_from_85_to_100_plus():
    ages = [f"Y{age}" for age in range(85, 100)]
    without_open = mortality.deaths_by_group(_deaths([(age, 1.0) for age in ages]))
    assert without_open["deaths"].isna().all()
    with_open = mortality.deaths_by_group(_deaths([(age, 1.0) for age in [*ages, "Y_OPEN"]]))
    assert with_open["deaths"].tolist() == [16.0]


def test_unknown_share_is_zero_without_unknown_rows():
    deaths = _deaths([("Y_LT1", 30), ("TOTAL", 30)])
    assert mortality.unknown_age_share(deaths)["unknown_share"].iloc[0] == 0


def test_average_population_is_the_mean_of_two_first_januaries():
    population = pd.DataFrame(
        {
            "geo": "ITI3",
            "sex": "T",
            "age": ["Y_LT5", "Y_LT5", "Y_LT5", "TOTAL"],
            "year": [2020, 2021, 2022, 2020],
            "value": [100.0, 110.0, 130.0, 999.0],
        }
    )
    out = mortality.average_population(population).set_index("year")["population"]
    assert out.to_dict() == {2020: 105.0, 2021: 120.0}  # 2022 lacks 1 January 2023


def test_mortality_table_on_synthetic_extracts(eurostat_dir):
    fact = mortality.mortality_table(eurostat_dir)
    assert list(fact.columns) == mortality.FACT_MORTALITY_COLUMNS
    assert set(fact["geo_code"]) == set(COMPARISON_GEOS)
    assert not ((fact["geo_code"] == "EU27_2020") & (fact["year"] == 2024)).any()
    marche = fact[(fact["geo_code"] == "ITI3") & (fact["sex_code"] == "T")]
    assert marche["year"].tolist() == list(range(2013, 2025))
    # Deaths are rounded to whole numbers per group, so allow 1 %.
    assert marche["std_rate"].to_numpy() == pytest.approx(expected_std_rate(), rel=0.01)
    assert marche["eurostat_std_rate"].notna().sum() == 4  # 2018-2021


def test_benchmark_differences_cover_published_years_and_both_sexes(eurostat_dir):
    table = mortality.benchmark_differences(mortality.mortality_table(eurostat_dir))
    assert table[["year", "sex_code"]].values.tolist() == [
        [year, sex] for year in (2018, 2019, 2020, 2021) for sex in ("T", "M", "F")
    ]
    assert set(table["geo_code"]) == {"ITI3"}
    assert (table["difference_pct"].abs() < 3).all()


def test_benchmark_differences_for_every_area(eurostat_dir):
    fact = mortality.mortality_table(eurostat_dir)
    table = mortality.benchmark_differences(fact, geos=COMPARISON_GEOS)
    assert set(table["geo_code"]) == set(COMPARISON_GEOS)
    assert len(table) == len(COMPARISON_GEOS) * 4 * 3


def test_five_year_rate_is_pooled_not_averaged():
    # 85+ deaths, 1,000 then 3,000 people per group: 10 deaths in year 1 (rate 25),
    # 90 deaths in year 2 (rate 75). Pooled: 2,500 x 100 / 4,000 = 62.5; the average of the
    # two annual rates would be 50.
    rows = []
    for year, deaths, population in ((1, 10, 1000.0), (2, 90, 3000.0)):
        frame = _groups({"Y_GE85": deaths}, population).assign(year=year)
        rows.append(frame)
    frame = pd.concat(rows)
    pooled = frame.groupby(["geo", "age_group"], as_index=False)[["deaths", "population"]].sum()
    assert mortality.standardise(pooled, ["geo"])["std_rate"].iloc[0] == pytest.approx(62.5)


def test_five_year_window_follows_regions_and_italy_and_leaves_out_gaps(eurostat_dir):
    # Synthetic EU27 deaths stop in 2023: the window stays 2020-2024 and the EU27 is left
    # out instead of being pooled over four years.
    table = mortality.five_year_table(eurostat_dir)
    assert list(table.columns) == mortality.FACT_MORTALITY_5Y_COLUMNS
    assert set(table["period_start"]) == {2020}
    assert set(table["period_end"]) == {2024}
    assert "EU27_2020" not in set(table["geo_code"])
    assert len(table) == (len(COMPARISON_GEOS) - 1) * 3


def test_area_missing_an_age_group_in_the_window_is_left_out(eurostat_dir):
    path = eurostat_dir / "regional_population.csv"
    population = pd.read_csv(path, dtype=str, keep_default_na=False)
    gap = (population["geo"] == "ITF1") & (population["age"] == "Y30-34")
    gap &= population["TIME_PERIOD"] == "2022"
    population[~gap].to_csv(path, index=False)
    table = mortality.five_year_table(eurostat_dir)
    assert "ITF1" not in set(table["geo_code"])
    assert set(table["period_end"]) == {2024}


def test_synthetic_rates_rise_with_age():
    rates = list(DEATH_RATES.values())
    assert rates == sorted(rates)
