import re
from pathlib import Path

import pandas as pd
import pytest
from conftest import synthetic_wide

from marche_stats import cli, companies, powerbi_export, timeseries


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

    actual_rows = table[table["actual"].notna()]
    assert list(table.index[table["holdout_sarima"].notna()]) == list(actual_rows.index[-12:])
    first_forecast = table.loc[table["forecast"].notna(), "date"].min()
    assert first_forecast == series.index[-1] + pd.offsets.MonthEnd(1)


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
    # Independent check of the first month: section rows of all municipalities that stay
    # in the region (everything but the transferred-out one).
    first_month = series.index[0].strftime("%d/%m/%Y")
    stays = wide[
        (wide["Settore Ateco 2007"] != "TOTAL") & (wide["Territorio"] != "PU-42 Pennabilli")
    ]
    assert region.iloc[0]["active_companies"] == stays[first_month].sum()

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


def test_cli_export_powerbi_writes_three_files(companies_csv, tmp_path):
    code = cli.main(
        [
            "export-powerbi",
            "--companies",
            str(companies_csv),
            "--powerbi",
            str(tmp_path),
            "--holdout",
            "12",
        ]
    )
    assert code == 0
    names = sorted(p.name for p in (tmp_path / "data").iterdir())
    assert names == ["forecast.csv", "forecast_accuracy.csv", "reconciliation.csv"]
    forecast = pd.read_csv(tmp_path / "data" / "forecast.csv")
    assert forecast["date"].iloc[0] == "2009-03-31"

    def raw(name):
        return pd.read_csv(tmp_path / "data" / name, dtype=str, keep_default_na=False)

    forecast_raw = raw("forecast.csv")
    accuracy_raw = raw("forecast_accuracy.csv")
    reconciliation_raw = raw("reconciliation.csv")
    iso_date = r"^\d{4}-\d{2}-\d{2}$"
    assert forecast_raw["date"].str.match(iso_date).all()
    assert accuracy_raw["holdout_start"].str.match(iso_date).all()
    assert accuracy_raw["holdout_end"].str.match(iso_date).all()
    assert reconciliation_raw["date"].str.match(iso_date).all()
    coverage = accuracy_raw["interval_coverage_pct"]
    sarima = accuracy_raw["method"] == "SARIMA"
    assert sarima.sum() == 1
    assert (coverage[~sarima] == "").all()
    assert (coverage[sarima] != "").all()
    assert reconciliation_raw["active_companies"].str.match(r"^\d+$").all()


FIXTURES = Path(__file__).parent / "fixtures"


def test_province_shapes_fit_the_box():
    table = powerbi_export.province_shapes_table(FIXTURES / "marche_nuts3.geojson")
    assert list(table.columns) == ["geo", "path", "label_x", "label_y"]
    assert list(table["geo"]) == ["ITI31", "ITI32", "ITI33", "ITI34", "ITI35"]
    for row in table.itertuples():
        assert re.fullmatch(r"(M[\d ,]+Z)+", row.path), row.geo
        numbers = [int(n) for n in re.findall(r"\d+", row.path)]
        assert max(numbers) <= 400, row.geo
        assert 0 <= row.label_x <= 400 and 0 <= row.label_y <= 400, row.geo
    labels = table.set_index("geo")
    # North up: Pesaro e Urbino lies north of Ascoli Piceno.
    assert labels.loc["ITI31", "label_y"] < labels.loc["ITI34", "label_y"]
