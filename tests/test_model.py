import pandas as pd

from marche_stats import cli, model


def test_built_tables_meet_the_contract(eurostat_dir):
    assert model.check_contract(model.build_tables(eurostat_dir)) == []


def test_written_tables_read_back_unchanged_and_sorted(eurostat_dir, tmp_path):
    tables = model.build_tables(eurostat_dir)
    model.write_tables(tables, tmp_path)
    again = model.read_tables(tmp_path)
    assert model.check_contract(again) == []
    fact = again["fact_mortality"]
    assert fact[model.KEYS["fact_mortality"]].equals(
        fact[model.KEYS["fact_mortality"]]
        .sort_values(model.KEYS["fact_mortality"])
        .reset_index(drop=True)
    )
    first = (tmp_path / "fact_indicator.csv").read_bytes()
    model.write_tables(model.read_tables(tmp_path), tmp_path)
    assert (tmp_path / "fact_indicator.csv").read_bytes() == first  # writing is idempotent


def test_dim_year_spans_every_fact_year(eurostat_dir):
    tables = model.build_tables(eurostat_dir)
    years = tables["dim_year"]["year"].tolist()
    assert years[0] == 2013
    assert years == list(range(2013, years[-1] + 1))
    assert years[-1] == 2024


def test_contract_reports_duplicates_unknown_keys_and_types(eurostat_dir):
    tables = model.build_tables(eurostat_dir)
    broken = dict(tables)
    broken["fact_indicator"] = pd.concat(
        [tables["fact_indicator"], tables["fact_indicator"].head(1)]
    )
    broken["fact_enrolment"] = tables["fact_enrolment"].assign(isced_code="ED9")
    broken["dim_geo"] = tables["dim_geo"].assign(sort_order="first")
    problems = "\n".join(model.check_contract(broken))
    assert "fact_indicator: 1 duplicated keys" in problems
    assert "fact_enrolment.isced_code: ['ED9'] not in dim_isced" in problems
    assert "dim_geo.sort_order: not numeric" in problems


def test_contract_reports_missing_table_and_wrong_columns(eurostat_dir):
    tables = model.build_tables(eurostat_dir)
    del tables["dim_sex"]
    tables["dim_year"] = tables["dim_year"].rename(columns={"year": "anno"})
    problems = "\n".join(model.check_contract(tables))
    assert "dim_sex: missing" in problems
    assert "dim_year: columns ['anno']" in problems


def test_cli_model_step_writes_every_table(eurostat_dir, tmp_path):
    out = tmp_path / "model"
    assert cli.main(["model", "--eurostat-dir", str(eurostat_dir), "--model-dir", str(out)]) == 0
    assert sorted(p.stem for p in out.glob("*.csv")) == sorted(model.TABLES)
