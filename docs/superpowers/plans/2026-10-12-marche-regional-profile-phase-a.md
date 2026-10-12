# Marche Regional Profile, Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data side of the merged Power BI report: Python exports and source checks, a new region-ready semantic model (TMDL), its measures and calculation group, and one model-check page that proves it works after a refresh.

**Architecture:** Python keeps the analysis that Power BI cannot do well (SARIMA) and writes three small CSV files to `powerbi/data/`. A new `.pbip` project, `powerbi/marche-regional-profile`, holds a star schema keyed on NUTS codes. Power Query downloads Eurostat (through one function, `fnEurostat`), GISCO and the Chamber of Commerce file, and every query depends only on parameters, so profiling another region means changing parameters. `marche-stats check-sources` reads the same TMDL files and requests every source, weekly in CI.

**Tech Stack:** Python 3.11, pandas, statsmodels, requests, pytest, ruff; Power BI Desktop (PBIP/PBIR, TMDL, Power Query M, DAX); GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-12-marche-regional-profile-report-design.md`

---

## Ground rules for every task

- Work on the branch `powerbi-pbip`. Run every command from the repository root.
- **Power BI Desktop must be closed** while any `.tmdl` or report JSON file changes. Saving in Desktop rewrites every TMDL file and would overwrite edits made outside it. Check with `tasklist /FI "IMAGENAME eq PBIDesktop.exe"` (PowerShell) before Tasks 6–14 and 17.
- TMDL indentation is **tabs**. In the code blocks below, every leading indent of a TMDL file is tabs. Power Query lines inside a `source =` block start with four tabs and may then continue with spaces, as Desktop writes them. No TMDL line may start with a space; the test in Task 6 enforces it.
- Nobody can run DAX or Power Query outside Power BI Desktop. The static tests in Task 6 catch broken references. The refresh in Task 16 is the real test.
- Python style: ruff (line length 100), `from __future__ import annotations`, docstrings on modules and public functions, as in `src/marche_stats/`.

## File map

| Path | Responsibility |
|---|---|
| `src/marche_stats/companies.py` | + `modelling_series()`: the regional series the model is fitted on |
| `src/marche_stats/report.py` | uses `modelling_series()` |
| `src/marche_stats/powerbi_export.py` (new) | forecast, accuracy and reconciliation tables → `powerbi/data/*.csv` |
| `src/marche_stats/sources.py` (new) | reads parameters and source calls from TMDL, requests every source |
| `src/marche_stats/cli.py` | + steps `export-powerbi`, `check-sources` |
| `tests/test_companies.py` | + test for `modelling_series()` |
| `tests/test_powerbi_export.py` (new) | export tables and CLI step |
| `tests/test_sources.py` (new) | TMDL parsing, URL building, checks with a fake HTTP client |
| `tests/test_powerbi_model.py` (new) | static consistency checks of the TMDL model and report JSON |
| `.github/workflows/check-sources.yml` (new) | weekly source check |
| `.gitignore` | keep `powerbi/data/` tracked |
| `powerbi/marche-regional-profile.pbip` (new) | project entry point |
| `powerbi/marche-regional-profile.SemanticModel/` (new) | the model: `definition/*.tmdl`, `definition/tables/*.tmdl` |
| `powerbi/marche-regional-profile.Report/` (new) | the report, copied from the old project with its pages replaced by one check page |
| `powerbi/data/*.csv` (new, generated) | Python export read by Power BI through GitHub raw URLs |
| `powerbi/README.md`, `powerbi/sources.md` | describe the new project; the old projects are removed |

---

### Task 0: Record the verified facts in the spec

Planning verified five facts that change details of the spec. Update it before building.

**Files:**
- Modify: `docs/superpowers/specs/2026-10-12-marche-regional-profile-report-design.md`

- [ ] **Step 1: Business series dates.** In the Pages table, row 6, replace `Active companies, January 2009 to March 2025, on constant boundaries` with `Active companies, March 2009 to March 2025, on constant boundaries (February 2025 is dropped: identical to January in every cell, so not updated)`. In the Facts table, row `Companies`, keep the text and add at the end: `Sections A–T plus X (not classified).`

- [ ] **Step 2: Provinces parameter.** In the Power Query parameters table, insert this row after `PeerRegions`:

```markdown
| `ProvinceRegions` | `ITI31,ITI32,ITI33,ITI34,ITI35` | NUTS 3 provinces of the focus region. Eurostat filters accept only exact codes (no "starts with"), and a query that read the codes from the GISCO-based `Geo` table would trip the Power Query privacy firewall. `check-sources` verifies that the parameter matches the GISCO children of `FocusRegion` |
```

In the Dimensions table, row `Geo`, replace `filtered by the parameters, plus static rows` with `filtered to the codes in FocusRegion, PeerRegions and ProvinceRegions (the refresh fails if one is missing from GISCO), plus static rows`.

- [ ] **Step 3: `fnEurostat` geo codes.** In the Data flow section, replace `- takes geo codes from \`Geo\`, never typed by hand;` with `- takes geo codes from the parameters, by level: EU (\`EU27_2020\`), Country, NUTS2 (focus and peers), NUTS3 (provinces);`.

- [ ] **Step 4: Reconciliation checkpoints.** In the Data flow section, replace `The reconciliation checkpoints are: the regional total in January 2009 and March 2025, and each province in March 2025.` with `The reconciliation checkpoints are: the regional total in the first month (March 2009) and in the last month the model is fitted on (January 2025), and each province in the first and last full-year December (2009, 2024), which the "change" and "per 1,000 residents" indicators use.`

- [ ] **Step 5: Text guard.** In the calculation group rules, replace `(\`IF ( ISNUMERIC ( SELECTEDMEASURE () ), …, SELECTEDMEASURE () )\`)` with `(\`IF ( ISTEXT ( SELECTEDMEASURE () ), SELECTEDMEASURE (), … )\`; \`ISTEXT\` and not \`ISNUMERIC\`, so a blank value is still compared)`.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-10-12-marche-regional-profile-report-design.md
git commit -m "Record verified source details in the report spec"
```

---

### Task 1: `companies.modelling_series()`

`report.build()` stops the regional series before the first stale month. The Power BI export needs the same series, so the rule moves into one function.

**Files:**
- Modify: `src/marche_stats/companies.py` (append after `regional_series`)
- Modify: `src/marche_stats/report.py:26-33`
- Test: `tests/test_companies.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_companies.py`)

```python
def test_modelling_series_stops_before_first_stale_month(wide):
    wide[wide.columns[-2]] = wide[wide.columns[-3]]  # second-to-last month not updated
    series = companies.modelling_series(wide)
    assert series.index[-1] == pd.to_datetime(wide.columns[-3], format="%d/%m/%Y")
    assert series.index.freqstr == "ME"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_companies.py::test_modelling_series_stops_before_first_stale_month -v`
Expected: FAIL with `AttributeError: module 'marche_stats.companies' has no attribute 'modelling_series'`

- [ ] **Step 3: Implement** (append to `src/marche_stats/companies.py`)

```python
def modelling_series(wide: pd.DataFrame) -> pd.Series:
    """Regional series on constant boundaries, stopped before the first stale month.

    SARIMA needs consecutive months, so a month identical to the previous one in every
    cell (not updated) ends the series even when later months exist.
    """
    series = regional_series(to_long(wide))
    stale = stale_months(wide)
    if stale:
        series = series[series.index < min(stale)]
    return series
```

- [ ] **Step 4: Use it in `report.build()`.** In `src/marche_stats/report.py`, replace

```python
    long = companies.to_long(wide)

    series = companies.regional_series(long)
    if stale:
        # A month identical to the previous one in every cell is treated as not updated.
        series = series[series.index < min(stale)]
```

with

```python
    long = companies.to_long(wide)
    series = companies.modelling_series(wide)
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_companies.py tests/test_analysis.py -v`
Expected: all PASS (the end-to-end report test proves the refactor kept behaviour).

- [ ] **Step 6: Lint and commit**

```bash
ruff check src tests && ruff format --check src tests
git add src/marche_stats/companies.py src/marche_stats/report.py tests/test_companies.py
git commit -m "Move the stale-month cut of the regional series into companies.modelling_series"
```

---

### Task 2: `powerbi_export` tables

**Files:**
- Create: `src/marche_stats/powerbi_export.py`
- Test: `tests/test_powerbi_export.py`

- [ ] **Step 1: Write the failing tests** (`tests/test_powerbi_export.py`)

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_powerbi_export.py -v`
Expected: FAIL with `ImportError: cannot import name 'powerbi_export'`

- [ ] **Step 3: Implement** (`src/marche_stats/powerbi_export.py`)

```python
"""Tables for the Power BI report: SARIMA forecast, its accuracy and reconciliation totals.

Power BI cleans the business register itself, in Power Query. These files carry what the
report cannot compute well (the SARIMA model validated in Python) and the totals that its
own cleaning must reproduce exactly.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from marche_stats import companies, timeseries

FOCUS_REGION = "ITI3"
HOLDOUT_COLUMNS = {
    "SARIMA": "holdout_sarima",
    "Naive (last value)": "holdout_naive",
    "Seasonal naive": "holdout_seasonal_naive",
}


def forecast_table(
    series: pd.Series, evaluation: timeseries.Evaluation, future: pd.DataFrame
) -> pd.DataFrame:
    """One row per month-end: actual values, holdout forecasts and the future forecast."""
    holdout = evaluation.holdout_forecast.drop(columns="actual").rename(columns=HOLDOUT_COLUMNS)
    frame = pd.DataFrame({"actual": series}).join(holdout, how="outer").join(future, how="outer")
    frame.index.name = "date"
    return frame.reset_index()


def accuracy_table(evaluation: timeseries.Evaluation) -> pd.DataFrame:
    """Out-of-sample errors of SARIMA and the naive baselines on the holdout months."""
    table = evaluation.errors.rename(columns={"MAE": "mae", "MAPE (%)": "mape_pct"})
    table.index.name = "method"
    table = table.reset_index()
    order, seasonal = evaluation.order, evaluation.seasonal_order
    is_sarima = table["method"] == "SARIMA"
    table["specification"] = ""
    table.loc[is_sarima, "specification"] = f"SARIMA{order}{seasonal[:3]}[{seasonal[3]}]"
    table["interval_coverage_pct"] = None
    table.loc[is_sarima, "interval_coverage_pct"] = 100 * evaluation.interval_coverage
    table["interval_coverage_pct"] = table["interval_coverage_pct"].astype(float)
    table["holdout_start"] = evaluation.holdout_forecast.index.min()
    table["holdout_end"] = evaluation.holdout_forecast.index.max()
    return table


def reconciliation_table(wide: pd.DataFrame, series: pd.Series) -> pd.DataFrame:
    """Checkpoints the Power Query cleaning must match: region and provinces."""
    provinces = companies.province_totals(companies.to_long(wide))
    provinces = provinces[provinces["date"] <= series.index[-1]]
    december = provinces[provinces["date"].dt.month == 12]
    first_dec, last_dec = december["date"].min(), december["date"].max()

    rows = [
        ("Region, first month", FOCUS_REGION, series.index[0], series.iloc[0]),
        ("Region, last modelled month", FOCUS_REGION, series.index[-1], series.iloc[-1]),
    ]
    for row in december[december["date"].isin([first_dec, last_dec])].itertuples():
        rows.append((f"{row.nuts3}, {row.date:%b %Y}", row.nuts3, row.date, row.active_companies))
    table = pd.DataFrame(rows, columns=["checkpoint", "geo", "date", "active_companies"])
    table["active_companies"] = table["active_companies"].astype(int)
    return table


def build(companies_csv: Path, out_dir: Path, holdout: int = 24) -> dict[str, Path]:
    """Fit the model and write forecast.csv, forecast_accuracy.csv and reconciliation.csv."""
    wide = companies.read_wide(companies_csv)
    series = companies.modelling_series(wide)
    evaluation = timeseries.evaluate(series, holdout=holdout)
    future = timeseries.forecast(series, evaluation.order, evaluation.seasonal_order, steps=12)
    tables = {
        "forecast.csv": forecast_table(series, evaluation, future),
        "forecast_accuracy.csv": accuracy_table(evaluation),
        "reconciliation.csv": reconciliation_table(wide, series),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, frame in tables.items():
        path = out_dir / name
        frame.to_csv(path, index=False, date_format="%Y-%m-%d", float_format="%.4f")
        paths[name] = path
    return paths
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_powerbi_export.py -v`
Expected: 3 PASS (the SARIMA grid search makes the module fixture take a few tens of seconds).

- [ ] **Step 5: Lint and commit**

```bash
ruff check src tests && ruff format --check src tests
git add src/marche_stats/powerbi_export.py tests/test_powerbi_export.py
git commit -m "Add the Power BI export tables: forecast, accuracy, reconciliation"
```

---

### Task 3: CLI step `export-powerbi` and tracked `powerbi/data/`

**Files:**
- Modify: `src/marche_stats/cli.py`
- Modify: `.gitignore`
- Test: `tests/test_powerbi_export.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_powerbi_export.py`)

```python
import pandas as pd

from marche_stats import cli


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
```

Move the two new imports to the top of the file with the others, so ruff's import sorting passes.

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_powerbi_export.py::test_cli_export_powerbi_writes_three_files -v`
Expected: FAIL, argparse exits with `invalid choice: 'export-powerbi'`.

- [ ] **Step 3: Implement.** Replace `src/marche_stats/cli.py` with:

```python
"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from marche_stats import companies, eurostat, powerbi_export, report, sources

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="marche-stats", description=__doc__)
    parser.add_argument(
        "step", choices=["download", "report", "run", "export-powerbi", "check-sources"]
    )
    parser.add_argument(
        "--companies",
        type=Path,
        default=ROOT / "data" / "raw" / "active_companies_marche.csv",
        help="active companies file (semicolon-separated, wide by month)",
    )
    parser.add_argument(
        "--eurostat-dir",
        type=Path,
        default=ROOT / "data" / "raw",
        help="folder for the Eurostat and GISCO files",
    )
    parser.add_argument("--docs", type=Path, default=ROOT / "docs", help="output folder")
    parser.add_argument("--powerbi", type=Path, default=ROOT / "powerbi", help="Power BI folder")
    parser.add_argument("--holdout", type=int, default=24, help="test months for SARIMA")
    args = parser.parse_args(argv)

    if args.step == "export-powerbi":
        powerbi_export.build(args.companies, args.powerbi / "data", holdout=args.holdout)
        return 0
    if args.step == "check-sources":
        results = sources.check(args.powerbi / sources.MODEL_DEFINITION)
        print(sources.report(results))
        return 0 if all(r.ok for r in results) else 1
    if args.step in ("download", "run"):
        companies.download(args.companies)
        eurostat.download(args.eurostat_dir)
    if args.step in ("report", "run"):
        report.build(args.companies, args.eurostat_dir, args.docs, holdout=args.holdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`sources` is created in Task 4. Until then, create `src/marche_stats/sources.py` with only the constant, so the import works:

```python
"""Check the data sources of the Power BI semantic model."""

from __future__ import annotations

from pathlib import Path

MODEL_DEFINITION = Path("marche-regional-profile.SemanticModel") / "definition"
```

- [ ] **Step 4: Keep `powerbi/data/` tracked.** The `.gitignore` line `data/` matches every folder called `data`. Append to `.gitignore`:

```gitignore

# Files exported by marche-stats for the Power BI report are committed.
!powerbi/data/
```

Check: `git check-ignore -v powerbi/data/forecast.csv` prints nothing (exit code 1).

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_powerbi_export.py -v`
Expected: 4 PASS.

- [ ] **Step 6: Lint and commit**

```bash
ruff check src tests && ruff format --check src tests
git add src/marche_stats/cli.py src/marche_stats/sources.py tests/test_powerbi_export.py .gitignore
git commit -m "Add the export-powerbi CLI step and track powerbi/data"
```

---

### Task 4: `sources` module

**Files:**
- Modify: `src/marche_stats/sources.py` (replace the stub from Task 3)
- Test: `tests/test_sources.py`

- [ ] **Step 1: Write the failing tests** (`tests/test_sources.py`)

```python
from pathlib import Path

import pytest

from marche_stats import sources

EXPRESSIONS = """\
expression FocusRegion = "ITI3" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tqueryGroup: Parameters

expression PeerRegions = "ITI1,ITI2" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression ProvinceRegions = "ITI31,ITI32" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression Country = "IT" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression StartYear = 2009 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]

expression RepoRawBase = "https://raw.example/repo/main" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression CompaniesSourceUrl = "https://opendata.example/stock.csv" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
"""

TABLE = """\
table Population
\tpartition Population = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = fnEurostat(
\t\t\t\t        "demo_r_pjangrp3",
\t\t\t\t        "c[unit]=NR&c[sex]=T",
\t\t\t\t        {"EU", "NUTS2", "NUTS3"}
\t\t\t\t    ),
\t\t\t\t    Nuts = Csv.Document(Web.Contents("https://gisco-services.ec.europa.eu/nuts.csv")),
\t\t\t\t    Fc = Csv.Document(Web.Contents(RepoRawBase & "/powerbi/data/forecast.csv"))
\t\t\t\tin
\t\t\t\t    Source
"""

GISCO_OK = "CNTR_CODE,NUTS_ID\nIT,ITI3\nIT,ITI31\nIT,ITI32\n"
EUROSTAT_OK = "geo,TIME_PERIOD,OBS_VALUE\nITI3,2024,10\nITI3,2025,\n"
EUROSTAT_FAULT = (
    "<S:Fault><faultcode>150</faultcode><faultstring>INVALID_QUERY_DIMENSION_VALUE: "
    "The following values for dimension are not allowed: GEO=ITI31.</faultstring></S:Fault>"
)


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = ""):
        self.status_code = status_code
        self.text = text

    def close(self) -> None:
        pass


def fake_get(routes: dict[str, FakeResponse]):
    def get(url: str, **_kwargs):
        for key, response in routes.items():
            if key in url:
                return response
        return FakeResponse(200)

    return get


@pytest.fixture
def definition(tmp_path: Path) -> Path:
    (tmp_path / "tables").mkdir()
    (tmp_path / "expressions.tmdl").write_text(EXPRESSIONS, encoding="utf-8")
    (tmp_path / "tables" / "Population.tmdl").write_text(TABLE, encoding="utf-8")
    return tmp_path


def test_parameters_are_read_from_expressions(definition):
    assert sources.parameters(definition) == {
        "FocusRegion": "ITI3",
        "PeerRegions": "ITI1,ITI2",
        "ProvinceRegions": "ITI31,ITI32",
        "Country": "IT",
        "StartYear": "2009",
        "RepoRawBase": "https://raw.example/repo/main",
        "CompaniesSourceUrl": "https://opendata.example/stock.csv",
    }


def test_eurostat_calls_are_found_across_lines(definition):
    assert sources.eurostat_calls(definition) == [
        sources.EurostatCall(
            "Population", "demo_r_pjangrp3", "c[unit]=NR&c[sex]=T", ("EU", "NUTS2", "NUTS3")
        )
    ]


def test_eurostat_url_lists_geo_codes_by_level(definition):
    call = sources.eurostat_calls(definition)[0]
    url = sources.eurostat_url(call, sources.parameters(definition))
    assert url == (
        "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/"
        "demo_r_pjangrp3/1.0?c[geo]=EU27_2020,ITI3,ITI1,ITI2,ITI31,ITI32"
        "&c[unit]=NR&c[sex]=T&c[TIME_PERIOD]=ge:2009"
        "&format=csvdata&formatVersion=1.0&labels=id&compress=false"
    )


def test_check_passes_when_every_source_answers(definition):
    get = fake_get({"gisco": FakeResponse(200, GISCO_OK), "ESTAT": FakeResponse(200, EUROSTAT_OK)})
    results = sources.check(definition, get=get)
    assert [r.source for r in results] == [
        "GISCO NUTS codes",
        "ProvinceRegions matches GISCO",
        "Eurostat demo_r_pjangrp3 (Population)",
        "Chamber of Commerce archive",
        "Repository file /powerbi/data/forecast.csv",
    ]
    assert all(r.ok for r in results)
    assert "latest 2024" in results[2].detail


def test_check_reports_the_eurostat_fault_message(definition):
    get = fake_get(
        {"gisco": FakeResponse(200, GISCO_OK), "ESTAT": FakeResponse(400, EUROSTAT_FAULT)}
    )
    eurostat = [r for r in sources.check(definition, get=get) if r.source.startswith("Eurostat")]
    assert not eurostat[0].ok
    assert "HTTP 400" in eurostat[0].detail
    assert "GEO=ITI31" in eurostat[0].detail


def test_check_flags_provinces_that_differ_from_gisco(definition):
    gisco = GISCO_OK + "IT,ITI33\n"
    get = fake_get({"gisco": FakeResponse(200, gisco), "ESTAT": FakeResponse(200, EUROSTAT_OK)})
    provinces = next(
        r for r in sources.check(definition, get=get) if r.source.startswith("ProvinceRegions")
    )
    assert not provinces.ok
    assert "ITI31,ITI32,ITI33" in provinces.detail


def test_report_prints_one_line_per_result():
    text = sources.report(
        [
            sources.Result("A", True, "fine", "https://a"),
            sources.Result("B", False, "HTTP 404", "https://b"),
        ]
    )
    assert text.splitlines() == ["OK    A: fine", "FAIL  B: HTTP 404", "      https://b"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_sources.py -v`
Expected: FAIL with `AttributeError: module 'marche_stats.sources' has no attribute 'parameters'`

- [ ] **Step 3: Implement.** Replace `src/marche_stats/sources.py` with:

```python
"""Check the data sources of the Power BI semantic model.

The Power Query code in the model's TMDL files is the one description of what the report
downloads. This module reads it, rebuilds each request and runs it, so a source that
changes (a dataset that drops a year, a file that moves) shows up before the next refresh.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

MODEL_DEFINITION = Path("marche-regional-profile.SemanticModel") / "definition"
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT"
EUROSTAT_FORMAT = "format=csvdata&formatVersion=1.0&labels=id&compress=false"
TIMEOUT_SECONDS = 180

PARAMETER = re.compile(r'^expression (\w+) = (?:"([^"]*)"|(\d+)) meta \[IsParameterQuery=true', re.M)
EUROSTAT_CALL = re.compile(r'fnEurostat\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*\{([^}]*)\}\s*\)')
WEB_LITERAL = re.compile(r'Web\.Contents\(\s*"(https://[^"]+)"')
REPO_FILE = re.compile(r'RepoRawBase\s*&\s*"([^"]+)"')


@dataclass(frozen=True)
class EurostatCall:
    table: str
    dataset: str
    filters: str
    levels: tuple[str, ...]


@dataclass(frozen=True)
class Result:
    source: str
    ok: bool
    detail: str
    url: str


def parameters(definition: Path) -> dict[str, str]:
    """Power Query parameters, as text, from expressions.tmdl."""
    text = (definition / "expressions.tmdl").read_text(encoding="utf-8")
    return {m[1]: m[2] if m[2] is not None else m[3] for m in PARAMETER.finditer(text)}


def _tables(definition: Path) -> dict[str, str]:
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((definition / "tables").glob("*.tmdl"))
    }


def eurostat_calls(definition: Path) -> list[EurostatCall]:
    """Every fnEurostat(dataset, filters, levels) call in the model's tables."""
    calls = []
    for table, text in _tables(definition).items():
        for m in EUROSTAT_CALL.finditer(text):
            levels = tuple(re.findall(r'"([^"]+)"', m[3]))
            calls.append(EurostatCall(table, m[1], m[2], levels))
    return calls


def geo_codes(params: dict[str, str], levels: tuple[str, ...]) -> list[str]:
    """Geo codes requested for each level, the same rule as fnEurostat in Power Query."""
    by_level = {
        "EU": ["EU27_2020"],
        "Country": [params["Country"]],
        "NUTS2": [params["FocusRegion"], *params["PeerRegions"].split(",")],
        "NUTS3": params["ProvinceRegions"].split(","),
    }
    return [code for level in levels for code in by_level[level]]


def eurostat_url(call: EurostatCall, params: dict[str, str]) -> str:
    parts = [
        f"c[geo]={','.join(geo_codes(params, call.levels))}",
        call.filters,
        f"c[TIME_PERIOD]=ge:{params['StartYear']}",
        EUROSTAT_FORMAT,
    ]
    return f"{EUROSTAT_BASE}/{call.dataset}/1.0?{'&'.join(p for p in parts if p)}"


def check_eurostat(call: EurostatCall, url: str, get: Callable) -> Result:
    name = f"Eurostat {call.dataset} ({call.table})"
    try:
        response = get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return Result(name, False, str(exc), url)
    if response.status_code != 200:
        fault = re.search(r"<faultstring>(.*?)</faultstring>", response.text, re.S)
        message = fault.group(1) if fault else response.text[:200]
        return Result(name, False, f"HTTP {response.status_code}: {message}", url)
    rows = [r for r in csv.DictReader(io.StringIO(response.text)) if r.get("OBS_VALUE")]
    if not rows:
        return Result(name, False, "no observations", url)
    latest = max(r["TIME_PERIOD"] for r in rows)
    return Result(name, True, f"{len(rows):,} observations, latest {latest}", url)


def check_file(name: str, url: str, get: Callable) -> Result:
    try:
        response = get(url, timeout=TIMEOUT_SECONDS, stream=True)
    except requests.RequestException as exc:
        return Result(name, False, str(exc), url)
    response.close()
    return Result(name, response.status_code == 200, f"HTTP {response.status_code}", url)


def check_provinces(params: dict[str, str], gisco_csv: str) -> Result:
    """ProvinceRegions must list exactly the NUTS 3 children of FocusRegion."""
    focus = params["FocusRegion"]
    children = sorted(
        r["NUTS_ID"]
        for r in csv.DictReader(io.StringIO(gisco_csv))
        if r["NUTS_ID"].startswith(focus) and len(r["NUTS_ID"]) == len(focus) + 1
    )
    configured = sorted(params["ProvinceRegions"].split(","))
    detail = f"GISCO: {','.join(children)}; parameter: {','.join(configured)}"
    return Result("ProvinceRegions matches GISCO", children == configured, detail, "")


def check(definition: Path, get: Callable = requests.get) -> list[Result]:
    """Request every source the model uses and report each one."""
    params = parameters(definition)
    text = "\n".join(_tables(definition).values())
    results = []
    for url in sorted(set(WEB_LITERAL.findall(text))):
        if "gisco-services" not in url:
            results.append(check_file(url, url, get))
            continue
        try:
            response = get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            results.append(Result("GISCO NUTS codes", False, str(exc), url))
            continue
        ok = response.status_code == 200
        results.append(Result("GISCO NUTS codes", ok, f"HTTP {response.status_code}", url))
        if ok:
            results.append(check_provinces(params, response.text))
    for call in eurostat_calls(definition):
        results.append(check_eurostat(call, eurostat_url(call, params), get))
    results.append(check_file("Chamber of Commerce archive", params["CompaniesSourceUrl"], get))
    for relative in sorted(set(REPO_FILE.findall(text))):
        url = params["RepoRawBase"] + relative
        results.append(check_file(f"Repository file {relative}", url, get))
    return results


def report(results: list[Result]) -> str:
    lines = []
    for r in results:
        lines.append(f"{'OK  ' if r.ok else 'FAIL'}  {r.source}: {r.detail}")
        if not r.ok and r.url:
            lines.append(f"      {r.url}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_sources.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Lint and commit**

```bash
ruff check src tests && ruff format --check src tests
git add src/marche_stats/sources.py tests/test_sources.py
git commit -m "Add the sources module: read the model's TMDL and request every source"
```

---

### Task 5: CLI step `check-sources` and weekly workflow

The CLI branch already exists (Task 3). This task tests it and schedules it.

**Files:**
- Test: `tests/test_sources.py`
- Create: `.github/workflows/check-sources.yml`

- [ ] **Step 1: Write the test** (append to `tests/test_sources.py`, and add `from marche_stats import cli` to the imports at the top)

```python
def test_cli_check_sources_fails_when_a_source_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        sources, "check", lambda _definition: [sources.Result("X", False, "HTTP 404", "u")]
    )
    assert cli.main(["check-sources", "--powerbi", str(tmp_path)]) == 1
    assert "FAIL  X: HTTP 404" in capsys.readouterr().out
```

- [ ] **Step 2: Run it**

Run: `pytest tests/test_sources.py -v`
Expected: 8 PASS (the CLI code from Task 3 already handles the step).

- [ ] **Step 3: Create `.github/workflows/check-sources.yml`**

```yaml
name: check-sources

# Requests every data source of the Power BI model (Eurostat, GISCO, Chamber of Commerce,
# files exported to powerbi/data/), so a changed source is found before the next refresh.
on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - name: Install
        run: pip install -r requirements.txt -e .
      - name: Check sources
        run: marche-stats check-sources
```

- [ ] **Step 4: Lint and commit**

```bash
ruff check src tests && ruff format --check src tests
git add tests/test_sources.py .github/workflows/check-sources.yml
git commit -m "Run check-sources weekly in GitHub Actions"
```

---

### Task 6: Project skeleton and static model tests

**Files:**
- Create: `powerbi/marche-regional-profile.pbip`
- Create: `powerbi/marche-regional-profile.SemanticModel/.platform`, `definition.pbism`, `definition/database.tmdl`, `definition/model.tmdl`
- Create: `powerbi/marche-regional-profile.Report/` (copied, pages replaced)
- Test: `tests/test_powerbi_model.py`

- [ ] **Step 1: Write the static tests** (`tests/test_powerbi_model.py`)

```python
"""Static checks of the Power BI project: names and references that Desktop would reject.

DAX and Power Query cannot run outside Power BI Desktop; the refresh is the real test.
These checks catch a renamed column or measure, a missing table file or a space-indented
TMDL line before the project is opened.
"""

import json
import re
from pathlib import Path

import pytest

from marche_stats import sources

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "powerbi" / sources.MODEL_DEFINITION
REPORT = ROOT / "powerbi" / "marche-regional-profile.Report" / "definition"
NAME = r"('[^']+'|[^\s=.]+)"


def _name(raw: str) -> str:
    raw = raw.strip()
    return raw[1:-1] if raw.startswith("'") else raw


def model_tables() -> dict[str, dict[str, set[str]]]:
    tables = {}
    for path in sorted((MODEL / "tables").glob("*.tmdl")):
        text = path.read_text(encoding="utf-8")
        name = _name(re.search(r"^table (.+)$", text, re.M).group(1))
        tables[name] = {
            "columns": {_name(m) for m in re.findall(rf"^\tcolumn {NAME}", text, re.M)},
            "measures": {_name(m) for m in re.findall(rf"^\tmeasure {NAME}", text, re.M)},
        }
    return tables


def test_model_references_every_table_file():
    text = (MODEL / "model.tmdl").read_text(encoding="utf-8")
    refs = {_name(m) for m in re.findall(r"^ref table (.+)$", text, re.M)}
    assert refs == set(model_tables())


def test_tmdl_lines_are_tab_indented():
    for path in MODEL.rglob("*.tmdl"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not line.startswith(" "), f"{path.name}:{number} starts with a space"


def test_relationships_use_existing_columns():
    path = MODEL / "relationships.tmdl"
    if not path.exists():
        pytest.skip("no relationships yet")
    tables = model_tables()
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"^\t(?:from|to)Column: (.+)$", text, re.M):
        table, column = re.match(rf"{NAME}\.(.+)$", ref.strip()).groups()
        assert _name(column) in tables[_name(table)]["columns"], ref


def test_measure_references_exist():
    tables = model_tables()
    if "_Measures" not in tables:
        pytest.skip("no measures yet")
    measures = tables["_Measures"]["measures"]
    text = "\n".join(p.read_text(encoding="utf-8") for p in (MODEL / "tables").glob("*.tmdl"))
    named = re.findall(r"NAMEOF\s*\(\s*'_Measures'\[([^\]]+)\]", text)
    selected = [
        m
        for args in re.findall(r"ISSELECTEDMEASURE\s*\(((?:[^()]|\([^()]*\))*)\)", text)
        for m in re.findall(r"\[([^\]]+)\]", args)
    ]
    for measure in named + selected:
        assert measure in measures, measure


def _field_refs(node):
    if isinstance(node, dict):
        source = node.get("Expression", {}).get("SourceRef", {})
        if "Entity" in source and "Property" in node:
            yield source["Entity"], node["Property"]
        for value in node.values():
            yield from _field_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _field_refs(value)


def test_report_fields_exist_in_model():
    tables = model_tables()
    for path in REPORT.glob("pages/*/visuals/*/visual.json"):
        visual = json.loads(path.read_text(encoding="utf-8"))
        for entity, prop in _field_refs(visual):
            assert entity in tables, f"{path.parent.name}: table {entity}"
            fields = tables[entity]["columns"] | tables[entity]["measures"]
            assert prop in fields, f"{path.parent.name}: {entity}[{prop}]"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_powerbi_model.py -v`
Expected: FAIL with `FileNotFoundError` on `model.tmdl`.

- [ ] **Step 3: Create the project files.**

`powerbi/marche-regional-profile.pbip`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [
    {
      "report": {
        "path": "marche-regional-profile.Report"
      }
    }
  ],
  "settings": {
    "enableAutoRecovery": true
  }
}
```

`powerbi/marche-regional-profile.SemanticModel/.platform`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "SemanticModel",
    "displayName": "marche-regional-profile"
  },
  "config": {
    "version": "2.0",
    "logicalId": "a3b9e2d4-5c61-4f07-8e1b-2d7c9f4a6b35"
  }
}
```

`powerbi/marche-regional-profile.SemanticModel/definition.pbism`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  "version": "4.2",
  "settings": {}
}
```

`powerbi/marche-regional-profile.SemanticModel/definition/database.tmdl`:

```tmdl
database
	compatibilityLevel: 1606
```

`powerbi/marche-regional-profile.SemanticModel/definition/model.tmdl` (later tasks append `ref table` lines at the end):

```tmdl
model Model
	culture: en-US
	defaultPowerBIDataSourceVersion: powerBI_V3
	discourageImplicitMeasures
	sourceQueryCulture: en-US
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

queryGroup Parameters

	annotation PBI_QueryGroupOrder = 0

queryGroup Functions

	annotation PBI_QueryGroupOrder = 1

annotation __PBI_TimeIntelligenceEnabled = 0

annotation PBI_ProTooling = ["DevMode"]

```

Create the empty folder `powerbi/marche-regional-profile.SemanticModel/definition/tables/` (it fills in Task 7).

- [ ] **Step 4: Copy the report and drop its pages.** The old report folder brings the base theme, the built-in theme and the Italy shape map, which Phase B may reuse.

```bash
cp -r powerbi/marche-regionali-2025.Report powerbi/marche-regional-profile.Report
rm -r powerbi/marche-regional-profile.Report/.pbi
rm -r powerbi/marche-regional-profile.Report/definition/bookmarks
rm -r powerbi/marche-regional-profile.Report/definition/pages
mkdir -p powerbi/marche-regional-profile.Report/definition/pages
```

Replace `powerbi/marche-regional-profile.Report/definition.pbir` with:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byPath": {
      "path": "../marche-regional-profile.SemanticModel"
    }
  }
}
```

Replace `powerbi/marche-regional-profile.Report/.platform` with:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "Report",
    "displayName": "marche-regional-profile"
  },
  "config": {
    "version": "2.0",
    "logicalId": "0f6d1c2e-7a43-4b8e-9d25-6c1a3e5b7f90"
  }
}
```

The page list is written in Task 14.

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_powerbi_model.py -v`
Expected: `test_model_references_every_table_file` and `test_tmdl_lines_are_tab_indented` PASS, the relationship and measure tests SKIP, `test_report_fields_exist_in_model` PASS (no visuals yet).

- [ ] **Step 6: Commit**

```bash
git add powerbi/marche-regional-profile.pbip powerbi/marche-regional-profile.SemanticModel powerbi/marche-regional-profile.Report tests/test_powerbi_model.py
git commit -m "Start the marche-regional-profile Power BI project with static model tests"
```

---

### Task 7: Parameters, `fnEurostat`, `Geo` and `Calendar`

**Files:**
- Create: `powerbi/marche-regional-profile.SemanticModel/definition/expressions.tmdl`
- Create: `.../definition/tables/Geo.tmdl`, `.../definition/tables/Calendar.tmdl`
- Modify: `.../definition/model.tmdl` (append `ref table` lines)
- Test: `tests/test_sources.py` (real-model parameters)

- [ ] **Step 1: Write the failing test** (append to `tests/test_sources.py`)

```python
REAL_MODEL = Path(__file__).resolve().parents[1] / "powerbi" / sources.MODEL_DEFINITION


def test_real_model_parameters_are_complete():
    params = sources.parameters(REAL_MODEL)
    assert params["FocusRegion"] == "ITI3"
    assert params["ProvinceRegions"] == "ITI31,ITI32,ITI33,ITI34,ITI35"
    assert params["StartYear"] == "2009"
    assert set(params) == {
        "FocusRegion",
        "PeerRegions",
        "ProvinceRegions",
        "Country",
        "StartYear",
        "RepoRawBase",
        "CompaniesSourceUrl",
    }
```

Run: `pytest tests/test_sources.py::test_real_model_parameters_are_complete -v`
Expected: FAIL with `FileNotFoundError` on `expressions.tmdl`.

- [ ] **Step 2: Create `expressions.tmdl`**

```tmdl
/// NUTS 2 region profiled by the report (ITI3 = Marche).
expression FocusRegion = "ITI3" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	queryGroup: Parameters

	annotation PBI_ResultType = Text

/// NUTS 2 regions compared with the focus region: Toscana, Umbria, Emilia-Romagna, Lazio, Abruzzo.
expression PeerRegions = "ITI1,ITI2,ITH5,ITI4,ITF1" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	queryGroup: Parameters

	annotation PBI_ResultType = Text

/// NUTS 3 provinces of the focus region. marche-stats check-sources verifies them against GISCO.
expression ProvinceRegions = "ITI31,ITI32,ITI33,ITI34,ITI35" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	queryGroup: Parameters

	annotation PBI_ResultType = Text

/// Country used as national benchmark.
expression Country = "IT" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	queryGroup: Parameters

	annotation PBI_ResultType = Text

/// First year requested from Eurostat and first year of the Calendar table.
expression StartYear = 2009 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]
	queryGroup: Parameters

	annotation PBI_ResultType = Number

/// Base URL of the files that marche-stats export-powerbi writes to powerbi/data/.
expression RepoRawBase = "https://raw.githubusercontent.com/simones99/marche-regional-stats/main" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	queryGroup: Parameters

	annotation PBI_ResultType = Text

/// Chamber of Commerce archive of active companies (ATECO 2007, closed series).
expression CompaniesSourceUrl = "https://opendata.marche.camcom.it/data/Stock-Imprese-Attive-Marche-2009-2025.csv" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	queryGroup: Parameters

	annotation PBI_ResultType = Text

/// Downloads one Eurostat dataset (SDMX 3.0, CSV with codes) for the geo levels given:
/// "EU", "Country", "NUTS2" (focus and peers), "NUTS3" (provinces). Filters are
/// "name=values" pairs joined by "&". A failed request stops the refresh with the
/// dataset name and Eurostat's own message.
expression fnEurostat =
		(dataset as text, filters as text, levels as list) as table =>
		let
		    GeoCodes = List.Combine({
		        if List.Contains(levels, "EU") then {"EU27_2020"} else {},
		        if List.Contains(levels, "Country") then {Country} else {},
		        if List.Contains(levels, "NUTS2") then {FocusRegion} & Text.Split(PeerRegions, ",") else {},
		        if List.Contains(levels, "NUTS3") then Text.Split(ProvinceRegions, ",") else {}
		    }),
		    FilterPairs = List.Select(Text.Split(filters, "&"), each _ <> ""),
		    FilterQuery = Record.FromList(
		        List.Transform(FilterPairs, each Text.AfterDelimiter(_, "=")),
		        List.Transform(FilterPairs, each Text.BeforeDelimiter(_, "="))
		    ),
		    Query = Record.Combine({
		        [#"c[geo]" = Text.Combine(GeoCodes, ",")],
		        FilterQuery,
		        [
		            #"c[TIME_PERIOD]" = "ge:" & Text.From(StartYear),
		            format = "csvdata",
		            formatVersion = "1.0",
		            labels = "id",
		            compress = "false"
		        ]
		    }),
		    Response = Web.Contents(
		        "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/",
		        [RelativePath = dataset & "/1.0", Query = Query, ManualStatusHandling = {400, 404, 413, 500, 503}]
		    ),
		    Status = Value.Metadata(Response)[Response.Status],
		    Body = Text.FromBinary(Response, TextEncoding.Utf8),
		    Message =
		        if Text.Contains(Body, "<faultstring>")
		        then Text.BeforeDelimiter(Text.AfterDelimiter(Body, "<faultstring>"), "</faultstring>")
		        else Text.Start(Body, 300),
		    Checked =
		        if Status = 200 then Body
		        else error Error.Record(
		            "Eurostat request failed",
		            "HTTP " & Text.From(Status) & " for " & dataset & ": " & Message,
		            [Dataset = dataset, Query = Query]
		        ),
		    Parsed = Csv.Document(Checked, [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
		    Promoted = Table.PromoteHeaders(Parsed, [PromoteAllScalars = true]),
		    Rows =
		        if Table.IsEmpty(Promoted)
		        then error Error.Record("Eurostat returned no rows", dataset)
		        else Promoted
		in
		    Rows
	queryGroup: Functions

	annotation PBI_ResultType = Function
```

- [ ] **Step 3: Create `tables/Geo.tmdl`**

```tmdl
/// Areas of the report: EU, country, focus region, peer regions and provinces, keyed on NUTS codes.
table Geo

	column Code
		dataType: string
		isKey
		summarizeBy: none
		sourceColumn: Code

	column Name
		dataType: string
		summarizeBy: none
		sourceColumn: Name
		sortByColumn: SortOrder

	column Level
		dataType: string
		summarizeBy: none
		sourceColumn: Level

	column ParentCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: ParentCode

	column Role
		dataType: string
		summarizeBy: none
		sourceColumn: Role

	column SortOrder
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: SortOrder

	partition Geo = m
		mode: import
		source =
				let
				    Source = Csv.Document(
				        Web.Contents("https://gisco-services.ec.europa.eu/distribution/v2/nuts/csv/NUTS_AT_2024.csv"),
				        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
				    ),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
				    Peers = Text.Split(PeerRegions, ","),
				    Provinces = Text.Split(ProvinceRegions, ","),
				    Wanted = List.Combine({{FocusRegion}, Peers, Provinces}),
				    Selected = Table.SelectRows(Promoted, each List.Contains(Wanted, [NUTS_ID])),
				    Renamed = Table.RenameColumns(
				        Table.SelectColumns(Selected, {"NUTS_ID", "NAME_LATN"}),
				        {{"NUTS_ID", "Code"}, {"NAME_LATN", "Name"}}
				    ),
				    WithLevel = Table.AddColumn(Renamed, "Level", each "NUTS" & Text.From(Text.Length([Code]) - 2), type text),
				    WithParent = Table.AddColumn(WithLevel, "ParentCode", each if Text.Length([Code]) = 5 then Text.Start([Code], 4) else Country, type text),
				    WithRole = Table.AddColumn(WithParent, "Role", each if [Code] = FocusRegion then "Focus" else if List.Contains(Peers, [Code]) then "Peer" else "Province", type text),
				    Benchmarks = #table(
				        type table [Code = text, Name = text, Level = text, ParentCode = text, Role = text],
				        {
				            {"EU27_2020", "European Union (27)", "EU", "", "EU"},
				            {Country, if Country = "IT" then "Italy" else Country, "Country", "EU27_2020", "Country"}
				        }
				    ),
				    Combined = Table.Combine({WithRole, Benchmarks}),
				    Missing = List.Difference(Wanted, Combined[Code]),
				    Checked =
				        if List.IsEmpty(Missing) then Combined
				        else error Error.Record("NUTS codes not found in GISCO", Text.Combine(Missing, ", ")),
				    RoleRank = Table.AddColumn(Checked, "RoleRank", each List.PositionOf({"Focus", "Peer", "Country", "EU", "Province"}, [Role]), Int64.Type),
				    Sorted = Table.Sort(RoleRank, {{"RoleRank", Order.Ascending}, {"Name", Order.Ascending}}),
				    Indexed = Table.AddIndexColumn(Sorted, "SortOrder", 1, 1, Int64.Type),
				    Result = Table.RemoveColumns(Indexed, {"RoleRank"})
				in
				    Result

	annotation PBI_ResultType = Table
```

- [ ] **Step 4: Create `tables/Calendar.tmdl`**

```tmdl
/// Daily calendar from 1 January of StartYear to the end of the current year. Annual
/// Eurostat facts join on 1 January, monthly facts on the month-end date.
table Calendar
	dataCategory: Time

	column Date
		dataType: dateTime
		isKey
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Year
		dataType: int64
		formatString: 0
		summarizeBy: none
		sourceColumn: Year

	column Quarter
		dataType: string
		summarizeBy: none
		sourceColumn: Quarter

	column MonthNumber
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: MonthNumber

	column MonthName
		dataType: string
		summarizeBy: none
		sourceColumn: MonthName
		sortByColumn: MonthNumber

	column YearMonth
		dataType: int64
		formatString: 0
		summarizeBy: none
		sourceColumn: YearMonth

	column MonthEnd
		dataType: dateTime
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: MonthEnd

	partition Calendar = m
		mode: import
		source =
				let
				    Start = #date(StartYear, 1, 1),
				    End = #date(Date.Year(DateTime.LocalNow()), 12, 31),
				    Dates = List.Dates(Start, Duration.Days(End - Start) + 1, #duration(1, 0, 0, 0)),
				    Base = Table.FromList(Dates, Splitter.SplitByNothing(), type table [Date = date]),
				    WithYear = Table.AddColumn(Base, "Year", each Date.Year([Date]), Int64.Type),
				    WithQuarter = Table.AddColumn(WithYear, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
				    WithMonth = Table.AddColumn(WithQuarter, "MonthNumber", each Date.Month([Date]), Int64.Type),
				    WithMonthName = Table.AddColumn(WithMonth, "MonthName", each Date.ToText([Date], [Format = "MMM", Culture = "en-US"]), type text),
				    WithYearMonth = Table.AddColumn(WithMonthName, "YearMonth", each Date.Year([Date]) * 100 + Date.Month([Date]), Int64.Type),
				    WithMonthEnd = Table.AddColumn(WithYearMonth, "MonthEnd", each Date.EndOfMonth([Date]), type date)
				in
				    WithMonthEnd

	annotation PBI_ResultType = Table
```

- [ ] **Step 5: Reference the tables.** Append to `model.tmdl`:

```tmdl
ref table Geo
ref table Calendar
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_sources.py tests/test_powerbi_model.py -v`
Expected: PASS (relationship and measure tests still SKIP).

- [ ] **Step 7: Commit**

```bash
git add powerbi/marche-regional-profile.SemanticModel tests/test_sources.py
git commit -m "Add parameters, fnEurostat, Geo and Calendar to the semantic model"
```

---

### Task 8: Static dimensions and the measure table

**Files:**
- Create: `.../definition/tables/Sex.tmdl`, `AgeGroup.tmdl`, `ISCED.tmdl`, `Sector.tmdl`, `_Measures.tmdl`
- Modify: `.../definition/model.tmdl`

- [ ] **Step 1: Create `tables/Sex.tmdl`**

```tmdl
/// Eurostat sex codes.
table Sex

	column Code
		dataType: string
		isKey
		summarizeBy: none
		sourceColumn: Code

	column Name
		dataType: string
		summarizeBy: none
		sourceColumn: Name
		sortByColumn: SortOrder

	column SortOrder
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: SortOrder

	partition Sex = m
		mode: import
		source =
				#table(
				    type table [Code = text, Name = text, SortOrder = Int64.Type],
				    {{"T", "Total", 1}, {"M", "Male", 2}, {"F", "Female", 3}}
				)

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Create `tables/AgeGroup.tmdl`**

```tmdl
/// Eurostat five-year age groups (Y_LT5 to Y_GE90), the total and unknown age.
table AgeGroup

	column Code
		dataType: string
		isKey
		summarizeBy: none
		sourceColumn: Code

	column Name
		dataType: string
		summarizeBy: none
		sourceColumn: Name
		sortByColumn: SortOrder

	column SortOrder
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: SortOrder

	column BroadGroup
		dataType: string
		summarizeBy: none
		sourceColumn: BroadGroup

	column Is80Plus
		dataType: boolean
		formatString: """TRUE"";""TRUE"";""FALSE"""
		summarizeBy: none
		sourceColumn: Is80Plus

	partition AgeGroup = m
		mode: import
		source =
				let
				    Bands = List.Transform(
				        {0..18},
				        (i) =>
				            let
				                Lower = i * 5,
				                Code = if i = 0 then "Y_LT5" else if i = 18 then "Y_GE90" else "Y" & Text.From(Lower) & "-" & Text.From(Lower + 4),
				                Name = if i = 18 then "90+" else Text.From(Lower) & "-" & Text.From(Lower + 4),
				                Broad = if Lower < 15 then "0-14" else if Lower < 65 then "15-64" else "65+"
				            in
				                {Code, Name, i + 1, Broad, Lower >= 80}
				    ),
				    Rows = {{"TOTAL", "Total", 0, "Total", false}} & Bands & {{"UNK", "Unknown", 99, "Unknown", false}}
				in
				    #table(type table [Code = text, Name = text, SortOrder = Int64.Type, BroadGroup = text, Is80Plus = logical], Rows)

	annotation PBI_ResultType = Table
```

- [ ] **Step 3: Create `tables/ISCED.tmdl`**

```tmdl
/// ISCED 2011 education levels used by educ_uoe_enra11. ED0-8 is the total.
table ISCED

	column Code
		dataType: string
		isKey
		summarizeBy: none
		sourceColumn: Code

	column Name
		dataType: string
		summarizeBy: none
		sourceColumn: Name
		sortByColumn: SortOrder

	column SortOrder
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: SortOrder

	column Group
		dataType: string
		summarizeBy: none
		sourceColumn: Group

	column IsTotal
		dataType: boolean
		isHidden
		formatString: """TRUE"";""TRUE"";""FALSE"""
		summarizeBy: none
		sourceColumn: IsTotal

	partition ISCED = m
		mode: import
		source =
				#table(
				    type table [Code = text, Name = text, SortOrder = Int64.Type, Group = text, IsTotal = logical],
				    {
				        {"ED0", "Early childhood education", 0, "ISCED 0-3", false},
				        {"ED1", "Primary education", 1, "ISCED 0-3", false},
				        {"ED2", "Lower secondary education", 2, "ISCED 0-3", false},
				        {"ED3", "Upper secondary education", 3, "ISCED 0-3", false},
				        {"ED4", "Post-secondary non-tertiary education", 4, "ISCED 4", false},
				        {"ED5", "Short-cycle tertiary education", 5, "ISCED 5-8", false},
				        {"ED6", "Bachelor's or equivalent", 6, "ISCED 5-8", false},
				        {"ED7", "Master's or equivalent", 7, "ISCED 5-8", false},
				        {"ED8", "Doctoral or equivalent", 8, "ISCED 5-8", false},
				        {"ED0-8", "All levels", 9, "All", true}
				    }
				)

	annotation PBI_ResultType = Table
```

- [ ] **Step 4: Create `tables/Sector.tmdl`**

```tmdl
/// ATECO 2007 sections (NACE Rev. 2) in the Chamber of Commerce file. X = not classified.
table Sector

	column Code
		dataType: string
		isKey
		summarizeBy: none
		sourceColumn: Code

	column Name
		dataType: string
		summarizeBy: none
		sourceColumn: Name

	partition Sector = m
		mode: import
		source =
				#table(
				    type table [Code = text, Name = text],
				    {
				        {"A", "Agriculture, forestry and fishing"},
				        {"B", "Mining and quarrying"},
				        {"C", "Manufacturing"},
				        {"D", "Electricity, gas, steam and air conditioning supply"},
				        {"E", "Water supply, sewerage and waste management"},
				        {"F", "Construction"},
				        {"G", "Wholesale and retail trade, repair of motor vehicles"},
				        {"H", "Transportation and storage"},
				        {"I", "Accommodation and food service activities"},
				        {"J", "Information and communication"},
				        {"K", "Financial and insurance activities"},
				        {"L", "Real estate activities"},
				        {"M", "Professional, scientific and technical activities"},
				        {"N", "Administrative and support service activities"},
				        {"O", "Public administration and defence, compulsory social security"},
				        {"P", "Education"},
				        {"Q", "Human health and social work activities"},
				        {"R", "Arts, entertainment and recreation"},
				        {"S", "Other service activities"},
				        {"T", "Activities of households as employers"},
				        {"X", "Not classified"}
				    }
				)

	annotation PBI_ResultType = Table
```

- [ ] **Step 5: Create `tables/_Measures.tmdl`** (measures are added in Task 12)

```tmdl
/// All measures of the report, in display folders by page.
table _Measures

	column Placeholder
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: Placeholder

	partition _Measures = m
		mode: import
		source =
				#table(type table [Placeholder = text], {})

	annotation PBI_ResultType = Table
```

- [ ] **Step 6: Reference the tables.** Append to `model.tmdl`:

```tmdl
ref table Sex
ref table AgeGroup
ref table ISCED
ref table Sector
ref table _Measures
```

- [ ] **Step 7: Run the tests**

Run: `pytest tests/test_powerbi_model.py -v`
Expected: PASS; `test_measure_references_exist` now runs and passes (no references yet).

- [ ] **Step 8: Commit**

```bash
git add powerbi/marche-regional-profile.SemanticModel
git commit -m "Add the static dimensions and the measure table"
```

---

### Task 9: Eurostat fact tables

**Files:**
- Create: `.../definition/tables/Population.tmdl`, `Deaths.tmdl`, `GDP.tmdl`, `Unemployment.tmdl`, `Enrolment.tmdl`
- Modify: `.../definition/model.tmdl`
- Test: `tests/test_sources.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_sources.py`)

```python
def test_real_model_eurostat_calls():
    calls = {(c.table, c.dataset): c.levels for c in sources.eurostat_calls(REAL_MODEL)}
    assert calls == {
        ("Deaths", "demo_r_magec3"): ("EU", "Country", "NUTS2", "NUTS3"),
        ("Enrolment", "educ_uoe_enra11"): ("EU", "Country", "NUTS2"),
        ("GDP", "nama_10r_2gdp"): ("EU", "Country", "NUTS2"),
        ("GDP", "nama_10r_3gdp"): ("NUTS3",),
        ("Population", "demo_r_pjangrp3"): ("EU", "Country", "NUTS2", "NUTS3"),
        ("Unemployment", "lfst_r_lfu3rt"): ("EU", "Country", "NUTS2"),
    }
```

Run: `pytest tests/test_sources.py::test_real_model_eurostat_calls -v`
Expected: FAIL (the dictionary is empty).

- [ ] **Step 2: Create `tables/Population.tmdl`**

```tmdl
/// Population on 1 January by sex and five-year age group (Eurostat demo_r_pjangrp3).
table Population

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column SexCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: SexCode

	column AgeCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: AgeCode

	column Date
		dataType: dateTime
		isHidden
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Residents
		dataType: int64
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Residents

	column Flag
		dataType: string
		summarizeBy: none
		sourceColumn: Flag

	partition Population = m
		mode: import
		source =
				let
				    Source = fnEurostat(
				        "demo_r_pjangrp3",
				        "c[unit]=NR&c[sex]=T,M,F&c[age]=TOTAL,Y_LT5,Y5-9,Y10-14,Y15-19,Y20-24,Y25-29,Y30-34,Y35-39,Y40-44,Y45-49,Y50-54,Y55-59,Y60-64,Y65-69,Y70-74,Y75-79,Y80-84,Y85-89,Y_GE90,UNK",
				        {"EU", "Country", "NUTS2", "NUTS3"}
				    ),
				    Selected = Table.SelectColumns(Source, {"geo", "sex", "age", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"}),
				    NonEmpty = Table.SelectRows(Selected, each [OBS_VALUE] <> ""),
				    WithDate = Table.AddColumn(NonEmpty, "Date", each #date(Number.FromText([TIME_PERIOD]), 1, 1), type date),
				    Renamed = Table.RenameColumns(
				        Table.RemoveColumns(WithDate, {"TIME_PERIOD"}),
				        {{"geo", "GeoCode"}, {"sex", "SexCode"}, {"age", "AgeCode"}, {"OBS_VALUE", "Residents"}, {"OBS_FLAG", "Flag"}}
				    ),
				    Typed = Table.TransformColumnTypes(
				        Renamed,
				        {{"GeoCode", type text}, {"SexCode", type text}, {"AgeCode", type text}, {"Residents", Int64.Type}, {"Flag", type text}},
				        "en-US"
				    )
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 3: Create `tables/Deaths.tmdl`**

```tmdl
/// Deaths in the year by sex and five-year age group (Eurostat demo_r_magec3).
table Deaths

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column SexCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: SexCode

	column AgeCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: AgeCode

	column Date
		dataType: dateTime
		isHidden
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Count
		dataType: int64
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Count

	column Flag
		dataType: string
		summarizeBy: none
		sourceColumn: Flag

	partition Deaths = m
		mode: import
		source =
				let
				    Source = fnEurostat(
				        "demo_r_magec3",
				        "c[unit]=NR&c[sex]=T,M,F&c[age]=TOTAL,Y_LT5,Y5-9,Y10-14,Y15-19,Y20-24,Y25-29,Y30-34,Y35-39,Y40-44,Y45-49,Y50-54,Y55-59,Y60-64,Y65-69,Y70-74,Y75-79,Y80-84,Y85-89,Y_GE90,UNK",
				        {"EU", "Country", "NUTS2", "NUTS3"}
				    ),
				    Selected = Table.SelectColumns(Source, {"geo", "sex", "age", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"}),
				    NonEmpty = Table.SelectRows(Selected, each [OBS_VALUE] <> ""),
				    WithDate = Table.AddColumn(NonEmpty, "Date", each #date(Number.FromText([TIME_PERIOD]), 1, 1), type date),
				    Renamed = Table.RenameColumns(
				        Table.RemoveColumns(WithDate, {"TIME_PERIOD"}),
				        {{"geo", "GeoCode"}, {"sex", "SexCode"}, {"age", "AgeCode"}, {"OBS_VALUE", "Count"}, {"OBS_FLAG", "Flag"}}
				    ),
				    Typed = Table.TransformColumnTypes(
				        Renamed,
				        {{"GeoCode", type text}, {"SexCode", type text}, {"AgeCode", type text}, {"Count", Int64.Type}, {"Flag", type text}},
				        "en-US"
				    )
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 4: Create `tables/GDP.tmdl`**

```tmdl
/// GDP per inhabitant as published by Eurostat: EUR_HAB (euro) and PPS_HAB_EU27_2020
/// (purchasing power standard, EU = 100). nama_10r_2gdp for EU, country and regions,
/// nama_10r_3gdp for provinces.
table GDP

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column UnitCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: UnitCode

	column Date
		dataType: dateTime
		isHidden
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Value
		dataType: double
		isHidden
		formatString: #,0.0
		summarizeBy: sum
		sourceColumn: Value

	column Flag
		dataType: string
		summarizeBy: none
		sourceColumn: Flag

	partition GDP = m
		mode: import
		source =
				let
				    Regions = fnEurostat("nama_10r_2gdp", "c[unit]=EUR_HAB,PPS_HAB_EU27_2020", {"EU", "Country", "NUTS2"}),
				    Provinces = fnEurostat("nama_10r_3gdp", "c[unit]=EUR_HAB,PPS_HAB_EU27_2020", {"NUTS3"}),
				    Combined = Table.Combine({
				        Table.SelectColumns(Regions, {"geo", "unit", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"}),
				        Table.SelectColumns(Provinces, {"geo", "unit", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"})
				    }),
				    NonEmpty = Table.SelectRows(Combined, each [OBS_VALUE] <> ""),
				    WithDate = Table.AddColumn(NonEmpty, "Date", each #date(Number.FromText([TIME_PERIOD]), 1, 1), type date),
				    Renamed = Table.RenameColumns(
				        Table.RemoveColumns(WithDate, {"TIME_PERIOD"}),
				        {{"geo", "GeoCode"}, {"unit", "UnitCode"}, {"OBS_VALUE", "Value"}, {"OBS_FLAG", "Flag"}}
				    ),
				    Typed = Table.TransformColumnTypes(
				        Renamed,
				        {{"GeoCode", type text}, {"UnitCode", type text}, {"Value", type number}, {"Flag", type text}},
				        "en-US"
				    )
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 5: Create `tables/Unemployment.tmdl`**

```tmdl
/// Unemployment rate, age 15-74, all education levels (Eurostat lfst_r_lfu3rt), as a fraction.
table Unemployment

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column Date
		dataType: dateTime
		isHidden
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Rate
		dataType: double
		isHidden
		formatString: 0.0%
		summarizeBy: none
		sourceColumn: Rate

	column Flag
		dataType: string
		summarizeBy: none
		sourceColumn: Flag

	partition Unemployment = m
		mode: import
		source =
				let
				    Source = fnEurostat(
				        "lfst_r_lfu3rt",
				        "c[isced11]=TOTAL&c[sex]=T&c[age]=Y15-74&c[unit]=PC",
				        {"EU", "Country", "NUTS2"}
				    ),
				    Selected = Table.SelectColumns(Source, {"geo", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"}),
				    NonEmpty = Table.SelectRows(Selected, each [OBS_VALUE] <> ""),
				    WithDate = Table.AddColumn(NonEmpty, "Date", each #date(Number.FromText([TIME_PERIOD]), 1, 1), type date),
				    WithRate = Table.AddColumn(WithDate, "Rate", each Number.FromText([OBS_VALUE], "en-US") / 100, type number),
				    Renamed = Table.RenameColumns(
				        Table.RemoveColumns(WithRate, {"TIME_PERIOD", "OBS_VALUE"}),
				        {{"geo", "GeoCode"}, {"OBS_FLAG", "Flag"}}
				    ),
				    Typed = Table.TransformColumnTypes(Renamed, {{"GeoCode", type text}, {"Flag", type text}})
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 6: Create `tables/Enrolment.tmdl`**

```tmdl
/// Pupils and students enrolled by ISCED level and sex (Eurostat educ_uoe_enra11).
table Enrolment

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column SexCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: SexCode

	column IscedCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: IscedCode

	column Date
		dataType: dateTime
		isHidden
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Students
		dataType: int64
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Students

	column Flag
		dataType: string
		summarizeBy: none
		sourceColumn: Flag

	partition Enrolment = m
		mode: import
		source =
				let
				    Source = fnEurostat(
				        "educ_uoe_enra11",
				        "c[unit]=NR&c[sex]=T,M,F&c[isced11]=ED0-8,ED0,ED1,ED2,ED3,ED4,ED5,ED6,ED7,ED8",
				        {"EU", "Country", "NUTS2"}
				    ),
				    Selected = Table.SelectColumns(Source, {"geo", "sex", "isced11", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"}),
				    NonEmpty = Table.SelectRows(Selected, each [OBS_VALUE] <> ""),
				    WithDate = Table.AddColumn(NonEmpty, "Date", each #date(Number.FromText([TIME_PERIOD]), 1, 1), type date),
				    Renamed = Table.RenameColumns(
				        Table.RemoveColumns(WithDate, {"TIME_PERIOD"}),
				        {{"geo", "GeoCode"}, {"sex", "SexCode"}, {"isced11", "IscedCode"}, {"OBS_VALUE", "Students"}, {"OBS_FLAG", "Flag"}}
				    ),
				    Typed = Table.TransformColumnTypes(
				        Renamed,
				        {{"GeoCode", type text}, {"SexCode", type text}, {"IscedCode", type text}, {"Students", Int64.Type}, {"Flag", type text}},
				        "en-US"
				    )
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 7: Reference the tables.** Append to `model.tmdl`:

```tmdl
ref table Population
ref table Deaths
ref table GDP
ref table Unemployment
ref table Enrolment
```

- [ ] **Step 8: Run the tests, then the live check of these queries**

Run: `pytest tests/test_sources.py tests/test_powerbi_model.py -v`
Expected: PASS.

Run: `marche-stats check-sources`
Expected: `OK` for "GISCO NUTS codes", "ProvinceRegions matches GISCO" and the six Eurostat lines, each with a latest period (2023 to 2025). "Chamber of Commerce archive" is `OK`. No repository files are listed yet.

- [ ] **Step 9: Commit**

```bash
git add powerbi/marche-regional-profile.SemanticModel tests/test_sources.py
git commit -m "Add the Eurostat fact tables through fnEurostat"
```

---

### Task 10: `Companies` and the Python export tables

**Files:**
- Create: `.../definition/tables/Companies.tmdl`, `Forecast.tmdl`, `ForecastAccuracy.tmdl`, `Reconciliation.tmdl`
- Modify: `.../definition/model.tmdl`

- [ ] **Step 1: Create `tables/Companies.tmdl`**

```tmdl
/// Active companies by province, ATECO 2007 section and month-end, on constant boundaries.
/// Same rules as src/marche_stats/companies.py: section rows only (TOTAL rows equal their
/// sum), the 9 municipalities transferred to Emilia-Romagna removed from every month, and
/// months identical to the previous one in every row dropped as not updated.
table Companies

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column SectorCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: SectorCode

	column Date
		dataType: dateTime
		isHidden
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Companies
		dataType: int64
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Companies

	partition Companies = m
		mode: import
		source =
				let
				    Source = Csv.Document(Web.Contents(CompaniesSourceUrl), [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
				    Long = Table.UnpivotOtherColumns(Promoted, {"Territorio", "Settore Ateco 2007"}, "DateText", "Companies"),
				    Typed = Table.TransformColumnTypes(Long, {{"Companies", Int64.Type}}, "en-US"),
				    WithDate = Table.AddColumn(Typed, "Date", each Date.FromText([DateText], [Format = "dd/MM/yyyy", Culture = "en-US"]), type date),
				    // Stale months: identical to the previous month in every row of the file.
				    ByMonth = Table.Sort(
				        Table.Group(
				            WithDate,
				            {"Date"},
				            {{"Values", each Table.Sort(_, {{"Territorio", Order.Ascending}, {"Settore Ateco 2007", Order.Ascending}})[Companies], type list}}
				        ),
				        {{"Date", Order.Ascending}}
				    ),
				    MonthDates = ByMonth[Date],
				    MonthValues = ByMonth[Values],
				    StaleMonths = List.Select(
				        List.Positions(MonthDates),
				        each _ > 0 and MonthValues{_} = MonthValues{_ - 1}
				    ),
				    StaleDates = List.Transform(StaleMonths, each MonthDates{_}),
				    Updated = Table.SelectRows(WithDate, each not List.Contains(StaleDates, [Date])),
				    // Municipalities moved to Emilia-Romagna (Law 117/2009, Law 84/2021).
				    TransferredOut = {
				        "PU-11 Casteldelci", "PU-24 Maiolo", "PU-39 Novafeltria", "PU-42 Pennabilli", "PU-53 San Leo",
				        "PU-55 Sant'Agata Feltria", "PU-63 Talamello", "PU-33 Montecopiolo", "PU-60 Sassofeltrio"
				    },
				    Sections = Table.SelectRows(
				        Updated,
				        each [#"Settore Ateco 2007"] <> "TOTAL" and not List.Contains(TransferredOut, [Territorio])
				    ),
				    // Province code in the territory label -> NUTS 3. PS is the old code of Pesaro e Urbino.
				    ProvinceToNuts3 = [PU = "ITI31", PS = "ITI31", AN = "ITI32", MC = "ITI33", AP = "ITI34", FM = "ITI35"],
				    WithGeo = Table.AddColumn(Sections, "GeoCode", each Record.Field(ProvinceToNuts3, Text.Start([Territorio], 2)), type text),
				    Grouped = Table.Group(
				        WithGeo,
				        {"GeoCode", "Settore Ateco 2007", "Date"},
				        {{"Companies", each List.Sum([Companies]), Int64.Type}}
				    ),
				    Renamed = Table.RenameColumns(Grouped, {{"Settore Ateco 2007", "SectorCode"}})
				in
				    Renamed

	annotation PBI_ResultType = Table
```

- [ ] **Step 2: Create `tables/Forecast.tmdl`**

```tmdl
/// Regional active companies: series the SARIMA model is fitted on, holdout forecasts and
/// the 12-month forecast with its 95 % interval (powerbi/data/forecast.csv).
table Forecast

	column Date
		dataType: dateTime
		isHidden
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Actual
		dataType: double
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Actual

	column HoldoutSarima
		dataType: double
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: HoldoutSarima

	column HoldoutNaive
		dataType: double
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: HoldoutNaive

	column HoldoutSeasonalNaive
		dataType: double
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: HoldoutSeasonalNaive

	column Forecast
		dataType: double
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Forecast

	column Lower95
		dataType: double
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Lower95

	column Upper95
		dataType: double
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Upper95

	partition Forecast = m
		mode: import
		source =
				let
				    Source = Csv.Document(Web.Contents(RepoRawBase & "/powerbi/data/forecast.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
				    Blanks = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, Table.ColumnNames(Promoted)),
				    Renamed = Table.RenameColumns(Blanks, {
				        {"date", "Date"}, {"actual", "Actual"}, {"holdout_sarima", "HoldoutSarima"}, {"holdout_naive", "HoldoutNaive"},
				        {"holdout_seasonal_naive", "HoldoutSeasonalNaive"}, {"forecast", "Forecast"}, {"lower_95", "Lower95"}, {"upper_95", "Upper95"}
				    }),
				    Typed = Table.TransformColumnTypes(Renamed, {
				        {"Date", type date}, {"Actual", type number}, {"HoldoutSarima", type number}, {"HoldoutNaive", type number},
				        {"HoldoutSeasonalNaive", type number}, {"Forecast", type number}, {"Lower95", type number}, {"Upper95", type number}
				    }, "en-US")
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 3: Create `tables/ForecastAccuracy.tmdl`**

```tmdl
/// Out-of-sample errors of SARIMA and the naive baselines (powerbi/data/forecast_accuracy.csv).
table ForecastAccuracy

	column Method
		dataType: string
		summarizeBy: none
		sourceColumn: Method

	column MAE
		dataType: double
		formatString: #,0
		summarizeBy: none
		sourceColumn: MAE

	column MAPE
		dataType: double
		formatString: 0.00
		summarizeBy: none
		sourceColumn: MAPE

	column Specification
		dataType: string
		summarizeBy: none
		sourceColumn: Specification

	column IntervalCoverage
		dataType: double
		formatString: 0
		summarizeBy: none
		sourceColumn: IntervalCoverage

	column HoldoutStart
		dataType: dateTime
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: HoldoutStart

	column HoldoutEnd
		dataType: dateTime
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: HoldoutEnd

	partition ForecastAccuracy = m
		mode: import
		source =
				let
				    Source = Csv.Document(Web.Contents(RepoRawBase & "/powerbi/data/forecast_accuracy.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
				    Blanks = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, Table.ColumnNames(Promoted)),
				    Renamed = Table.RenameColumns(Blanks, {
				        {"method", "Method"}, {"mae", "MAE"}, {"mape_pct", "MAPE"}, {"specification", "Specification"},
				        {"interval_coverage_pct", "IntervalCoverage"}, {"holdout_start", "HoldoutStart"}, {"holdout_end", "HoldoutEnd"}
				    }),
				    Typed = Table.TransformColumnTypes(Renamed, {
				        {"Method", type text}, {"MAE", type number}, {"MAPE", type number}, {"Specification", type text},
				        {"IntervalCoverage", type number}, {"HoldoutStart", type date}, {"HoldoutEnd", type date}
				    }, "en-US")
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 4: Create `tables/Reconciliation.tmdl`** (not related to other tables: its measures set their own filters)

```tmdl
/// Totals computed by the tested Python pipeline that the Power Query cleaning must match
/// (powerbi/data/reconciliation.csv).
table Reconciliation

	column Checkpoint
		dataType: string
		summarizeBy: none
		sourceColumn: Checkpoint

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column Date
		dataType: dateTime
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: Date

	column Expected
		dataType: int64
		isHidden
		formatString: #,0
		summarizeBy: sum
		sourceColumn: Expected

	partition Reconciliation = m
		mode: import
		source =
				let
				    Source = Csv.Document(Web.Contents(RepoRawBase & "/powerbi/data/reconciliation.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
				    Renamed = Table.RenameColumns(Promoted, {
				        {"checkpoint", "Checkpoint"}, {"geo", "GeoCode"}, {"date", "Date"}, {"active_companies", "Expected"}
				    }),
				    Typed = Table.TransformColumnTypes(Renamed, {
				        {"Checkpoint", type text}, {"GeoCode", type text}, {"Date", type date}, {"Expected", Int64.Type}
				    }, "en-US")
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 5: Reference the tables.** Append to `model.tmdl`:

```tmdl
ref table Companies
ref table Forecast
ref table ForecastAccuracy
ref table Reconciliation
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_powerbi_model.py tests/test_sources.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add powerbi/marche-regional-profile.SemanticModel
git commit -m "Add the Companies table cleaned in Power Query and the Python export tables"
```

---

### Task 11: Relationships

**Files:**
- Create: `.../definition/relationships.tmdl`

- [ ] **Step 1: Create `relationships.tmdl`.** Every relationship is many-to-one from the fact to the dimension, single direction (the TMDL defaults). `ForecastAccuracy` and `Reconciliation` stay unrelated.

```tmdl
relationship Population_Geo
	fromColumn: Population.GeoCode
	toColumn: Geo.Code

relationship Population_Calendar
	fromColumn: Population.Date
	toColumn: Calendar.Date

relationship Population_Sex
	fromColumn: Population.SexCode
	toColumn: Sex.Code

relationship Population_AgeGroup
	fromColumn: Population.AgeCode
	toColumn: AgeGroup.Code

relationship Deaths_Geo
	fromColumn: Deaths.GeoCode
	toColumn: Geo.Code

relationship Deaths_Calendar
	fromColumn: Deaths.Date
	toColumn: Calendar.Date

relationship Deaths_Sex
	fromColumn: Deaths.SexCode
	toColumn: Sex.Code

relationship Deaths_AgeGroup
	fromColumn: Deaths.AgeCode
	toColumn: AgeGroup.Code

relationship GDP_Geo
	fromColumn: GDP.GeoCode
	toColumn: Geo.Code

relationship GDP_Calendar
	fromColumn: GDP.Date
	toColumn: Calendar.Date

relationship Unemployment_Geo
	fromColumn: Unemployment.GeoCode
	toColumn: Geo.Code

relationship Unemployment_Calendar
	fromColumn: Unemployment.Date
	toColumn: Calendar.Date

relationship Enrolment_Geo
	fromColumn: Enrolment.GeoCode
	toColumn: Geo.Code

relationship Enrolment_Calendar
	fromColumn: Enrolment.Date
	toColumn: Calendar.Date

relationship Enrolment_Sex
	fromColumn: Enrolment.SexCode
	toColumn: Sex.Code

relationship Enrolment_ISCED
	fromColumn: Enrolment.IscedCode
	toColumn: ISCED.Code

relationship Companies_Geo
	fromColumn: Companies.GeoCode
	toColumn: Geo.Code

relationship Companies_Calendar
	fromColumn: Companies.Date
	toColumn: Calendar.Date

relationship Companies_Sector
	fromColumn: Companies.SectorCode
	toColumn: Sector.Code

relationship Forecast_Calendar
	fromColumn: Forecast.Date
	toColumn: Calendar.Date
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_powerbi_model.py -v`
Expected: `test_relationships_use_existing_columns` now runs and PASSES.

- [ ] **Step 3: Commit**

```bash
git add powerbi/marche-regional-profile.SemanticModel/definition/relationships.tmdl
git commit -m "Relate the fact tables to Geo, Calendar and the code dimensions"
```

---

### Task 12: Measures

Definitions follow `docs/methodology.md` (spec, "Measures"). Two patterns repeat:

- **Reference date (`_Ref date …`).** The latest date with data for *every* area of the comparison set, inside the current Calendar filter. The comparison set is the provinces when the row is a province, otherwise focus, peers, country and EU. `MINX` skips areas without a value, so on a year axis each year shows wherever data exists, and a single KPI uses the latest year common to all areas.
- **Region from provinces.** `Companies` rows are provinces. A measure evaluated for the focus region adds the province codes whose `ParentCode` is in the filter.

**Files:**
- Modify: `.../definition/tables/_Measures.tmdl`

- [ ] **Step 1: Write a failing reference check.** Append to `tests/test_powerbi_model.py`:

```python
def test_measure_table_has_the_spec_indicators():
    measures = model_tables()["_Measures"]["measures"]
    assert {
        "Population",
        "Population change 5y %",
        "Share aged 0-14",
        "Share aged 65+",
        "Share aged 80+",
        "Deaths",
        "Crude death rate per 1,000",
        "GDP per inhabitant (EUR)",
        "GDP per inhabitant (PPS, EU = 100)",
        "Unemployment rate",
        "Students enrolled",
        "Tertiary students per 1,000 residents",
        "Active companies",
        "Active companies change %",
        "Companies per 1,000 residents",
        "Reconciliation status",
    } <= measures
```

Run: `pytest tests/test_powerbi_model.py::test_measure_table_has_the_spec_indicators -v`
Expected: FAIL (the set is empty).

- [ ] **Step 2: Replace `tables/_Measures.tmdl` with the full table**

```tmdl
/// All measures of the report, in display folders by page.
table _Measures

	/// Latest date with population data for every area of the comparison set.
	measure '_Ref date Population' =
			VAR Areas = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer", "Country", "EU" } )
			VAR Provinces = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Province" )
			VAR AreaDate = MINX ( Areas, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( Population[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
			VAR ProvinceDate = MINX ( Provinces, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( Population[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
			RETURN IF ( SELECTEDVALUE ( Geo[Level] ) = "NUTS3", ProvinceDate, AreaDate )
		formatString: yyyy-mm-dd
		isHidden
		displayFolder: _Helpers

	/// Latest date with deaths data for every area of the comparison set.
	measure '_Ref date Deaths' =
			VAR Areas = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer", "Country", "EU" } )
			VAR Provinces = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Province" )
			VAR AreaDate = MINX ( Areas, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( Deaths[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
			VAR ProvinceDate = MINX ( Provinces, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( Deaths[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
			RETURN IF ( SELECTEDVALUE ( Geo[Level] ) = "NUTS3", ProvinceDate, AreaDate )
		formatString: yyyy-mm-dd
		isHidden
		displayFolder: _Helpers

	/// Latest date with GDP data for every area of the comparison set.
	measure '_Ref date GDP' =
			VAR Areas = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer", "Country", "EU" } )
			VAR Provinces = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Province" )
			VAR AreaDate = MINX ( Areas, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( GDP[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
			VAR ProvinceDate = MINX ( Provinces, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( GDP[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
			RETURN IF ( SELECTEDVALUE ( Geo[Level] ) = "NUTS3", ProvinceDate, AreaDate )
		formatString: yyyy-mm-dd
		isHidden
		displayFolder: _Helpers

	/// Latest date with unemployment data for every area of the comparison set.
	measure '_Ref date Unemployment' =
			VAR Areas = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer", "Country", "EU" } )
			RETURN MINX ( Areas, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( Unemployment[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
		formatString: yyyy-mm-dd
		isHidden
		displayFolder: _Helpers

	/// Latest date with enrolment data for every area of the comparison set.
	measure '_Ref date Enrolment' =
			VAR Areas = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer", "Country", "EU" } )
			RETURN MINX ( Areas, VAR c = Geo[Code] RETURN CALCULATE ( MAX ( Enrolment[Date] ), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
		formatString: yyyy-mm-dd
		isHidden
		displayFolder: _Helpers

	/// Population on 1 January of the reference year. Total sex and age unless the visual
	/// filters Sex or AgeGroup.
	measure Population =
			VAR d = [_Ref date Population]
			RETURN
			    SWITCH (
			        TRUE (),
			        ISFILTERED ( Sex ) && ISFILTERED ( AgeGroup ), CALCULATE ( SUM ( Population[Residents] ), Population[Date] = d ),
			        ISFILTERED ( Sex ), CALCULATE ( SUM ( Population[Residents] ), Population[Date] = d, AgeGroup[Code] = "TOTAL" ),
			        ISFILTERED ( AgeGroup ), CALCULATE ( SUM ( Population[Residents] ), Population[Date] = d, Sex[Code] = "T" ),
			        CALCULATE ( SUM ( Population[Residents] ), Population[Date] = d, Sex[Code] = "T", AgeGroup[Code] = "TOTAL" )
			    )
		formatString: #,0
		displayFolder: Population & Health

	/// Change in population over the five years to the reference year.
	measure 'Population change 5y %' =
			VAR d = [_Ref date Population]
			VAR PopLatest = [Population]
			VAR PopBefore = CALCULATE ( [Population], REMOVEFILTERS ( Calendar ), Calendar[Date] = DATE ( YEAR ( d ) - 5, 1, 1 ) )
			RETURN IF ( NOT ISBLANK ( PopBefore ), DIVIDE ( PopLatest - PopBefore, PopBefore ) )
		formatString: +0.0%;-0.0%;0.0%
		displayFolder: Population & Health

	/// Share of residents aged 0-14 on 1 January.
	measure 'Share aged 0-14' =
			DIVIDE (
			    CALCULATE ( [Population], REMOVEFILTERS ( AgeGroup ), AgeGroup[BroadGroup] = "0-14" ),
			    CALCULATE ( [Population], REMOVEFILTERS ( AgeGroup ), AgeGroup[Code] = "TOTAL" )
			)
		formatString: 0.0%
		displayFolder: Population & Health

	/// Share of residents aged 65 or over on 1 January.
	measure 'Share aged 65+' =
			DIVIDE (
			    CALCULATE ( [Population], REMOVEFILTERS ( AgeGroup ), AgeGroup[BroadGroup] = "65+" ),
			    CALCULATE ( [Population], REMOVEFILTERS ( AgeGroup ), AgeGroup[Code] = "TOTAL" )
			)
		formatString: 0.0%
		displayFolder: Population & Health

	/// Share of residents aged 80 or over on 1 January.
	measure 'Share aged 80+' =
			DIVIDE (
			    CALCULATE ( [Population], REMOVEFILTERS ( AgeGroup ), AgeGroup[Is80Plus] = TRUE () ),
			    CALCULATE ( [Population], REMOVEFILTERS ( AgeGroup ), AgeGroup[Code] = "TOTAL" )
			)
		formatString: 0.0%
		displayFolder: Population & Health

	/// Deaths in the reference year. Total sex and age unless the visual filters Sex or AgeGroup.
	measure Deaths =
			VAR d = [_Ref date Deaths]
			RETURN
			    SWITCH (
			        TRUE (),
			        ISFILTERED ( Sex ) && ISFILTERED ( AgeGroup ), CALCULATE ( SUM ( Deaths[Count] ), Deaths[Date] = d ),
			        ISFILTERED ( Sex ), CALCULATE ( SUM ( Deaths[Count] ), Deaths[Date] = d, AgeGroup[Code] = "TOTAL" ),
			        ISFILTERED ( AgeGroup ), CALCULATE ( SUM ( Deaths[Count] ), Deaths[Date] = d, Sex[Code] = "T" ),
			        CALCULATE ( SUM ( Deaths[Count] ), Deaths[Date] = d, Sex[Code] = "T", AgeGroup[Code] = "TOTAL" )
			    )
		formatString: #,0
		displayFolder: Population & Health

	/// Deaths in the year per 1,000 residents on 1 January of the same year.
	measure 'Crude death rate per 1,000' =
			VAR d = [_Ref date Deaths]
			VAR DeathsTotal = CALCULATE ( SUM ( Deaths[Count] ), Deaths[Date] = d, Sex[Code] = "T", AgeGroup[Code] = "TOTAL" )
			VAR Residents = CALCULATE ( SUM ( Population[Residents] ), Population[Date] = d, Sex[Code] = "T", AgeGroup[Code] = "TOTAL" )
			RETURN DIVIDE ( 1000 * DeathsTotal, Residents )
		formatString: 0.0
		displayFolder: Population & Health

	/// GDP per inhabitant in euro, as published by Eurostat (EUR_HAB).
	measure 'GDP per inhabitant (EUR)' =
			VAR d = [_Ref date GDP]
			RETURN CALCULATE ( SUM ( GDP[Value] ), GDP[Date] = d, GDP[UnitCode] = "EUR_HAB" )
		formatString: #,0
		displayFolder: Economy & Labour

	/// GDP per inhabitant in purchasing power standard, EU = 100 (PPS_HAB_EU27_2020).
	measure 'GDP per inhabitant (PPS, EU = 100)' =
			VAR d = [_Ref date GDP]
			RETURN CALCULATE ( SUM ( GDP[Value] ), GDP[Date] = d, GDP[UnitCode] = "PPS_HAB_EU27_2020" )
		formatString: 0
		displayFolder: Economy & Labour

	/// Unemployment rate, age 15-74.
	measure 'Unemployment rate' =
			VAR d = [_Ref date Unemployment]
			RETURN CALCULATE ( SUM ( Unemployment[Rate] ), Unemployment[Date] = d )
		formatString: 0.0%
		displayFolder: Economy & Labour

	/// Pupils and students enrolled. All levels and both sexes unless the visual filters ISCED or Sex.
	measure 'Students enrolled' =
			VAR d = [_Ref date Enrolment]
			RETURN
			    SWITCH (
			        TRUE (),
			        ISFILTERED ( Sex ) && ISFILTERED ( ISCED ), CALCULATE ( SUM ( Enrolment[Students] ), Enrolment[Date] = d, KEEPFILTERS ( ISCED[IsTotal] = FALSE () ) ),
			        ISFILTERED ( Sex ), CALCULATE ( SUM ( Enrolment[Students] ), Enrolment[Date] = d, ISCED[Code] = "ED0-8" ),
			        ISFILTERED ( ISCED ), CALCULATE ( SUM ( Enrolment[Students] ), Enrolment[Date] = d, Sex[Code] = "T", KEEPFILTERS ( ISCED[IsTotal] = FALSE () ) ),
			        CALCULATE ( SUM ( Enrolment[Students] ), Enrolment[Date] = d, Sex[Code] = "T", ISCED[Code] = "ED0-8" )
			    )
		formatString: #,0
		displayFolder: Education

	/// Students in ISCED 5-8 per 1,000 residents on 1 January of the same year.
	measure 'Tertiary students per 1,000 residents' =
			VAR d = [_Ref date Enrolment]
			VAR Tertiary = CALCULATE ( SUM ( Enrolment[Students] ), Enrolment[Date] = d, Sex[Code] = "T", REMOVEFILTERS ( ISCED ), ISCED[Group] = "ISCED 5-8" )
			VAR Residents = CALCULATE ( SUM ( Population[Residents] ), Population[Date] = d, Sex[Code] = "T", AgeGroup[Code] = "TOTAL" )
			RETURN DIVIDE ( 1000 * Tertiary, Residents )
		formatString: 0.0
		displayFolder: Education

	/// Active companies at the last month-end in context. For the focus region, the sum of its provinces.
	measure 'Active companies' =
			VAR Areas = VALUES ( Geo[Code] )
			VAR WithProvinces = UNION ( Areas, CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), TREATAS ( Areas, Geo[ParentCode] ) ) )
			VAR LastDate = CALCULATE ( MAX ( Companies[Date] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ) )
			RETURN CALCULATE ( SUM ( Companies[Companies] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), Companies[Date] = LastDate )
		formatString: #,0
		displayFolder: Business

	/// Change in active companies from the first to the last full-year December.
	measure 'Active companies change %' =
			VAR Areas = VALUES ( Geo[Code] )
			VAR WithProvinces = UNION ( Areas, CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), TREATAS ( Areas, Geo[ParentCode] ) ) )
			VAR LastDec = CALCULATE ( MAX ( Companies[Date] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), Calendar[MonthNumber] = 12 )
			VAR FirstDec = CALCULATE ( MIN ( Companies[Date] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), REMOVEFILTERS ( Calendar ), Calendar[MonthNumber] = 12 )
			VAR AtLast = CALCULATE ( SUM ( Companies[Companies] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), REMOVEFILTERS ( Calendar ), Companies[Date] = LastDec )
			VAR AtFirst = CALCULATE ( SUM ( Companies[Companies] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), REMOVEFILTERS ( Calendar ), Companies[Date] = FirstDec )
			RETURN DIVIDE ( AtLast - AtFirst, AtFirst )
		formatString: +0.0%;-0.0%;0.0%
		displayFolder: Business

	/// Active companies at 31 December per 1,000 residents on 1 January of the following year.
	measure 'Companies per 1,000 residents' =
			VAR Areas = VALUES ( Geo[Code] )
			VAR WithProvinces = UNION ( Areas, CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), TREATAS ( Areas, Geo[ParentCode] ) ) )
			VAR LastDec = CALCULATE ( MAX ( Companies[Date] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), Calendar[MonthNumber] = 12 )
			VAR CompaniesAtDec = CALCULATE ( SUM ( Companies[Companies] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), REMOVEFILTERS ( Calendar ), Companies[Date] = LastDec )
			VAR Residents = CALCULATE ( SUM ( Population[Residents] ), REMOVEFILTERS ( Calendar ), Population[Date] = DATE ( YEAR ( LastDec ) + 1, 1, 1 ), Sex[Code] = "T", AgeGroup[Code] = "TOTAL" )
			RETURN DIVIDE ( 1000 * CompaniesAtDec, Residents )
		formatString: 0.0
		displayFolder: Business

	/// Regional active companies in the series the SARIMA model is fitted on.
	measure 'Modelled companies' = SUM ( Forecast[Actual] )
		formatString: #,0
		displayFolder: Forecast

	/// SARIMA forecast of the holdout months, made from the end of the training period.
	measure 'SARIMA holdout forecast' = SUM ( Forecast[HoldoutSarima] )
		formatString: #,0
		displayFolder: Forecast

	/// SARIMA forecast of the next 12 months, refitted on the full series.
	measure 'SARIMA forecast' = SUM ( Forecast[Forecast] )
		formatString: #,0
		displayFolder: Forecast

	/// Lower bound of the 95 % prediction interval.
	measure 'Forecast lower 95' = SUM ( Forecast[Lower95] )
		formatString: #,0
		displayFolder: Forecast

	/// Upper bound of the 95 % prediction interval.
	measure 'Forecast upper 95' = SUM ( Forecast[Upper95] )
		formatString: #,0
		displayFolder: Forecast

	/// Mean absolute percentage error of SARIMA on the holdout months.
	measure 'MAPE SARIMA' = CALCULATE ( SUM ( ForecastAccuracy[MAPE] ), ForecastAccuracy[Method] = "SARIMA" ) / 100
		formatString: 0.00%
		displayFolder: Forecast

	/// Mean absolute percentage error of the naive forecast (last value) on the holdout months.
	measure 'MAPE naive' = CALCULATE ( SUM ( ForecastAccuracy[MAPE] ), ForecastAccuracy[Method] = "Naive (last value)" ) / 100
		formatString: 0.00%
		displayFolder: Forecast

	/// Mean absolute percentage error of the seasonal naive forecast on the holdout months.
	measure 'MAPE seasonal naive' = CALCULATE ( SUM ( ForecastAccuracy[MAPE] ), ForecastAccuracy[Method] = "Seasonal naive" ) / 100
		formatString: 0.00%
		displayFolder: Forecast

	/// Value of the checkpoint computed by the Python pipeline.
	measure 'Reconciliation expected' = SUM ( Reconciliation[Expected] )
		formatString: #,0
		displayFolder: Checks

	/// The same checkpoint computed from the Companies table.
	measure 'Reconciliation in model' =
			VAR g = SELECTEDVALUE ( Reconciliation[GeoCode] )
			VAR d = SELECTEDVALUE ( Reconciliation[Date] )
			VAR WithProvinces = UNION ( { g }, CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[ParentCode] = g ) )
			RETURN CALCULATE ( SUM ( Companies[Companies] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ), REMOVEFILTERS ( Calendar ), Companies[Date] = d )
		formatString: #,0
		displayFolder: Checks

	/// ✓ when Power BI matches the Python pipeline, otherwise ✗ and the difference.
	measure 'Reconciliation status' =
			VAR Expected = [Reconciliation expected]
			VAR Diff = [Reconciliation in model] - Expected
			RETURN IF ( NOT ISBLANK ( Expected ), IF ( Diff = 0, "✓", "✗ " & FORMAT ( Diff, "+#,0;-#,0" ) ) )
		displayFolder: Checks

	column Placeholder
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: Placeholder

	partition _Measures = m
		mode: import
		source =
				#table(type table [Placeholder = text], {})

	annotation PBI_ResultType = Table
```

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_powerbi_model.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add powerbi/marche-regional-profile.SemanticModel/definition/tables/_Measures.tmdl tests/test_powerbi_model.py
git commit -m "Add the report measures with a common reference year per comparison"
```

---

### Task 13: Calculation group `Compare to` and field parameter `Province indicator`

**Files:**
- Create: `.../definition/tables/Compare to.tmdl`, `.../definition/tables/Province indicator.tmdl`
- Modify: `.../definition/model.tmdl`

- [ ] **Step 1: Create `tables/Compare to.tmdl`.** Every item leaves text measures unchanged (`ISTEXT`), so the reconciliation status and Phase B's dynamic titles are not compared.

```tmdl
/// Benchmark comparisons for any indicator measure: the value, the country, the EU, the
/// unweighted mean of the peer regions, the differences from them and the rank among peers.
table 'Compare to'
	calculationGroup
		precedence: 10

		calculationItem Value = SELECTEDMEASURE ()
			ordinal: 0

		calculationItem Country =
				VAR v = SELECTEDMEASURE ()
				RETURN IF ( ISTEXT ( v ), v, CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( Geo ), Geo[Role] = "Country" ) )
			ordinal: 1

		calculationItem 'vs Country' =
				VAR v = SELECTEDMEASURE ()
				VAR c = CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( Geo ), Geo[Role] = "Country" )
				RETURN IF ( ISTEXT ( v ), v, IF ( NOT ISBLANK ( v ) && NOT ISBLANK ( c ), v - c ) )
			ordinal: 2
			formatStringDefinition = SELECTEDMEASUREFORMATSTRING ()

		calculationItem EU =
				VAR v = SELECTEDMEASURE ()
				RETURN IF ( ISTEXT ( v ), v, CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( Geo ), Geo[Role] = "EU" ) )
			ordinal: 3

		calculationItem 'vs EU' =
				VAR v = SELECTEDMEASURE ()
				VAR e = CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( Geo ), Geo[Role] = "EU" )
				RETURN IF ( ISTEXT ( v ), v, IF ( NOT ISBLANK ( v ) && NOT ISBLANK ( e ), v - e ) )
			ordinal: 4
			formatStringDefinition = SELECTEDMEASUREFORMATSTRING ()

		calculationItem 'Peers avg' =
				VAR v = SELECTEDMEASURE ()
				VAR Peers = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Peer" )
				RETURN IF ( ISTEXT ( v ), v, AVERAGEX ( Peers, VAR c = Geo[Code] RETURN CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( Geo ), Geo[Code] = c ) ) )
			ordinal: 5

		calculationItem 'vs Peers avg' =
				VAR v = SELECTEDMEASURE ()
				VAR Peers = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Peer" )
				VAR p = AVERAGEX ( Peers, VAR c = Geo[Code] RETURN CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( Geo ), Geo[Code] = c ) )
				RETURN IF ( ISTEXT ( v ), v, IF ( NOT ISBLANK ( v ) && NOT ISBLANK ( p ), v - p ) )
			ordinal: 6
			formatStringDefinition = SELECTEDMEASUREFORMATSTRING ()

		calculationItem 'Rank among peers' =
				VAR v = SELECTEDMEASURE ()
				VAR Areas = CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer" } )
				VAR Comparable =
				    ISSELECTEDMEASURE (
				        [Population change 5y %], [Share aged 0-14], [Share aged 65+], [Share aged 80+],
				        [Crude death rate per 1,000], [GDP per inhabitant (EUR)], [GDP per inhabitant (PPS, EU = 100)],
				        [Unemployment rate], [Tertiary students per 1,000 residents]
				    )
				RETURN
				    IF (
				        Comparable && SELECTEDVALUE ( Geo[Role] ) IN { "Focus", "Peer" } && NOT ISBLANK ( v ),
				        RANKX ( Areas, VAR c = Geo[Code] RETURN CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( Geo ), Geo[Code] = c ), v, DESC, DENSE )
				    )
			ordinal: 7
			formatStringDefinition = "0"

	column Comparison
		dataType: string
		summarizeBy: none
		sourceColumn: Name
		sortByColumn: Ordinal

	column Ordinal
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: sum
		sourceColumn: Ordinal
```

- [ ] **Step 2: Create `tables/Province indicator.tmdl`** (field parameter for the Provinces page)

```tmdl
/// Indicator shown on the Provinces map (field parameter).
table 'Province indicator'

	column 'Province indicator'
		summarizeBy: none
		sourceColumn: [Value1]
		sortByColumn: 'Province indicator Order'

		relatedColumnDetails
			groupByColumn: 'Province indicator Fields'

	column 'Province indicator Fields'
		isHidden
		summarizeBy: none
		sourceColumn: [Value2]
		sortByColumn: 'Province indicator Order'

		extendedProperty ParameterMetadata =
				{
				  "version": 3,
				  "kind": 2
				}

	column 'Province indicator Order'
		isHidden
		formatString: 0
		summarizeBy: sum
		sourceColumn: [Value3]

	partition 'Province indicator' = calculated
		mode: import
		source =
				{
				    ("Population change 5y %", NAMEOF ( '_Measures'[Population change 5y %] ), 0),
				    ("Share aged 65+", NAMEOF ( '_Measures'[Share aged 65+] ), 1),
				    ("Crude death rate per 1,000", NAMEOF ( '_Measures'[Crude death rate per 1,000] ), 2),
				    ("Companies per 1,000 residents", NAMEOF ( '_Measures'[Companies per 1,000 residents] ), 3),
				    ("GDP per inhabitant (EUR)", NAMEOF ( '_Measures'[GDP per inhabitant (EUR)] ), 4)
				}
```

- [ ] **Step 3: Reference the tables.** Append to `model.tmdl`:

```tmdl
ref table 'Compare to'
ref table 'Province indicator'
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_powerbi_model.py -v`
Expected: PASS. `test_measure_references_exist` now checks every `ISSELECTEDMEASURE` and `NAMEOF` name against `_Measures`.

- [ ] **Step 5: Commit**

```bash
git add powerbi/marche-regional-profile.SemanticModel
git commit -m "Add the Compare to calculation group and the Province indicator field parameter"
```

---

### Task 14: Model check page

One page with three visuals:
1. **Indicators by area:** a table of every indicator for every area.
2. **Compare to:** a matrix of the calculation group for the focus region.
3. **Reconciliation:** a table of Power BI against Python.

**Files:**
- Create: `powerbi/marche-regional-profile.Report/definition/pages/pages.json`
- Create: `.../definition/pages/5e0c7a1d9b3f2a4c6e81/page.json` and three `visuals/*/visual.json`

- [ ] **Step 1: Write the page with a script** (the JSON is repetitive, so a script avoids typos). Run from the repository root:

```bash
python -I - <<'EOF'
import json
from pathlib import Path

PAGE = "5e0c7a1d9b3f2a4c6e81"
root = Path("powerbi/marche-regional-profile.Report/definition/pages")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"


def column(entity, prop):
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }


def measure(prop):
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": prop}},
        "queryRef": f"_Measures.{prop}",
        "nativeQueryRef": prop,
    }


def title(text):
    return {"title": [{"properties": {
        "show": {"expr": {"Literal": {"Value": "true"}}},
        "text": {"expr": {"Literal": {"Value": f"'{text}'"}}},
    }}]}


def visual(name, kind, y, height, query_state, text, filters=None):
    container = {
        "$schema": f"{SCHEMA}/visualContainer/2.13.0/schema.json",
        "name": name,
        "position": {"x": 24, "y": y, "z": 0, "height": height, "width": 1232, "tabOrder": 0},
        "visual": {
            "visualType": kind,
            "query": {"queryState": query_state},
            "visualContainerObjects": title(text),
            "drillFilterOtherVisuals": True,
        },
    }
    if filters:
        container["filterConfig"] = {"filters": filters}
    path = root / PAGE / "visuals" / name / "visual.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(container, indent=2), encoding="utf-8")


root.mkdir(parents=True, exist_ok=True)
(root / "pages.json").write_text(json.dumps({
    "$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
    "pageOrder": [PAGE],
    "activePageName": PAGE,
}, indent=2), encoding="utf-8")
(root / PAGE).mkdir(exist_ok=True)
(root / PAGE / "page.json").write_text(json.dumps({
    "$schema": f"{SCHEMA}/page/2.1.0/schema.json",
    "name": PAGE,
    "displayName": "Model check",
    "displayOption": "FitToWidth",
    "height": 1180,
    "width": 1280,
}, indent=2), encoding="utf-8")

indicators = [
    "Population", "Population change 5y %", "Share aged 65+", "Crude death rate per 1,000",
    "GDP per inhabitant (EUR)", "GDP per inhabitant (PPS, EU = 100)", "Unemployment rate",
    "Students enrolled", "Tertiary students per 1,000 residents", "Active companies",
    "Companies per 1,000 residents",
]
visual("a1c3e5f7091b2d4f6a8c", "tableEx", 24, 520,
       {"Values": {"projections": [column("Geo", "Name"), column("Geo", "Role")]
                   + [measure(m) for m in indicators]}},
       "Indicators by area (latest year common to the areas)")

focus_filter = [{
    "name": "f0c1a2b3c4d5e6f7a8b9",
    "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Geo"}}, "Property": "Role"}},
    "type": "Categorical",
    "filter": {
        "Version": 2,
        "From": [{"Name": "g", "Entity": "Geo", "Type": 0}],
        "Where": [{"Condition": {"In": {
            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "g"}}, "Property": "Role"}}],
            "Values": [[{"Literal": {"Value": "'Focus'"}}]],
        }}}],
    },
}]
visual("b2d4f6a8c0e1f3a5b7d9", "pivotTable", 568, 300,
       {"Columns": {"projections": [column("Compare to", "Comparison")]},
        "Values": {"projections": [measure(m) for m in (
            "Unemployment rate", "Crude death rate per 1,000", "GDP per inhabitant (PPS, EU = 100)",
            "Share aged 65+")]}},
       "Compare to: focus region", focus_filter)

visual("c3e5f7a9b1d2e4f6a8c0", "tableEx", 892, 264,
       {"Values": {"projections": [column("Reconciliation", "Checkpoint"),
                                   measure("Reconciliation expected"),
                                   measure("Reconciliation in model"),
                                   measure("Reconciliation status")]}},
       "Reconciliation with the Python pipeline")
print("written", sorted(str(p) for p in root.rglob("*.json")))
EOF
```

Expected: the script prints five paths: `pages.json`, `page.json` and three `visual.json` files.

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_powerbi_model.py -v`
Expected: PASS. `test_report_fields_exist_in_model` checks every field of the three visuals against the model.

- [ ] **Step 3: Commit**

```bash
git add powerbi/marche-regional-profile.Report/definition/pages
git commit -m "Add the model check page"
```

---

### Task 15: Generate and commit the Power BI data files

**Files:**
- Create: `powerbi/data/forecast.csv`, `powerbi/data/forecast_accuracy.csv`, `powerbi/data/reconciliation.csv`

- [ ] **Step 1: Download the sources** (the business register file is not in the repository)

Run: `marche-stats download`
Expected: `data/raw/active_companies_marche.csv` exists (about 2.7 MB) with the Eurostat and GISCO files.

- [ ] **Step 2: Export**

Run: `marche-stats export-powerbi`
Expected: three files in `powerbi/data/`. Check them against `docs/results.md`:
- `forecast_accuracy.csv`: SARIMA `mape_pct` about 1.13, naive about 3.31, seasonal naive about 5.76; specification `SARIMA(2, 1, 2)(0, 1, 1)[12]`; holdout 2023-02-28 to 2025-01-31.
- `reconciliation.csv`: 12 rows. `Region, first month` is dated 2009-03-31 and `Region, last modelled month` 2025-01-31. The provinces are dated 2009-12-31 and 2024-12-31.
- `forecast.csv`: the first date is 2009-03-31; the `forecast` column covers 2025-02-28 to 2026-01-31.

- [ ] **Step 3: Commit**

```bash
git add powerbi/data
git commit -m "Export the SARIMA forecast, its accuracy and the reconciliation totals for Power BI"
```

---

### Task 16: First refresh in Power BI Desktop (user)

Only the user can run this task. The executor stops here and hands over these steps.

- [ ] **Step 1: Publish the branch, so the raw URLs resolve.** `RepoRawBase` points at `main`, which does not yet have `powerbi/data/`. Ask the user before pushing (pushing is outward-facing):

```bash
git push -u origin powerbi-pbip
```

- [ ] **Step 2: Point `RepoRawBase` at the branch.** Open `powerbi/marche-regional-profile.pbip` in Power BI Desktop. Go to *Transform data → Manage parameters → RepoRawBase* and set it to `https://raw.githubusercontent.com/simones99/marche-regional-stats/powerbi-pbip`. The value returns to `main` in Task 17.

- [ ] **Step 3: Refresh.** Choose *Anonymous* for every source if Desktop asks, and *Public* as privacy level. Expected: every table loads without errors. Error messages to look for:
  - "Eurostat request failed: HTTP 400 for …": a code in a parameter does not exist in that dataset. The message names the value.
  - "NUTS codes not found in GISCO": a code in `FocusRegion`, `PeerRegions` or `ProvinceRegions` does not exist in GISCO.
  - "The field 'XX' of the record wasn't found" in `Companies`: a new province prefix appeared in the Chamber of Commerce file.

- [ ] **Step 4: Check the model check page against known values.**
  - The **reconciliation** table shows ✓ in all 12 rows.
  - In **indicators by area**, compare with `docs/results.md`:

    | Row | Indicator | Expected |
    |---|---|---|
    | Pesaro e Urbino (ITI31) | Companies per 1,000 residents | about 87.0 |
    | Pesaro e Urbino (ITI31) | Share aged 65+ | about 25.7 % |
    | Macerata (ITI33) | Crude death rate | about 12.6 |
    | Marche | Crude death rate | between 11 and 13 (the 2019–2023 average was 12.6 per 1,000) |
    | Marche | Active companies | about 130,000 (March 2025) |
    | Italy, EU | Business columns | blank |
    | Every area | Unemployment rate | between 3 % and 12 % |
  - In the **Compare to** matrix, the columns Value, Country, vs Country, EU, vs EU, Peers avg, vs Peers avg and Rank among peers are filled. The rank is between 1 and 6. "vs Country" equals Value − Country.

- [ ] **Step 5: If a visual shows an error** (PBIR written by hand), rebuild it in Desktop with the same fields and title, listed in Task 14, Step 1. If Desktop rejects the field parameter table, delete it and recreate it with *Modeling → New parameter → Fields*, named `Province indicator`, with the five measures of Task 13, Step 2. Then save. If Desktop reports an unknown property `ordinal` in `Compare to.tmdl`, delete the eight `ordinal:` lines and set the item order in *Model view → Compare to → Calculation items* (Value, Country, vs Country, EU, vs EU, Peers avg, vs Peers avg, Rank among peers).

- [ ] **Step 6: Save and commit what Desktop rewrote.** Desktop adds lineage tags and may reformat TMDL. Close Desktop, then:

```bash
pytest -q
git add powerbi/marche-regional-profile.SemanticModel powerbi/marche-regional-profile.Report
git commit -m "Save the model after the first refresh in Power BI Desktop"
```

---

### Task 17: Retire the old projects and document the new one

**Files:**
- Delete: `powerbi/marche-regionali-2025.*`, `powerbi/marche-demography-education.*`
- Modify: `powerbi/README.md`, `powerbi/sources.md`
- Modify: `.../definition/expressions.tmdl` (`RepoRawBase` back to `main`)

- [ ] **Step 1: Remove the old projects** (they stay in git history)

```bash
git rm -r -q powerbi/marche-regionali-2025.pbip powerbi/marche-regionali-2025.Report powerbi/marche-regionali-2025.SemanticModel
git rm -r -q powerbi/marche-demography-education.pbip powerbi/marche-demography-education.Report powerbi/marche-demography-education.SemanticModel
```

- [ ] **Step 2: Replace `powerbi/README.md`** (Phase B extends it with pages and screenshots):

```markdown
# Power BI report

`marche-regional-profile.pbip` is a Power BI project on the Marche region (NUTS 2 `ITI3`), its provinces and its neighbouring regions, against Italy and the EU. It replaces the two earlier reports (`marche-regionali-2025`, `marche-demography-education`), which remain in the git history.

Phase A (this version) contains the semantic model and one model check page. The report pages follow in Phase B. Design: [spec](../docs/superpowers/specs/2026-10-12-marche-regional-profile-report-design.md).

## Model

- A star schema keyed on NUTS codes. Dimensions: `Geo`, `Calendar` (daily, the date table), `Sex`, `AgeGroup`, `ISCED`, `Sector`. Facts: `Population`, `Deaths`, `GDP`, `Unemployment`, `Enrolment`, `Companies`, `Forecast`.
- Power Query parameters choose the areas: `FocusRegion`, `PeerRegions`, `ProvinceRegions`, `Country`, `StartYear`. Every Eurostat query goes through one function, `fnEurostat`.
- The calculation group `Compare to` adds Country, EU, peer average, differences and rank to any indicator.
- `Companies` is cleaned in Power Query with the rules of `src/marche_stats/companies.py`. The model check page reconciles it with the totals that Python writes to `data/reconciliation.csv`.
- `data/` holds the files exported by `marche-stats export-powerbi`: the SARIMA forecast, its accuracy and the reconciliation totals.

## Refresh

Open `marche-regional-profile.pbip` in Power BI Desktop (Windows) and choose *Refresh*. All sources are public: use anonymous access. The data cache (`.pbi/cache.abf`) is not committed, so refresh after cloning.

`marche-stats check-sources` requests every source the model uses, from the TMDL files. It runs weekly in GitHub Actions.

Sources and query details: [sources.md](sources.md).
```

- [ ] **Step 3: Replace `powerbi/sources.md`:**

````markdown
# Data sources of the Power BI model

Every Eurostat query calls `fnEurostat(dataset, filters, levels)` (in `marche-regional-profile.SemanticModel/definition/expressions.tmdl`). The function requests:

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/<dataset>/1.0
  ?c[geo]=<codes for the levels>&<filters>&c[TIME_PERIOD]=ge:<StartYear>
  &format=csvdata&formatVersion=1.0&labels=id&compress=false
```

The levels map to codes through the parameters: `EU` → `EU27_2020`, `Country` → `IT`, `NUTS2` → `FocusRegion` and `PeerRegions`, `NUTS3` → `ProvinceRegions`. The period is open-ended. A fixed list of years fails with HTTP 400 as soon as Eurostat drops one of them.

| Table | Dataset | Filters | Levels |
|---|---|---|---|
| Population | `demo_r_pjangrp3` | `unit=NR`, `sex=T,M,F`, five-year age groups, `TOTAL`, `UNK` | EU, Country, NUTS2, NUTS3 |
| Deaths | `demo_r_magec3` | as above | EU, Country, NUTS2, NUTS3 |
| GDP | `nama_10r_2gdp` | `unit=EUR_HAB,PPS_HAB_EU27_2020` | EU, Country, NUTS2 |
| GDP | `nama_10r_3gdp` | `unit=EUR_HAB,PPS_HAB_EU27_2020` | NUTS3 |
| Unemployment | `lfst_r_lfu3rt` | `isced11=TOTAL`, `sex=T`, `age=Y15-74`, `unit=PC` | EU, Country, NUTS2 |
| Enrolment | `educ_uoe_enra11` | `unit=NR`, `sex=T,M,F`, `isced11=ED0-8,ED0…ED8` | EU, Country, NUTS2 |

Other sources:

| Table | Source |
|---|---|
| Geo | GISCO, NUTS 2024 attributes: `https://gisco-services.ec.europa.eu/distribution/v2/nuts/csv/NUTS_AT_2024.csv` (© EuroGeographics) |
| Companies | Camera di Commercio delle Marche, active companies by municipality and ATECO 2007 section, monthly, 2009–2025 (CC BY 4.0): parameter `CompaniesSourceUrl` |
| Forecast, ForecastAccuracy, Reconciliation | `powerbi/data/*.csv` in this repository, read from `RepoRawBase` (GitHub raw URL) |
````

- [ ] **Step 4: Point `RepoRawBase` back to `main`.** In `.../definition/expressions.tmdl`, the `RepoRawBase` line must read exactly:

```tmdl
expression RepoRawBase = "https://raw.githubusercontent.com/simones99/marche-regional-stats/main" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

Once the branch is merged, `main` serves `powerbi/data/` and the refresh works from a clean clone.

- [ ] **Step 5: Run everything and commit**

```bash
ruff check src tests && ruff format --check src tests && pytest -q
git add -A powerbi
git commit -m "Retire the two earlier Power BI projects and document the merged model"
```

---

### Task 18 (optional): Best Practice Analyzer in CI

The spec leaves this open. Timebox it to 30 minutes and record the outcome either way.

- [ ] **Step 1: Try Tabular Editor 2 on the TMDL folder.** Download `TabularEditor.Portable.zip` 2.27.2 from `https://github.com/TabularEditor/TabularEditor/releases/tag/2.27.2` and extract it to a new empty folder outside the repository, for example `$env:TEMP\te2`, then (PowerShell):

```powershell
& "$env:TEMP\te2\TabularEditor.exe" "powerbi\marche-regional-profile.SemanticModel\definition" -A "https://raw.githubusercontent.com/microsoft/Analysis-Services/master/BestPracticeRules/BPARules.json"
```

- [ ] **Step 2: Decide.**
  - **If it loads the model and lists rule results:** add a job `bpa` on `windows-latest` to `.github/workflows/ci.yml` that downloads the same zip and runs the same command with `-V` (fail on errors). Commit with "Run the Best Practice Analyzer on the semantic model in CI".
  - **If it cannot load a TMDL folder:** add one sentence under "Model" in `powerbi/README.md`: "Tabular Editor 2.27.2 cannot load the TMDL folder, so the Best Practice Analyzer does not run in CI." Commit with "Note why the Best Practice Analyzer is not in CI".

---

## Done when (Phase A)

- `pytest -q`, `ruff check src tests` and `ruff format --check src tests` pass.
- `marche-stats check-sources` reports every source as `OK` once the branch is merged (before that, `RepoRawBase` = `main` has no `powerbi/data/` and the three repository files fail).
- The user refreshes `marche-regional-profile.pbip` in Desktop without errors (Task 16).
- Every reconciliation row shows ✓, and the reference values of Task 16, Step 4 hold.
- The two old projects are removed, and `powerbi/README.md` and `sources.md` describe the new one.
