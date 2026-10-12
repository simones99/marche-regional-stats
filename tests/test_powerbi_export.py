import pytest
from conftest import synthetic_wide

from marche_stats import companies, powerbi_export, timeseries


@pytest.fixture(scope="module")
def fitted():
    wide = synthetic_wide()
    series = companies.modelling_series(wide)
    evaluation = timeseries.evaluate(series, holdout=12)
    future = timeseries.forecast(series, evaluation.order, evaluation.seasonal_order, steps=6)
    return wide, series, evaluation, future


def test_forecast_table_has_one_row_per_month(fitted):
    _, series, evaluation, future = fitted
    table = powerbi_export.forecast_table(series, evaluation, future)
    assert list(table.columns) == [
        "date",
        "actual",
        "holdout_sarima",
        "holdout_naive",
        "holdout_seasonal_naive",
        "forecast",
        "lower_95",
        "upper_95",
    ]
    assert len(table) == len(series) + 6
    assert table["date"].is_monotonic_increasing
    assert table["holdout_sarima"].notna().sum() == 12
    assert table["forecast"].notna().sum() == 6
    assert table.loc[table["forecast"].notna(), "actual"].isna().all()


def test_accuracy_table_lists_the_three_methods(fitted):
    _, _, evaluation, _ = fitted
    table = powerbi_export.accuracy_table(evaluation)
    assert list(table.columns) == [
        "method",
        "mae",
        "mape_pct",
        "specification",
        "interval_coverage_pct",
        "holdout_start",
        "holdout_end",
    ]
    assert list(table["method"]) == ["SARIMA", "Naive (last value)", "Seasonal naive"]
    assert table.loc[0, "specification"].startswith("SARIMA(")
    assert 0 <= table.loc[0, "interval_coverage_pct"] <= 100
    assert table["mape_pct"].gt(0).all()


def test_reconciliation_matches_series_and_section_sums(fitted):
    wide, series, _, _ = fitted
    table = powerbi_export.reconciliation_table(wide, series)
    assert list(table.columns) == ["checkpoint", "geo", "date", "active_companies"]

    region = table[table["geo"] == "ITI3"]
    assert list(region["active_companies"]) == [series.iloc[0], series.iloc[-1]]

    provinces = table[table["geo"] != "ITI3"]
    assert set(provinces["geo"]) == {"ITI31", "ITI32", "ITI33", "ITI34", "ITI35"}
    assert len(provinces) == 10

    # Power Query sums section rows, not TOTAL rows: the checkpoint must equal that sum.
    first = provinces.iloc[0]
    month = first["date"].strftime("%d/%m/%Y")
    pesaro = wide[
        (wide["Settore Ateco 2007"] != "TOTAL")
        & wide["Territorio"].str.startswith("PU")
        & (wide["Territorio"] != "PU-42 Pennabilli")
    ]
    assert first["geo"] == "ITI31"
    assert first["active_companies"] == pesaro[month].sum()
