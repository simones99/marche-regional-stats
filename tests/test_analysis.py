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


def test_report_end_to_end(companies_csv, tmp_path):
    docs = tmp_path / "docs"
    text = report.build(companies_csv, FIXTURES, docs, holdout=12)
    assert "## 4. SARIMA model" in text
    for name in ("nuts3_maps", "province_index", "decomposition", "forecast"):
        assert (docs / "figures" / f"{name}.png").stat().st_size > 0
