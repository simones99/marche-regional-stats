import pandas as pd

from marche_stats import companies


def _check(wide, name_prefix):
    return next(c for c in companies.quality_checks(wide) if c.name.startswith(name_prefix))


def test_clean_synthetic_file_passes_structural_checks(wide):
    for prefix in ("Unique", "Known province", "Counts", "TOTAL row", "No missing months"):
        assert _check(wide, prefix).passed, prefix


def test_total_mismatch_is_detected(wide):
    wide.loc[wide["Settore Ateco 2007"] == "TOTAL", wide.columns[5]] += 1
    assert not _check(wide, "TOTAL row").passed


def test_unchanged_last_month_is_flagged_as_stale(wide):
    wide[wide.columns[-1]] = wide[wide.columns[-2]]
    assert not _check(wide, "No month identical").passed
    assert companies.stale_months(wide) == [pd.to_datetime(wide.columns[-1], format="%d/%m/%Y")]


def test_regional_series_uses_total_rows_and_constant_boundaries(wide):
    long = companies.to_long(wide)
    series = companies.regional_series(long)

    in_scope = wide[
        (wide["Settore Ateco 2007"] == "TOTAL") & (wide["Territorio"] != "PU-42 Pennabilli")
    ]
    expected_first = in_scope[wide.columns[2]].sum()
    assert series.iloc[0] == expected_first
    assert series.index.freqstr == "ME"


def test_province_totals_map_to_nuts3(wide):
    totals = companies.province_totals(companies.to_long(wide))
    assert set(totals["nuts3"]) == {"ITI31", "ITI32", "ITI33", "ITI34", "ITI35"}
