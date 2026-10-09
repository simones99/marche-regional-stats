from conftest import FIXTURES, synthetic_wide

from marche_stats import companies, eurostat, report, timeseries


def test_demography_from_eurostat_fixtures():
    demo = eurostat.demography(FIXTURES)
    ancona = demo[(demo["geo"] == "ITI32") & (demo["year"] == 2024)].iloc[0]
    assert 0 < ancona["share_65_plus"] < 100
    assert ancona["crude_death_rate"] == 1000 * ancona["deaths"] / ancona["population"]
    assert set(eurostat.NUTS3_NAMES) <= set(demo["geo"])


def test_sarima_beats_naive_on_trending_seasonal_series():
    series = companies.regional_series(companies.to_long(synthetic_wide()))
    evaluation = timeseries.evaluate(series, holdout=12)
    errors = evaluation.errors["MAE"]
    assert errors["SARIMA"] < errors["Naive (last value)"]
    assert len(evaluation.holdout_forecast) == 12
    future = timeseries.forecast(series, evaluation.order, evaluation.seasonal_order, steps=6)
    assert (future["lower_95"] <= future["forecast"]).all()
    assert (future["forecast"] <= future["upper_95"]).all()


def test_report_end_to_end(companies_csv, eurostat_dir, tmp_path):
    docs = tmp_path / "docs"
    text = report.build(companies_csv, eurostat_dir, docs, holdout=12)
    for heading in ("## 4. SARIMA model", "## 5. Mortality", "## 6. Education", "## 7. Economy"):
        assert heading in text
    assert "| 2018 | Total |" in text  # benchmark table, by sex
    assert "| 2018 | Males |" in text
    assert "| 2018 | Females |" in text
    assert "By sex, across every area with a published rate, the difference ranges from " in text
    # EU27 deaths stop in 2023, so the 2024 table says it is missing instead of dropping it.
    assert "No complete 2024 data (deaths and population in every age group) for: " in text
    assert "European Union (27)." in text
    assert "Left out for lack of complete data in 2020-2024: European Union (27)." in text
    assert "European Union (27) only in 2013, 2014" in text
    assert "nan" not in text
    names = ("nuts3_maps", "province_index", "decomposition", "forecast")
    names += ("mortality", "indicators", "enrolment_index")
    for name in names:
        assert (docs / "figures" / f"{name}.png").stat().st_size > 0
