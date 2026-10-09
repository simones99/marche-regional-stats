"""Checks on the committed data/model/ tables, which the Power BI report reads."""

from pathlib import Path

from marche_stats import model

MODEL_DIR = Path(__file__).resolve().parents[1] / "data" / "model"


def test_committed_model_meets_the_contract():
    tables = model.read_tables(MODEL_DIR)
    assert sorted(tables) == sorted(model.TABLES)
    assert model.check_contract(tables) == []


def test_marche_standardised_rate_matches_eurostat_within_3_percent():
    fact = model.read_tables(MODEL_DIR)["fact_mortality"]
    rows = fact[(fact["geo_code"] == "ITI3") & (fact["sex_code"] == "T")]
    rows = rows.dropna(subset=["eurostat_std_rate"])
    assert len(rows) >= 4  # 2018-2021 at least
    difference = (rows["std_rate"] / rows["eurostat_std_rate"] - 1).abs()
    assert (difference <= 0.03).all(), rows[["year", "std_rate", "eurostat_std_rate"]]
