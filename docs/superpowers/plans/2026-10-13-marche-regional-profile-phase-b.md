# Marche regional profile, Phase B: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the report on top of the Phase A model: theme, navigation, eight pages, the Province detail drill-through, two tooltip pages, the PDF and PNG exports and the READMEs, as specified in [the Phase B spec](../specs/2026-10-13-marche-regional-profile-phase-b-design.md).

**Architecture:** Python adds two small export tables (province outlines, seasonal profile) and a PDF-to-PNG step. The semantic model gains five small tables and the measures the pages need (text, colours, map SVG, helpers). A new module writes the PBIR page folders from a compact layout (`report_layout.py` → `pbir.py`), once per page; the user then refines each page in Power BI Desktop, and Desktop's saved JSON becomes the source of truth.

**Tech Stack:** Python 3.11 (pandas, statsmodels, pypdfium2, Pillow via matplotlib), pytest, ruff; Power BI Desktop with PBIR and TMDL; DAX; Power Query M.

---

## Ground rules

- Work on the branch `powerbi-phase-b` (it holds the spec commit `9af8490`).
- **Edit TMDL and PBIR only while Power BI Desktop is closed.** Desktop overwrites the files on save.
- TMDL is indented with **tabs**: properties one tab deeper than their object, DAX of a multi-line measure three tabs. `tests/test_powerbi_model.py::test_tmdl_lines_are_tab_indented` fails on a space.
- New TMDL objects carry no `lineageTag`; Desktop adds them on the first save.
- `pytest -q`, `ruff check src tests` and `ruff format --check src tests` pass before every commit. `ruff format` does not split long string literals (titles, alt texts); split any string that leaves a line over 100 characters into adjacent literals (`"first part " "second part"`) so `ruff check` (E501) passes.
- `RepoRawBase` stays `…/main` in every commit (`tests/test_sources.py` guards it). Task 10 changes it in Desktop only for the refresh and resets it before committing.
- Commit messages: sentence case, imperative, no prefix (the repository's style).

## File structure

| File | Responsibility |
|---|---|
| `src/marche_stats/powerbi_export.py` (modify) | Adds `province_shapes_table`, `seasonality_table`; `build` writes five files |
| `src/marche_stats/pngs.py` (new) | Renders the exported PDF to one PNG per page |
| `src/marche_stats/pbir.py` (new) | PBIR writer: fields, visuals, pages, filters, `scaffold()` |
| `src/marche_stats/report_layout.py` (new) | Where each visual goes on each page, and which fields it shows |
| `src/marche_stats/cli.py` (modify) | Steps `scaffold-report` and `export-pngs`; passes the GeoJSON to `export-powerbi` |
| `tests/test_powerbi_export.py` (modify) | Tests of the two new tables and the five-file export |
| `tests/test_pngs.py`, `tests/test_pbir.py` (new) | Unit tests of the two new modules |
| `tests/test_powerbi_model.py` (modify) | Phase B tables, columns and measures exist |
| `tests/test_powerbi_report.py` (new) | Page list, navigator, 8 px grid, alt text, palette, font minimum, resources |
| `powerbi/data/province_shapes.csv`, `powerbi/data/seasonality.csv` (new) | Exported data, read through `RepoRawBase` |
| `…SemanticModel/definition/tables/*.tmdl` | New tables `ProvinceShape`, `Seasonality`, `Benchmark`, `Benchmark point`, `Data source`; `ShortName` in `ISCED` and `Sector`; new measures in `_Measures` |
| `…Report/StaticResources/RegisteredResources/` (new) | Theme `MarcheProfile.json` and the three photos |
| `…Report/definition/report.json`, `pages/` | Theme registration, the report pages |
| `powerbi/exports/` (new) | PDF and PNGs |
| `powerbi/README.md`, `powerbi/sources.md`, `README.md` | Documentation |

---

### Task 1: Align the spec with three facts found while planning

**Files:**
- Modify: `docs/superpowers/specs/2026-10-13-marche-regional-profile-phase-b-design.md`

- [x] **Step 1: Population years.** In "### 1 · Overview", replace `two line charts with markers: population on 1 January 2009–2025, active companies in December 2009–2024.` with:

```markdown
two line charts with markers: population on 1 January from the first year of `demo_r_pjangrp3` (2014) to the latest, active companies in December 2009–2024.
```

- [x] **Step 2: Alt text.** In "## Accessibility", replace item 6 with:

```markdown
6. Every visual has a title that says what and when, and alt text that names the chart and what it compares. The values themselves are written on the chart (rule 4).
```

- [x] **Step 3: Benchmark buttons label.** In "### 1 · Overview", replace `"Compare the Marche with" buttons Italy / EU / Peers` with `"Compare with" buttons (country, EU, peers; the country button shows the country's name)`. The label stays region-neutral, like the parameters.

- [x] **Step 4: Commit.**

```bash
git add docs/superpowers/specs/2026-10-13-marche-regional-profile-phase-b-design.md
git commit -m "Align the Phase B spec with the population years and the alt text rule"
```

---

### Task 2: `province_shapes_table`

**Files:**
- Modify: `src/marche_stats/powerbi_export.py`
- Test: `tests/test_powerbi_export.py`

- [x] **Step 1: Write the failing test.** Append to `tests/test_powerbi_export.py`, and add `import re` and `from pathlib import Path` to its imports:

```python
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
```

- [x] **Step 2: Run it.** `pytest tests/test_powerbi_export.py::test_province_shapes_fit_the_box -v`. Expected: FAIL with `AttributeError: module 'marche_stats.powerbi_export' has no attribute 'province_shapes_table'`.

- [x] **Step 3: Implement.** In `src/marche_stats/powerbi_export.py`, change the module docstring's first line to `"""Tables for the Power BI report: forecast, accuracy, reconciliation, seasonality, map."""`, add `import json` and `import math` to the imports, and add after `reconciliation_table`:

```python
MAP_BOX = 400


def _polygons(geometry: dict) -> list:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    return geometry["coordinates"]


def _ring_centroid(ring: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Area and centroid of a closed ring (shoelace formula)."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    if area == 0:
        return 0.0, ring[0][0], ring[0][1]
    return abs(area), cx / (6 * area), cy / (6 * area)


def province_shapes_table(geojson_path: Path, box: int = MAP_BOX) -> pd.DataFrame:
    """SVG path and label point of each NUTS 3 province, in a box x box square.

    Equirectangular projection scaled by the cosine of the mean latitude, north up. The
    label point is the centroid of the province's largest ring. The report's Map SVG
    measure draws these paths, so the map needs no map service.
    """
    features = json.loads(geojson_path.read_text(encoding="utf-8"))["features"]
    rings = {
        f["properties"]["NUTS_ID"]: [ring for poly in _polygons(f["geometry"]) for ring in poly]
        for f in features
    }
    points = [p for geo_rings in rings.values() for ring in geo_rings for p in ring]
    lon0, lon1 = min(p[0] for p in points), max(p[0] for p in points)
    lat0, lat1 = min(p[1] for p in points), max(p[1] for p in points)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    scale = box / max((lon1 - lon0) * k, lat1 - lat0)

    rows = []
    for geo in sorted(rings):
        projected = [
            [((p[0] - lon0) * k * scale, (lat1 - p[1]) * scale) for p in ring] for ring in rings[geo]
        ]
        path = "".join(
            "M" + " ".join(f"{x:.0f},{y:.0f}" for x, y in ring) + "Z" for ring in projected
        )
        _, label_x, label_y = max((_ring_centroid(ring) for ring in projected), key=lambda c: c[0])
        rows.append((geo, path, round(label_x), round(label_y)))
    return pd.DataFrame(rows, columns=["geo", "path", "label_x", "label_y"])
```

- [x] **Step 4: Run it.** `pytest tests/test_powerbi_export.py::test_province_shapes_fit_the_box -v`. Expected: PASS.

- [x] **Step 5: Commit.**

```bash
ruff check src tests && ruff format src tests
git add src/marche_stats/powerbi_export.py tests/test_powerbi_export.py
git commit -m "Project the province outlines into a 400 px box for the report map"
```

---

### Task 3: `seasonality_table`

**Files:**
- Modify: `src/marche_stats/powerbi_export.py`
- Test: `tests/test_powerbi_export.py`

- [ ] **Step 1: Write the failing test.** Append:

```python
def test_seasonality_table_has_twelve_months(fitted):
    _, series, _, _ = fitted
    table = powerbi_export.seasonality_table(series)
    assert list(table.columns) == ["month", "month_name", "effect"]
    assert list(table["month"]) == list(range(1, 13))
    assert list(table["month_name"]) == [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    # The synthetic register dips in January and February (conftest.py).
    assert table.loc[0, "effect"] < 0
    assert abs(table["effect"].sum()) < 0.02 * series.mean()
```

- [ ] **Step 2: Run it.** `pytest tests/test_powerbi_export.py::test_seasonality_table_has_twelve_months -v`. Expected: FAIL with `AttributeError: … has no attribute 'seasonality_table'`.

- [ ] **Step 3: Implement.** Add after `province_shapes_table`:

```python
def seasonality_table(series: pd.Series) -> pd.DataFrame:
    """Average STL seasonal effect by calendar month, as in docs/results.md (section 3)."""
    seasonal = timeseries.decompose(series)["seasonal"]
    profile = seasonal.groupby(seasonal.index.month).mean().round(0)
    return pd.DataFrame(
        {
            "month": profile.index.astype(int),
            "month_name": [pd.Timestamp(2000, m, 1).strftime("%b") for m in profile.index],
            "effect": profile.to_numpy(),
        }
    )
```

- [ ] **Step 4: Run it.** Same command. Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
ruff check src tests && ruff format src tests
git add src/marche_stats/powerbi_export.py tests/test_powerbi_export.py
git commit -m "Export the monthly seasonal profile for the business page"
```

---

### Task 4: Write five files from `export-powerbi`

**Files:**
- Modify: `src/marche_stats/powerbi_export.py` (`build`)
- Modify: `src/marche_stats/cli.py`
- Modify: `tests/test_powerbi_export.py` (`test_cli_export_powerbi_writes_three_files`)
- Create: `powerbi/data/province_shapes.csv`, `powerbi/data/seasonality.csv`

- [ ] **Step 1: Update the CLI test first.** Rename `test_cli_export_powerbi_writes_three_files` to `test_cli_export_powerbi_writes_five_files`, add `"--eurostat-dir", str(FIXTURES),` to its argument list after the `--companies` pair, and replace its `names` assertion with:

```python
    assert names == [
        "forecast.csv",
        "forecast_accuracy.csv",
        "province_shapes.csv",
        "reconciliation.csv",
        "seasonality.csv",
    ]
    shapes = pd.read_csv(tmp_path / "data" / "province_shapes.csv")
    assert len(shapes) == 5
    seasonality = pd.read_csv(tmp_path / "data" / "seasonality.csv")
    assert list(seasonality["month"]) == list(range(1, 13))
```

- [ ] **Step 2: Run it.** `pytest tests/test_powerbi_export.py -v -k cli`. Expected: FAIL (three files written).

- [ ] **Step 3: Implement `build`.** Replace `build` in `powerbi_export.py` with:

```python
def build(companies_csv: Path, out_dir: Path, geojson: Path, holdout: int = 24) -> dict[str, Path]:
    """Fit the model and write the five CSV files the report reads from powerbi/data/."""
    wide = companies.read_wide(companies_csv)
    series = companies.modelling_series(wide)
    evaluation = timeseries.evaluate(series, holdout=holdout)
    future = timeseries.forecast(series, evaluation.order, evaluation.seasonal_order, steps=12)
    tables = {
        "forecast.csv": forecast_table(series, evaluation, future),
        "forecast_accuracy.csv": accuracy_table(evaluation),
        "reconciliation.csv": reconciliation_table(wide, series),
        "seasonality.csv": seasonality_table(series),
        "province_shapes.csv": province_shapes_table(geojson),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, frame in tables.items():
        path = out_dir / name
        frame.to_csv(
            path, index=False, date_format="%Y-%m-%d", float_format="%.4f", lineterminator="\n"
        )
        paths[name] = path
    return paths
```

- [ ] **Step 4: Pass the GeoJSON from the CLI.** In `cli.py`, add after `args = parser.parse_args(argv)`:

```python
    geojson = args.eurostat_dir / "marche_nuts3.geojson"
```

and change both `powerbi_export.build(...)` calls to:

```python
        powerbi_export.build(args.companies, args.powerbi / "data", geojson, holdout=args.holdout)
```

- [ ] **Step 5: Run the tests.** `pytest -q`. Expected: all pass.

- [ ] **Step 6: Regenerate the real files.** `data/raw/` holds the companies file and `marche_nuts3.geojson` (run `marche-stats download` if not).

```bash
marche-stats export-powerbi
```

Check: `powerbi/data/seasonality.csv` has the effects of `docs/results.md`, section 3 (Jan −936, Feb −967, …, Dec +71, written as `-936.0000` etc.). `forecast.csv`, `forecast_accuracy.csv` and `reconciliation.csv` are unchanged (`git diff --stat powerbi/data` lists only the two new files).

- [ ] **Step 7: Commit.**

```bash
ruff check src tests && ruff format --check src tests
git add src/marche_stats tests powerbi/data/province_shapes.csv powerbi/data/seasonality.csv
git commit -m "Write the seasonal profile and province outlines with export-powerbi"
```

---

### Task 5: `export-pngs`

**Files:**
- Create: `src/marche_stats/pngs.py`
- Modify: `src/marche_stats/cli.py`, `requirements.txt`
- Test: `tests/test_pngs.py`

- [ ] **Step 1: Add the dependency.** Append `pypdfium2==4.30.0` to `requirements.txt` (keep the alphabetical order of the file if it has one: after `pandas`), then `pip install -r requirements-dev.txt`.

- [ ] **Step 2: Write the failing tests.** Create `tests/test_pngs.py`:

```python
import pypdfium2 as pdfium
import pytest
from PIL import Image

from marche_stats import cli, pngs


def _pdf(path, pages: int) -> None:
    document = pdfium.PdfDocument.new()
    for _ in range(pages):
        document.new_page(960, 540)
    document.save(str(path))
    document.close()


def test_export_writes_one_png_per_page(tmp_path):
    pdf = tmp_path / "report.pdf"
    _pdf(pdf, len(pngs.PAGE_SLUGS))
    paths = pngs.export(pdf, tmp_path / "png", width=640)
    assert [p.name for p in paths] == [f"{slug}.png" for slug in pngs.PAGE_SLUGS]
    with Image.open(paths[0]) as image:
        assert image.size == (640, 360)


def test_export_refuses_a_pdf_with_other_pages(tmp_path):
    pdf = tmp_path / "report.pdf"
    _pdf(pdf, 3)
    with pytest.raises(ValueError, match="3 pages"):
        pngs.export(pdf, tmp_path / "png")


def test_cli_export_pngs_writes_next_to_the_pdf(tmp_path):
    pdf = tmp_path / "report.pdf"
    _pdf(pdf, len(pngs.PAGE_SLUGS))
    assert cli.main(["export-pngs", "--pdf", str(pdf)]) == 0
    assert len(list((tmp_path / "png").glob("*.png"))) == len(pngs.PAGE_SLUGS)
```

- [ ] **Step 3: Run them.** `pytest tests/test_pngs.py -v`. Expected: FAIL with `ImportError: cannot import name 'pngs'`.

- [ ] **Step 4: Implement.** Create `src/marche_stats/pngs.py`:

```python
"""One PNG per report page, rendered from the PDF that Power BI Desktop exports.

Desktop exports the visible pages in navigation order; the file names follow that order.
"""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

PAGE_SLUGS = (
    "01-overview",
    "02-population-health",
    "03-economy-labour",
    "04-education",
    "05-provinces",
    "06-business",
    "07-benchmark",
    "08-about",
)


def export(pdf: Path, out_dir: Path, width: int = 1600) -> list[Path]:
    """Render every page of the PDF to out_dir/<slug>.png, width pixels wide."""
    document = pdfium.PdfDocument(str(pdf))
    try:
        if len(document) != len(PAGE_SLUGS):
            raise ValueError(
                f"{pdf.name} has {len(document)} pages; expected {len(PAGE_SLUGS)}, "
                "the visible report pages"
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for index, slug in enumerate(PAGE_SLUGS):
            page = document[index]
            image = page.render(scale=width / page.get_width()).to_pil()
            path = out_dir / f"{slug}.png"
            image.save(path, optimize=True)
            paths.append(path)
        return paths
    finally:
        document.close()
```

In `cli.py`: add `pngs` to the `from marche_stats import …` line; add `"export-pngs"` to the `step` choices; add the argument

```python
    parser.add_argument(
        "--pdf",
        type=Path,
        default=ROOT / "powerbi" / "exports" / "marche-regional-profile.pdf",
        help="PDF exported from Power BI Desktop (export-pngs)",
    )
```

and, before `if args.step == "check-sources":`,

```python
    if args.step == "export-pngs":
        for path in pngs.export(args.pdf, args.pdf.parent / "png"):
            print(path)
        return 0
```

- [ ] **Step 5: Run them.** `pytest tests/test_pngs.py -v`. Expected: PASS. Then `pytest -q`.

- [ ] **Step 6: Commit.**

```bash
ruff check src tests && ruff format src tests
git add requirements.txt src/marche_stats tests/test_pngs.py
git commit -m "Render one PNG per report page from the exported PDF"
```

---

### Task 6: New tables and short names in the model

**Files:**
- Create: `…/definition/tables/ProvinceShape.tmdl`, `Seasonality.tmdl`, `Benchmark.tmdl`, `Benchmark point.tmdl`, `Data source.tmdl`
- Modify: `…/definition/tables/ISCED.tmdl`, `Sector.tmdl`, `…/definition/model.tmdl`
- Test: `tests/test_powerbi_model.py`

`…` stands for `powerbi/marche-regional-profile.SemanticModel`.

- [ ] **Step 1: Write the failing test.** Append to `tests/test_powerbi_model.py`:

```python
def test_phase_b_tables_and_columns():
    tables = model_tables()
    for name in ("ProvinceShape", "Seasonality", "Benchmark", "Benchmark point", "Data source"):
        assert name in tables, name
    assert {"GeoCode", "Path", "LabelX", "LabelY"} <= tables["ProvinceShape"]["columns"]
    assert {"Month", "MonthName", "Effect"} <= tables["Seasonality"]["columns"]
    assert {"Benchmark", "Item", "ValueItem", "Order"} <= tables["Benchmark"]["columns"]
    assert {"Code", "Area", "Role", "Row", "Indicator", "Point"} <= tables["Benchmark point"][
        "columns"
    ]
    assert {"Source", "Order"} <= tables["Data source"]["columns"]
    assert "ShortName" in tables["ISCED"]["columns"]
    assert "ShortName" in tables["Sector"]["columns"]
```

- [ ] **Step 2: Run it.** `pytest tests/test_powerbi_model.py::test_phase_b_tables_and_columns -v`. Expected: FAIL on `ProvinceShape`.

- [ ] **Step 3: Create `tables/ProvinceShape.tmdl`.**

```
/// SVG outline and label point of each province, projected by marche-stats export-powerbi
/// into a 400 x 400 box (powerbi/data/province_shapes.csv). Read by the Map SVG measure.
table ProvinceShape
	isHidden

	column GeoCode
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: GeoCode

	column Path
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: Path

	column LabelX
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: LabelX

	column LabelY
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: LabelY

	partition ProvinceShape = m
		mode: import
		source =
				let
				    Source = Csv.Document(Web.Contents(RepoRawBase & "/powerbi/data/province_shapes.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
				    Renamed = Table.RenameColumns(Promoted, {{"geo", "GeoCode"}, {"path", "Path"}, {"label_x", "LabelX"}, {"label_y", "LabelY"}}),
				    Typed = Table.TransformColumnTypes(Renamed, {{"GeoCode", type text}, {"Path", type text}, {"LabelX", Int64.Type}, {"LabelY", Int64.Type}}, "en-US")
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 4: Create `tables/Seasonality.tmdl`.**

```
/// Average STL seasonal effect on active companies by calendar month
/// (powerbi/data/seasonality.csv, the profile of docs/results.md, section 3).
table Seasonality

	column Month
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: Month

	column MonthName
		dataType: string
		summarizeBy: none
		sourceColumn: MonthName
		sortByColumn: Month

	column Effect
		dataType: double
		isHidden
		formatString: +#,0;-#,0;0
		summarizeBy: sum
		sourceColumn: Effect

	partition Seasonality = m
		mode: import
		source =
				let
				    Source = Csv.Document(Web.Contents(RepoRawBase & "/powerbi/data/seasonality.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
				    Renamed = Table.RenameColumns(Promoted, {{"month", "Month"}, {"month_name", "MonthName"}, {"effect", "Effect"}}),
				    Typed = Table.TransformColumnTypes(Renamed, {{"Month", Int64.Type}, {"MonthName", type text}, {"Effect", type number}}, "en-US")
				in
				    Typed

	annotation PBI_ResultType = Table
```

- [ ] **Step 5: Create `tables/Benchmark.tmdl`.** The Overview buttons pick a benchmark without applying the `Compare to` calculation group to the whole page.

```
/// Benchmark chosen with the Overview buttons: the country, the EU or the peer average.
/// Item and ValueItem name the Compare to items that the KPI gap measures apply.
table Benchmark

	column Benchmark
		dataType: string
		summarizeBy: none
		sourceColumn: [Benchmark]
		sortByColumn: Order

	column Item
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: [Item]

	column ValueItem
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: [ValueItem]

	column Order
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: [Order]

	partition Benchmark = calculated
		mode: import
		source =
				VAR CountryName = CALCULATE ( SELECTEDVALUE ( Geo[Name] ), Geo[Role] = "Country" )
				RETURN
				    SELECTCOLUMNS (
				        { ( CountryName, "vs Country", "Country", 1 ), ( "EU", "vs EU", "EU", 2 ), ( "Peers", "vs Peers avg", "Peers avg", 3 ) },
				        "Benchmark", [Value1], "Item", [Value2], "ValueItem", [Value3], "Order", [Value4]
				    )
```

- [ ] **Step 6: Create `tables/Benchmark point.tmdl`.** One row per area and indicator, for the Benchmark dot plot.

```
/// One point per area of the comparison set and per indicator, for the Benchmark dot plot.
table 'Benchmark point'

	column Code
		dataType: string
		isHidden
		summarizeBy: none
		sourceColumn: [Code]

	column Area
		dataType: string
		summarizeBy: none
		sourceColumn: [Area]

	column Role
		dataType: string
		summarizeBy: none
		sourceColumn: [Role]

	column Row
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: [Row]

	column Indicator
		dataType: string
		summarizeBy: none
		sourceColumn: [Indicator]
		sortByColumn: Row

	column Point
		dataType: string
		summarizeBy: none
		sourceColumn: [Point]

	partition 'Benchmark point' = calculated
		mode: import
		source =
				VAR Areas = SELECTCOLUMNS ( FILTER ( Geo, Geo[Role] IN { "Focus", "Peer", "Country", "EU" } ), "Code", Geo[Code], "Area", Geo[Name], "Role", Geo[Role] )
				VAR Indicators = DATATABLE ( "Row", INTEGER, "Indicator", STRING, { { 1, "Population change, 5 years" }, { 2, "Aged 65+" }, { 3, "Deaths per 1,000" }, { 4, "GDP per inhabitant" }, { 5, "Unemployment" }, { 6, "Tertiary students per 1,000" } } )
				RETURN ADDCOLUMNS ( CROSSJOIN ( Areas, Indicators ), "Point", [Area] & " · " & [Indicator] )
```

- [ ] **Step 7: Create `tables/Data source.tmdl`.**

```
/// Sources listed in the About page's freshness table, in display order.
table 'Data source'

	column Source
		dataType: string
		summarizeBy: none
		sourceColumn: Source
		sortByColumn: Order

	column Order
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: Order

	partition 'Data source' = m
		mode: import
		source =
				#table(
				    type table [Source = text, Order = Int64.Type],
				    {
				        {"Population", 1}, {"Deaths", 2}, {"GDP, regions", 3}, {"GDP, provinces", 4},
				        {"Unemployment", 5}, {"Enrolment", 6}, {"Active companies", 7}, {"Forecast", 8}
				    }
				)

	annotation PBI_ResultType = Table
```

- [ ] **Step 8: Add `ShortName` to `ISCED.tmdl`.** Add the column after `Name`:

```
	column ShortName
		dataType: string
		summarizeBy: none
		sourceColumn: ShortName
		sortByColumn: SortOrder
```

and replace the partition's `#table(...)` with:

```
				#table(
				    type table [Code = text, Name = text, ShortName = text, SortOrder = Int64.Type, Group = text, IsTotal = logical],
				    {
				        {"ED0", "Early childhood education", "Early childhood", 0, "ISCED 0-3", false},
				        {"ED1", "Primary education", "Primary", 1, "ISCED 0-3", false},
				        {"ED2", "Lower secondary education", "Lower secondary", 2, "ISCED 0-3", false},
				        {"ED3", "Upper secondary education", "Upper secondary", 3, "ISCED 0-3", false},
				        {"ED4", "Post-secondary non-tertiary education", "Post-secondary", 4, "ISCED 4", false},
				        {"ED5", "Short-cycle tertiary education", "Short tertiary", 5, "ISCED 5-8", false},
				        {"ED6", "Bachelor's or equivalent", "Bachelor's", 6, "ISCED 5-8", false},
				        {"ED7", "Master's or equivalent", "Master's", 7, "ISCED 5-8", false},
				        {"ED8", "Doctoral or equivalent", "Doctoral", 8, "ISCED 5-8", false},
				        {"ED02-8", "All levels", "All levels", 9, "All", true}
				    }
				)
```

- [ ] **Step 9: Add `ShortName` to `Sector.tmdl`.** Add after `Name`:

```
	column ShortName
		dataType: string
		summarizeBy: none
		sourceColumn: ShortName
		sortByColumn: Code
```

and replace the `#table(...)`:

```
				#table(
				    type table [Code = text, Name = text, ShortName = text],
				    {
				        {"A", "Agriculture, forestry and fishing", "Agriculture"},
				        {"B", "Mining and quarrying", "Mining"},
				        {"C", "Manufacturing", "Manufacturing"},
				        {"D", "Electricity, gas, steam and air conditioning supply", "Energy"},
				        {"E", "Water supply, sewerage and waste management", "Water and waste"},
				        {"F", "Construction", "Construction"},
				        {"G", "Wholesale and retail trade, repair of motor vehicles", "Trade"},
				        {"H", "Transportation and storage", "Transport"},
				        {"I", "Accommodation and food service activities", "Hotels and food"},
				        {"J", "Information and communication", "Information"},
				        {"K", "Financial and insurance activities", "Finance"},
				        {"L", "Real estate activities", "Real estate"},
				        {"M", "Professional, scientific and technical activities", "Professional"},
				        {"N", "Administrative and support service activities", "Administrative"},
				        {"O", "Public administration and defence, compulsory social security", "Public administration"},
				        {"P", "Education", "Education"},
				        {"Q", "Human health and social work activities", "Health"},
				        {"R", "Arts, entertainment and recreation", "Arts and leisure"},
				        {"S", "Other service activities", "Other services"},
				        {"T", "Activities of households as employers", "Households"},
				        {"X", "Not classified", "Not classified"}
				    }
				)
```

- [ ] **Step 10: Reference the tables in `model.tmdl`.** Append:

```
ref table ProvinceShape
ref table Seasonality
ref table Benchmark
ref table 'Benchmark point'
ref table 'Data source'
```

and in the `PBI_QueryOrder` annotation add `"ProvinceShape","Seasonality","Data source"` after `"Reconciliation"`.

- [ ] **Step 11: Run the tests.** `pytest tests/test_powerbi_model.py -v`. Expected: all pass.

- [ ] **Step 12: Commit.**

```bash
git add powerbi/marche-regional-profile.SemanticModel tests/test_powerbi_model.py
git commit -m "Add the map, seasonality, benchmark and source tables to the model"
```

---

### Task 7: Measures for the visuals

All new measures go into `tables/_Measures.tmdl`, before `column Placeholder`, in the order given. Each block is copied as is (tabs).

**Files:**
- Modify: `…/definition/tables/_Measures.tmdl`
- Test: `tests/test_powerbi_model.py`

- [ ] **Step 1: Write the failing test.** Append:

```python
def test_report_visual_measures():
    assert {
        "Focus region name",
        "Country name",
        "Data up to",
        "Population (men, negative)",
        "Population (women)",
        "Students (women, negative)",
        "Students (men)",
        "Pyramid colour",
        "Education level colour",
        "Area colour",
        "Change colour",
        "Active companies at month-end",
        "Active companies, December",
        "Active companies index",
        "Sector change, ten largest",
        "Seasonal effect",
        "MAPE",
        "Forecast chart actual",
        "Forecast chart forecast",
        "Latest period",
        "Area name",
        "Flags text",
    } <= model_tables()["_Measures"]["measures"]
```

- [ ] **Step 2: Run it.** Expected: FAIL.

- [ ] **Step 3: Add the names and dates.**

```
	/// Name of the focus region (FocusRegion parameter), as GISCO spells it.
	measure 'Focus region name' = CALCULATE ( SELECTEDVALUE ( Geo[Name] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus" )
		displayFolder: Report text

	/// Name of the national benchmark (Country parameter).
	measure 'Country name' = CALCULATE ( SELECTEDVALUE ( Geo[Name] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Country" )
		displayFolder: Report text

	/// "Data up to <month year>": the latest date of any fact table, for the navigation bar.
	measure 'Data up to' =
			VAR Latest =
			    MAXX (
			        {
			            CALCULATE ( MAX ( Companies[Date] ), REMOVEFILTERS () ),
			            CALCULATE ( MAX ( Population[Date] ), REMOVEFILTERS () ),
			            CALCULATE ( MAX ( Unemployment[Date] ), REMOVEFILTERS () )
			        },
			        [Value]
			    )
			RETURN "Data up to " & FORMAT ( Latest, "mmm yyyy" )
		displayFolder: Report text

	/// Name of the area in context, for the tooltip pages.
	measure 'Area name' = SELECTEDVALUE ( Geo[Name] )
		displayFolder: Report text

	/// Eurostat flags of the area in context, in words, for the tooltip pages. Blank when none.
	measure 'Flags text' =
			VAR Flags =
			    {
			        ( "Population", [Population flag] ),
			        ( "Deaths", [Deaths flag] ),
			        ( "GDP", [GDP flag] ),
			        ( "Unemployment", [Unemployment flag] ),
			        ( "Enrolment", [Enrolment flag] )
			    }
			VAR Named = FILTER ( Flags, [Value2] <> "" )
			RETURN
			    IF (
			        COUNTROWS ( Named ) > 0,
			        "Eurostat flags: "
			            & CONCATENATEX (
			                Named,
			                [Value1] & " " & TRIM ( SUBSTITUTE ( SUBSTITUTE ( SUBSTITUTE ( [Value2], "p", " provisional" ), "e", " estimated" ), "b", " break in series" ) ),
			                "; "
			            )
			    )
		displayFolder: Report text

	/// Latest period of the source on the row of the About freshness table.
	measure 'Latest period' =
			SWITCH (
			    SELECTEDVALUE ( 'Data source'[Order] ),
			    1, "1 Jan " & FORMAT ( YEAR ( CALCULATE ( MAX ( Population[Date] ), REMOVEFILTERS () ) ), "0" ),
			    2, FORMAT ( YEAR ( CALCULATE ( MAX ( Deaths[Date] ), REMOVEFILTERS () ) ), "0" ),
			    3, FORMAT ( YEAR ( CALCULATE ( MAX ( GDP[Date] ), REMOVEFILTERS (), Geo[Level] <> "NUTS3" ) ), "0" ),
			    4, FORMAT ( YEAR ( CALCULATE ( MAX ( GDP[Date] ), REMOVEFILTERS (), Geo[Level] = "NUTS3" ) ), "0" ),
			    5, FORMAT ( YEAR ( CALCULATE ( MAX ( Unemployment[Date] ), REMOVEFILTERS () ) ), "0" ),
			    6, FORMAT ( YEAR ( CALCULATE ( MAX ( Enrolment[Date] ), REMOVEFILTERS () ) ), "0" ),
			    7, FORMAT ( CALCULATE ( MAX ( Companies[Date] ), REMOVEFILTERS () ), "mmm yyyy" ),
			    8, "to " & FORMAT ( CALCULATE ( MAX ( Forecast[Date] ), REMOVEFILTERS () ), "mmm yyyy" )
			)
		displayFolder: Report text
```

- [ ] **Step 4: Add the pyramid, butterfly and colour measures.**

```
	/// Men in each age band as negative numbers, so they draw to the left of the pyramid.
	/// The format string hides the sign.
	measure 'Population (men, negative)' = - CALCULATE ( [Population], Sex[Code] = "M" )
		formatString: #,0;#,0
		displayFolder: Report visuals

	/// Women in each age band, the right side of the pyramid.
	measure 'Population (women)' = CALCULATE ( [Population], Sex[Code] = "F" )
		formatString: #,0
		displayFolder: Report visuals

	/// Women enrolled at each level as negative numbers (left side of the butterfly chart).
	measure 'Students (women, negative)' = - CALCULATE ( [Students enrolled], Sex[Code] = "F" )
		formatString: #,0;#,0
		displayFolder: Report visuals

	/// Men enrolled at each level (right side of the butterfly chart).
	measure 'Students (men)' = CALCULATE ( [Students enrolled], Sex[Code] = "M" )
		formatString: #,0
		displayFolder: Report visuals

	/// Bar colour of the pyramid: accent for the bands aged 65 and over.
	measure 'Pyramid colour' = IF ( SELECTEDVALUE ( AgeGroup[BroadGroup] ) = "65+", "#00753A", "#6B746E" )
		displayFolder: Report visuals

	/// Bar colour of the butterfly chart: accent for the tertiary levels.
	measure 'Education level colour' = IF ( SELECTEDVALUE ( ISCED[Group] ) = "ISCED 5-8", "#00753A", "#6B746E" )
		displayFolder: Report visuals

	/// Bar colour by area role: accent for the focus region, text colour for the country and the
	/// EU (the fallback when a bar outline cannot be set per bar), grey for the peer regions.
	measure 'Area colour' = SWITCH ( SELECTEDVALUE ( Geo[Role] ), "Focus", "#00753A", "Country", "#15201A", "EU", "#15201A", "#6B746E" )
		displayFolder: Report visuals
```

- [ ] **Step 5: Add the business measures.**

```
	/// Active companies at the month-ends in context; for the focus region, the sum of its provinces.
	measure 'Active companies at month-end' =
			VAR Areas = VALUES ( Geo[Code] )
			VAR WithProvinces = UNION ( Areas, CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), TREATAS ( Areas, Geo[ParentCode] ) ) )
			RETURN CALCULATE ( SUM ( Companies[Companies] ), REMOVEFILTERS ( Geo ), TREATAS ( WithProvinces, Geo[Code] ) )
		formatString: #,0
		displayFolder: Report visuals

	/// Active companies on 31 December of each year in context.
	measure 'Active companies, December' = CALCULATE ( [Active companies at month-end], Calendar[MonthNumber] = 12 )
		formatString: #,0
		displayFolder: Report visuals

	/// Active companies in December as an index: the first full-year December = 100.
	measure 'Active companies index' =
			VAR FirstDec = CALCULATE ( MIN ( Companies[Date] ), REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( Geo ), Calendar[MonthNumber] = 12 )
			VAR Base = CALCULATE ( [Active companies at month-end], REMOVEFILTERS ( Calendar ), Calendar[Date] = FirstDec )
			RETURN DIVIDE ( 100 * [Active companies, December], Base )
		formatString: 0.0
		displayFolder: Report visuals

	/// Change since the first full-year December for the ten sections with most active
	/// companies. Blank for the other sections and for X (not classified).
	measure 'Sector change, ten largest' =
			VAR Size = RANKX ( FILTER ( ALL ( Sector ), Sector[Code] <> "X" ), [Active companies], , DESC )
			RETURN IF ( SELECTEDVALUE ( Sector[Code] ) <> "X" && Size <= 10, [Active companies change %] )
		formatString: +0.0%;-0.0%;0.0%
		displayFolder: Report visuals

	/// Bar colour of the sector chart: accent for the growing sections.
	measure 'Change colour' = IF ( [Sector change, ten largest] > 0, "#00753A", "#6B746E" )
		displayFolder: Report visuals

	/// Average seasonal effect of the calendar month, in active companies.
	measure 'Seasonal effect' = SUM ( Seasonality[Effect] )
		formatString: +#,0;-#,0;0
		displayFolder: Report visuals

	/// Mean absolute percentage error of the method in context on the holdout months.
	measure MAPE = DIVIDE ( SUM ( ForecastAccuracy[MAPE] ), 100 )
		formatString: 0.00%
		displayFolder: Report visuals

	/// Modelled companies in the last 24 months of the series, for the forecast chart.
	measure 'Forecast chart actual' =
			VAR LastActual = CALCULATE ( MAX ( Forecast[Date] ), REMOVEFILTERS (), NOT ISBLANK ( Forecast[Actual] ) )
			RETURN IF ( MAX ( Calendar[Date] ) > EOMONTH ( LastActual, -24 ), [Modelled companies] )
		formatString: #,0
		displayFolder: Report visuals

	/// SARIMA forecast, starting from the last actual month so the two lines join.
	measure 'Forecast chart forecast' =
			VAR LastActual = CALCULATE ( MAX ( Forecast[Date] ), REMOVEFILTERS (), NOT ISBLANK ( Forecast[Actual] ) )
			RETURN IF ( MAX ( Calendar[Date] ) = LastActual, [Modelled companies], [SARIMA forecast] )
		formatString: #,0
		displayFolder: Report visuals
```

- [ ] **Step 6: Run the model tests.** `pytest tests/test_powerbi_model.py -v`. Expected: all pass (`test_measure_column_references_exist` checks every `Table[Column]` above).

- [ ] **Step 7: Commit.**

```bash
git add powerbi/marche-regional-profile.SemanticModel tests/test_powerbi_model.py
git commit -m "Add the measures behind the report charts and colours"
```

---

### Task 8: KPI gaps, provinces, map SVG and dot plot

**Files:**
- Modify: `…/definition/tables/_Measures.tmdl`
- Test: `tests/test_powerbi_model.py`

- [ ] **Step 1: Write the failing test.** Append:

```python
def test_kpi_province_map_and_dot_measures():
    assert {
        "KPI gap Population",
        "KPI gap Share aged 65+",
        "KPI gap Crude death rate",
        "KPI gap Unemployment rate",
        "KPI gap GDP per inhabitant",
        "KPI gap Active companies",
        "Province indicator value",
        "Province indicator label",
        "Province gap to region",
        "Highlight population change",
        "Highlight aged 65+",
        "Highlight death rate",
        "Highlight companies",
        "Highlight GDP",
        "Map SVG",
        "Dot value",
        "Dot position",
        "Dot row",
        "Rank row label",
        "Benchmark years",
    } <= model_tables()["_Measures"]["measures"]
```

- [ ] **Step 2: Run it.** Expected: FAIL.

- [ ] **Step 3: Add the KPI gap measures.** The KPI cards on Overview filter `Geo[Role] = "Focus"`; the `Benchmark` buttons choose the comparison. `−` is U+2212.

```
	/// Five-year population change of the focus region and of the benchmark chosen on Overview.
	measure 'KPI gap Population' =
			VAR Label = SELECTEDVALUE ( Benchmark[Benchmark], [Country name] )
			VAR Item = SELECTEDVALUE ( Benchmark[ValueItem], "Country" )
			VAR Own = [Population change 5y %]
			VAR Other = CALCULATE ( [Population change 5y %], 'Compare to'[Comparison] = Item )
			RETURN
			    IF (
			        NOT ISBLANK ( Own ),
			        IF ( Own < 0, "−", "+" ) & FORMAT ( ABS ( Own ) * 100, "0.0" ) & " % in 5 years · " & Label & " "
			            & IF ( Other < 0, "−", "+" ) & FORMAT ( ABS ( Other ) * 100, "0.0" ) & " %"
			    )
		displayFolder: Report text

	/// Gap in the share aged 65+ to the benchmark chosen on Overview, in percentage points.
	measure 'KPI gap Share aged 65+' =
			VAR Label = SELECTEDVALUE ( Benchmark[Benchmark], [Country name] )
			VAR Item = SELECTEDVALUE ( Benchmark[Item], "vs Country" )
			VAR Gap = CALCULATE ( [Share aged 65+], 'Compare to'[Comparison] = Item )
			VAR Year = YEAR ( CALCULATE ( [_Ref date Population], REMOVEFILTERS ( AgeGroup ), AgeGroup[BroadGroup] = "65+" ) )
			RETURN IF ( NOT ISBLANK ( Gap ), IF ( Gap < 0, "−", "+" ) & FORMAT ( ABS ( Gap ) * 100, "0.0" ) & " pp vs " & Label & " · " & Year )
		displayFolder: Report text

	/// Gap in the crude death rate to the benchmark chosen on Overview.
	measure 'KPI gap Crude death rate' =
			VAR Label = SELECTEDVALUE ( Benchmark[Benchmark], [Country name] )
			VAR Item = SELECTEDVALUE ( Benchmark[Item], "vs Country" )
			VAR Gap = CALCULATE ( [Crude death rate per 1,000], 'Compare to'[Comparison] = Item )
			RETURN IF ( NOT ISBLANK ( Gap ), IF ( Gap < 0, "−", "+" ) & FORMAT ( ABS ( Gap ), "0.0" ) & " vs " & Label & " · " & YEAR ( [_Ref date Deaths] ) )
		displayFolder: Report text

	/// Gap in the unemployment rate to the benchmark chosen on Overview, in percentage points.
	measure 'KPI gap Unemployment rate' =
			VAR Label = SELECTEDVALUE ( Benchmark[Benchmark], [Country name] )
			VAR Item = SELECTEDVALUE ( Benchmark[Item], "vs Country" )
			VAR Gap = CALCULATE ( [Unemployment rate], 'Compare to'[Comparison] = Item )
			RETURN IF ( NOT ISBLANK ( Gap ), IF ( Gap < 0, "−", "+" ) & FORMAT ( ABS ( Gap ) * 100, "0.0" ) & " pp vs " & Label & " · " & YEAR ( [_Ref date Unemployment] ) )
		displayFolder: Report text

	/// Gap in GDP per inhabitant to the benchmark chosen on Overview, in euro.
	measure 'KPI gap GDP per inhabitant' =
			VAR Label = SELECTEDVALUE ( Benchmark[Benchmark], [Country name] )
			VAR Item = SELECTEDVALUE ( Benchmark[Item], "vs Country" )
			VAR Gap = CALCULATE ( [GDP per inhabitant (EUR)], 'Compare to'[Comparison] = Item )
			RETURN IF ( NOT ISBLANK ( Gap ), IF ( Gap < 0, "−€", "+€" ) & FORMAT ( ABS ( Gap ), "#,0" ) & " vs " & Label & " · " & YEAR ( [_Ref date GDP] ) )
		displayFolder: Report text

	/// Change in active companies since the first full-year December (no benchmark: the
	/// register covers the focus region only).
	measure 'KPI gap Active companies' =
			VAR Change = [Active companies change %]
			VAR FirstYear = YEAR ( CALCULATE ( MIN ( Companies[Date] ), REMOVEFILTERS (), Calendar[MonthNumber] = 12 ) )
			RETURN IF ( NOT ISBLANK ( Change ), IF ( Change < 0, "−", "+" ) & FORMAT ( ABS ( Change ) * 100, "0.0" ) & " % since December " & FirstYear )
		displayFolder: Report text
```

- [ ] **Step 4: Add the province measures.**

```
	/// Value of the indicator chosen in the Province indicator field parameter (default:
	/// companies per 1,000 residents), with that indicator's format.
	measure 'Province indicator value' =
			SWITCH (
			    SELECTEDVALUE ( 'Province indicator'[Province indicator Order], 3 ),
			    0, [Population change 5y %],
			    1, [Share aged 65+],
			    2, [Crude death rate per 1,000],
			    3, [Companies per 1,000 residents],
			    4, [GDP per inhabitant (EUR)]
			)
		formatStringDefinition = SWITCH ( SELECTEDVALUE ( 'Province indicator'[Province indicator Order], 3 ), 0, "+0.0%;-0.0%;0.0%", 1, "0.0%", 4, "#,0", "0.0" )
		displayFolder: Report visuals

	/// Province indicator value as text, as the map and the headlines print it.
	measure 'Province indicator label' =
			VAR v = [Province indicator value]
			RETURN
			    IF (
			        NOT ISBLANK ( v ),
			        SWITCH (
			            SELECTEDVALUE ( 'Province indicator'[Province indicator Order], 3 ),
			            0, IF ( v < 0, "−", "+" ) & FORMAT ( ABS ( v ) * 100, "0.0" ) & " %",
			            1, FORMAT ( v * 100, "0.0" ) & " %",
			            4, "€" & FORMAT ( v / 1000, "0.0" ) & "K",
			            FORMAT ( v, "0.0" )
			        )
			    )
		displayFolder: Report text

	/// Gap between the province and the focus region for the chosen indicator. GDP compares
	/// the same year: provincial GDP lags the regional series.
	measure 'Province gap to region' =
			VAR Order = SELECTEDVALUE ( 'Province indicator'[Province indicator Order], 3 )
			VAR Region = [Focus region name]
			VAR v = [Province indicator value]
			VAR d = [_Ref date GDP]
			VAR r =
			    IF (
			        Order = 4,
			        CALCULATE ( SUM ( GDP[Value] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", GDP[Date] = d, GDP[UnitCode] = "EUR_HAB" ),
			        CALCULATE ( [Province indicator value], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus" )
			    )
			VAR Gap = v - r
			RETURN
			    IF (
			        NOT ISBLANK ( v ) && NOT ISBLANK ( r ),
			        SWITCH (
			            Order,
			            0, IF ( Gap < 0, "−", "+" ) & FORMAT ( ABS ( Gap ) * 100, "0.0" ) & " pp vs " & Region,
			            1, IF ( Gap < 0, "−", "+" ) & FORMAT ( ABS ( Gap ) * 100, "0.0" ) & " pp vs " & Region,
			            4, IF ( Gap < 0, "−€", "+€" ) & FORMAT ( ABS ( Gap ), "#,0" ) & " vs " & Region & " · " & YEAR ( d ),
			            IF ( Gap < 0, "−", "+" ) & FORMAT ( ABS ( Gap ), "0.0" ) & " vs " & Region
			        )
			    )
		displayFolder: Report text

	/// Background of the Provinces table column when its indicator is the one on the map.
	measure 'Highlight population change' = IF ( SELECTEDVALUE ( 'Province indicator'[Province indicator], "Companies per 1,000 residents" ) = "Population change 5y %", "#D0E3D7" )
		displayFolder: Report visuals

	/// Background of the Provinces table column when its indicator is the one on the map.
	measure 'Highlight aged 65+' = IF ( SELECTEDVALUE ( 'Province indicator'[Province indicator], "Companies per 1,000 residents" ) = "Share aged 65+", "#D0E3D7" )
		displayFolder: Report visuals

	/// Background of the Provinces table column when its indicator is the one on the map.
	measure 'Highlight death rate' = IF ( SELECTEDVALUE ( 'Province indicator'[Province indicator], "Companies per 1,000 residents" ) = "Crude death rate per 1,000", "#D0E3D7" )
		displayFolder: Report visuals

	/// Background of the Provinces table column when its indicator is the one on the map.
	measure 'Highlight companies' = IF ( SELECTEDVALUE ( 'Province indicator'[Province indicator], "Companies per 1,000 residents" ) = "Companies per 1,000 residents", "#D0E3D7" )
		displayFolder: Report visuals

	/// Background of the Provinces table column when its indicator is the one on the map.
	measure 'Highlight GDP' = IF ( SELECTEDVALUE ( 'Province indicator'[Province indicator], "Companies per 1,000 residents" ) = "GDP per inhabitant (EUR)", "#D0E3D7" )
		displayFolder: Report visuals
```

- [ ] **Step 5: Add the map.** Four equal-interval classes between the lowest and the highest province, the accent tints of the spec, name and value printed on each province, legend on the right. `#` is written `%23` in the data URL.

```
	/// SVG map of the provinces for the indicator chosen in Province indicator: four equal
	/// classes between the lowest and highest province, each province labelled with its name
	/// and value, legend on the right. Shown in an Image visual (data category Image URL).
	measure 'Map SVG' =
			VAR Ind = SELECTEDVALUE ( 'Province indicator'[Province indicator Order], 3 )
			VAR IndName = SELECTEDVALUE ( 'Province indicator'[Province indicator], "Companies per 1,000 residents" )
			VAR Rows =
			    CALCULATETABLE (
			        ADDCOLUMNS (
			            VALUES ( Geo[Code] ),
			            "@name", CALCULATE ( SELECTEDVALUE ( Geo[Name] ) ),
			            "@v", [Province indicator value],
			            "@label", [Province indicator label],
			            "@path", LOOKUPVALUE ( ProvinceShape[Path], ProvinceShape[GeoCode], Geo[Code] ),
			            "@x", LOOKUPVALUE ( ProvinceShape[LabelX], ProvinceShape[GeoCode], Geo[Code] ),
			            "@y", LOOKUPVALUE ( ProvinceShape[LabelY], ProvinceShape[GeoCode], Geo[Code] )
			        ),
			        REMOVEFILTERS ( Geo ),
			        Geo[Role] = "Province"
			    )
			VAR Lo = MINX ( Rows, [@v] )
			VAR Hi = MAXX ( Rows, [@v] )
			VAR Step = ( Hi - Lo ) / 4
			VAR Classes =
			    ADDCOLUMNS (
			        Rows,
			        "@class", IF ( Step = 0, 4, MIN ( 4, INT ( ( [@v] - Lo ) / Step ) + 1 ) )
			    )
			VAR Painted =
			    ADDCOLUMNS (
			        Classes,
			        "@fill", SWITCH ( [@class], 1, "#D0E3D7", 2, "#7AB696", 3, "#4A9C72", "#00753A" ),
			        "@ink", IF ( [@class] = 4, "#F5F6F3", "#15201A" )
			    )
			VAR Shapes =
			    CONCATENATEX (
			        Painted,
			        "<path d='" & [@path] & "' fill='" & [@fill] & "' stroke='#F5F6F3' stroke-width='3' fill-rule='evenodd'/>",
			        ""
			    )
			VAR Labels =
			    CONCATENATEX (
			        Painted,
			        "<text x='" & [@x] & "' y='" & [@y] - 4 & "' text-anchor='middle' font-size='22' fill='" & [@ink] & "'>" & [@name] & "</text>"
			            & "<text x='" & [@x] & "' y='" & [@y] + 22 & "' text-anchor='middle' font-size='22' font-weight='600' fill='" & [@ink] & "'>" & [@label] & "</text>",
			        ""
			    )
			VAR Bounds = GENERATESERIES ( 1, 4, 1 )
			VAR Legend =
			    "<text x='424' y='40' font-size='22' fill='#4F5A53'>" & IndName & "</text>"
			        & CONCATENATEX (
			            Bounds,
			            VAR i = [Value]
			            VAR a = Lo + ( i - 1 ) * Step
			            VAR b = Lo + i * Step
			            VAR Fmt = SWITCH ( Ind, 0, FORMAT ( a * 100, "0.0" ) & " to " & FORMAT ( b * 100, "0.0" ) & " %", 1, FORMAT ( a * 100, "0.0" ) & " to " & FORMAT ( b * 100, "0.0" ) & " %", 4, "€" & FORMAT ( a / 1000, "0.0" ) & "K to " & FORMAT ( b / 1000, "0.0" ) & "K", FORMAT ( a, "0.0" ) & " to " & FORMAT ( b, "0.0" ) )
			            VAR y = 72 + ( 4 - i ) * 40
			            RETURN
			                "<rect x='424' y='" & y & "' width='32' height='24' fill='" & SWITCH ( i, 1, "#D0E3D7", 2, "#7AB696", 3, "#4A9C72", "#00753A" ) & "' stroke='#6B746E'/>"
			                    & "<text x='468' y='" & y + 19 & "' font-size='22' fill='#15201A'>" & Fmt & "</text>",
			            ""
			        )
			VAR Svg =
			    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 400' font-family='Segoe UI, sans-serif'>"
			        & Shapes & Labels & Legend & "</svg>"
			RETURN IF ( NOT ISBLANK ( Lo ), "data:image/svg+xml;utf8," & SUBSTITUTE ( Svg, "#", "%23" ) )
		dataCategory: ImageUrl
		displayFolder: Report visuals
```

- [ ] **Step 6: Add the dot plot and Benchmark helpers.**

```
	/// Value of the indicator on the row of Benchmark point, for the area of that row.
	measure 'Dot value' =
			VAR r = SELECTEDVALUE ( 'Benchmark point'[Row] )
			VAR c = SELECTEDVALUE ( 'Benchmark point'[Code] )
			RETURN
			    CALCULATE (
			        SWITCH ( r, 1, [Population change 5y %], 2, [Share aged 65+], 3, [Crude death rate per 1,000], 4, [GDP per inhabitant (EUR)], 5, [Unemployment rate], 6, [Tertiary students per 1,000 residents] ),
			        REMOVEFILTERS ( Geo ),
			        Geo[Code] = c
			    )
		displayFolder: Report visuals

	/// Position of the area between the lowest (0) and the highest (1) area for the indicator.
	measure 'Dot position' =
			VAR r = SELECTEDVALUE ( 'Benchmark point'[Row] )
			VAR v = [Dot value]
			VAR Others = CALCULATETABLE ( ADDCOLUMNS ( VALUES ( 'Benchmark point'[Code] ), "@v", [Dot value] ), REMOVEFILTERS ( 'Benchmark point' ), 'Benchmark point'[Row] = r )
			VAR Lo = MINX ( Others, [@v] )
			VAR Hi = MAXX ( Others, [@v] )
			RETURN IF ( NOT ISBLANK ( v ), DIVIDE ( v - Lo, Hi - Lo ) )
		formatString: 0.00
		displayFolder: Report visuals

	/// Row of the dot plot, negative so the first indicator is on top.
	measure 'Dot row' = - SELECTEDVALUE ( 'Benchmark point'[Row] )
		formatString: 0
		displayFolder: Report visuals

	/// Label of the Benchmark rank row, e.g. "Marche rank of 6".
	measure 'Rank row label' =
			[Focus region name] & " rank of "
			    & COUNTROWS ( CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer" } ) )
		displayFolder: Report text

	/// Years compared on the Benchmark page (the latest year common to the areas) and the rank direction.
	measure 'Benchmark years' =
			VAR yp = YEAR ( CALCULATE ( [_Ref date Population], REMOVEFILTERS ( Geo ), REMOVEFILTERS ( Calendar ) ) )
			VAR yo = YEAR ( CALCULATE ( [_Ref date Population], REMOVEFILTERS ( Geo ), REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( AgeGroup ), AgeGroup[BroadGroup] = "65+" ) )
			VAR yd = YEAR ( CALCULATE ( [_Ref date Deaths], REMOVEFILTERS ( Geo ), REMOVEFILTERS ( Calendar ) ) )
			VAR yg = YEAR ( CALCULATE ( [_Ref date GDP], REMOVEFILTERS ( Geo ), REMOVEFILTERS ( Calendar ) ) )
			VAR yu = YEAR ( CALCULATE ( [_Ref date Unemployment], REMOVEFILTERS ( Geo ), REMOVEFILTERS ( Calendar ) ) )
			VAR ye = YEAR ( CALCULATE ( [_Ref date Enrolment], REMOVEFILTERS ( Geo ), REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( ISCED ), ISCED[Group] = "ISCED 5-8" ) )
			RETURN
			    "Years: population change " & yp - 5 & "–" & yp & " · aged 65+ " & yo & " · deaths " & yd & " · GDP " & yg
			        & " · unemployment " & yu & " · tertiary " & ye & ". Rank 1 = highest value among the "
			        & [Focus region name] & " and its peers."
		displayFolder: Report text
```

- [ ] **Step 7: Run the model tests.** `pytest tests/test_powerbi_model.py -v`. Expected: all pass.

- [ ] **Step 8: Commit.**

```bash
git add powerbi/marche-regional-profile.SemanticModel tests/test_powerbi_model.py
git commit -m "Add the KPI gaps, the province map SVG and the benchmark dot plot measures"
```

---

### Task 9: Headlines and paragraphs

Each page has a headline lead (text colour), a headline accent (accent colour) and a paragraph. A headline states its claim only when the data support it, otherwise it falls back to a neutral title. Every measure removes the `Calendar` filter, so a year slicer on the page does not change the text.

**Files:**
- Modify: `…/definition/tables/_Measures.tmdl` (new measures; `Reconciliation status` wording)
- Test: `tests/test_powerbi_model.py`

- [ ] **Step 1: Write the failing test.** Append:

```python
REPORT_TEXT_PREFIXES = (
    "Overview",
    "Population",
    "Economy",
    "Education",
    "Provinces",
    "Business",
    "Benchmark",
    "About",
    "Province detail",
)


def test_report_text_measures():
    measures = model_tables()["_Measures"]["measures"]
    for prefix in REPORT_TEXT_PREFIXES:
        for part in ("headline lead", "headline accent", "paragraph"):
            assert f"{prefix} {part}" in measures
```

- [ ] **Step 2: Run it.** Expected: FAIL on `Overview headline lead`.

- [ ] **Step 3: Add the helpers.**

```
	/// Number of areas ranked on Benchmark: the focus region and its peers.
	measure '_Peer count' = COUNTROWS ( CALCULATETABLE ( VALUES ( Geo[Code] ), REMOVEFILTERS ( Geo ), Geo[Role] IN { "Focus", "Peer" } ) )
		isHidden
		displayFolder: _Helpers

	/// Rank of the focus region among its peers (1 = highest) for the five-year population change.
	measure '_Rank population change' = CALCULATE ( [Population change 5y %], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), 'Compare to'[Comparison] = "Rank among peers" )
		isHidden
		displayFolder: _Helpers

	/// Rank of the focus region among its peers (1 = highest) for the share aged 65+.
	measure '_Rank aged 65+' = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), 'Compare to'[Comparison] = "Rank among peers" )
		isHidden
		displayFolder: _Helpers

	/// Rank of the focus region among its peers (1 = highest) for the crude death rate.
	measure '_Rank death rate' = CALCULATE ( [Crude death rate per 1,000], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), 'Compare to'[Comparison] = "Rank among peers" )
		isHidden
		displayFolder: _Helpers

	/// Rank of the focus region among its peers (1 = highest) for GDP per inhabitant.
	measure '_Rank GDP' = CALCULATE ( [GDP per inhabitant (EUR)], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), 'Compare to'[Comparison] = "Rank among peers" )
		isHidden
		displayFolder: _Helpers

	/// Rank of the focus region among its peers (1 = highest) for the unemployment rate.
	measure '_Rank unemployment' = CALCULATE ( [Unemployment rate], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), 'Compare to'[Comparison] = "Rank among peers" )
		isHidden
		displayFolder: _Helpers

	/// Rank of the focus region among its peers (1 = highest) for tertiary students per 1,000 residents.
	measure '_Rank tertiary' = CALCULATE ( [Tertiary students per 1,000 residents], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), 'Compare to'[Comparison] = "Rank among peers" )
		isHidden
		displayFolder: _Helpers

	/// TRUE when the Overview claim holds: population falling over five years, a larger share
	/// aged 65+ than the country, fewer active companies than in the first December.
	measure '_Overview claim' =
			VAR Pop = CALCULATE ( [Population change 5y %], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR Old = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR OldCountry = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "Country", REMOVEFILTERS ( Calendar ) )
			VAR Firms = CALCULATE ( [Active companies change %], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus" )
			RETURN Pop < 0 && Old > OldCountry && Firms < 0
		isHidden
		displayFolder: _Helpers

	/// TRUE when trade, agriculture and manufacturing (ATECO G, A, C) all lost active companies
	/// and at least one of professional, real-estate and financial services (M, L, K) grew.
	measure '_Business claim' =
			VAR T = CALCULATETABLE ( ADDCOLUMNS ( VALUES ( Sector[Code] ), "@c", [Active companies change %] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Sector ) )
			RETURN MAXX ( FILTER ( T, Sector[Code] IN { "G", "A", "C" } ), [@c] ) < 0 && MAXX ( FILTER ( T, Sector[Code] IN { "M", "L", "K" } ), [@c] ) > 0
		isHidden
		displayFolder: _Helpers
```

- [ ] **Step 4: Overview, Population & Health, Economy & Labour.**

```
	/// Overview headline, first part. Claim in _Overview claim; neutral title otherwise.
	measure 'Overview headline lead' = IF ( [_Overview claim], "An older, smaller region with", "The " & [Focus region name] & " at a" )
		displayFolder: Report text

	/// Overview headline, accent part.
	measure 'Overview headline accent' = IF ( [_Overview claim], "fewer firms", "glance" )
		displayFolder: Report text

	/// Overview paragraph: population from the first to the latest year, share aged 65+,
	/// change in active companies.
	measure 'Overview paragraph' =
			VAR FirstDate = CALCULATE ( MIN ( Population[Date] ), REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus" )
			VAR PopFirst = CALCULATE ( SUM ( Population[Residents] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), Population[Date] = FirstDate, REMOVEFILTERS ( Sex ), Sex[Code] = "T", REMOVEFILTERS ( AgeGroup ), AgeGroup[Code] = "TOTAL" )
			VAR PopLast = CALCULATE ( [Population], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR LastYear = YEAR ( CALCULATE ( [_Ref date Population], REMOVEFILTERS ( Calendar ) ) )
			VAR Old = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR Firms = CALCULATE ( [Active companies change %], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus" )
			VAR FirstDec = YEAR ( CALCULATE ( MIN ( Companies[Date] ), REMOVEFILTERS (), Calendar[MonthNumber] = 12 ) )
			RETURN
			    "Residents " & IF ( PopLast < PopFirst, "fell", "rose" ) & " from " & FORMAT ( PopFirst / 1000000, "0.00" ) & " million in " & YEAR ( FirstDate )
			        & " to " & FORMAT ( PopLast / 1000000, "0.00" ) & " million in " & LastYear & ". "
			        & FORMAT ( Old * 100, "0.0" ) & " % are aged 65 or over. Active companies are "
			        & FORMAT ( ABS ( Firms ) * 100, "0.0" ) & " % " & IF ( Firms < 0, "fewer", "more" ) & " than in December " & FirstDec & "."
		displayFolder: Report text

	/// Population & Health headline, first part: "One resident in N is".
	measure 'Population headline lead' =
			VAR s = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR n = ROUND ( DIVIDE ( 1, s ), 0 )
			RETURN
			    IF (
			        NOT ISBLANK ( s ),
			        "One resident in " & SWITCH ( n, 2, "two", 3, "three", 4, "four", 5, "five", 6, "six", 7, "seven", 8, "eight", 9, "nine", FORMAT ( n, "0" ) ) & " is"
			    )
		displayFolder: Report text

	/// Population & Health headline, accent part.
	measure 'Population headline accent' = "65 or over"
		displayFolder: Report text

	/// Population & Health paragraph: share aged 65+ against the country and the EU, women per
	/// man among the over-85s.
	measure 'Population paragraph' =
			VAR d = CALCULATE ( [_Ref date Population], REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( AgeGroup ), AgeGroup[BroadGroup] = "65+" )
			VAR s = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR sc = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "Country", REMOVEFILTERS ( Calendar ) )
			VAR se = CALCULATE ( [Share aged 65+], REMOVEFILTERS ( Geo ), Geo[Role] = "EU", REMOVEFILTERS ( Calendar ) )
			VAR Women = CALCULATE ( SUM ( Population[Residents] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), Population[Date] = d, REMOVEFILTERS ( Sex ), Sex[Code] = "F", REMOVEFILTERS ( AgeGroup ), AgeGroup[Code] IN { "Y85-89", "Y_GE90" } )
			VAR Men = CALCULATE ( SUM ( Population[Residents] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), Population[Date] = d, REMOVEFILTERS ( Sex ), Sex[Code] = "M", REMOVEFILTERS ( AgeGroup ), AgeGroup[Code] IN { "Y85-89", "Y_GE90" } )
			RETURN
			    FORMAT ( s * 100, "0.0" ) & " % on 1 January " & YEAR ( d ) & ", against " & FORMAT ( sc * 100, "0.0" ) & " % in " & [Country name]
			        & " and " & FORMAT ( se * 100, "0.0" ) & " % in the EU. Among the over-85s there are "
			        & FORMAT ( DIVIDE ( Women, Men ), "0.0" ) & " women for every man."
		displayFolder: Report text

	/// Gap in GDP per inhabitant between the focus region and the country, latest common year.
	measure '_Economy GDP gap' = CALCULATE ( [GDP per inhabitant (EUR)], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), 'Compare to'[Comparison] = "vs Country" )
		isHidden
		displayFolder: _Helpers

	/// Economy & Labour headline, first part.
	measure 'Economy headline lead' = "GDP per inhabitant is"
		displayFolder: Report text

	/// Economy & Labour headline, accent part: the gap to the country, rounded to €100.
	measure 'Economy headline accent' =
			VAR Gap = [_Economy GDP gap]
			RETURN IF ( NOT ISBLANK ( Gap ), "€" & FORMAT ( ROUND ( ABS ( Gap ), -2 ), "#,0" ) & IF ( Gap < 0, " below ", " above " ) & [Country name] )
		displayFolder: Report text

	/// Economy & Labour paragraph: GDP per inhabitant and its PPS index; unemployment from its
	/// peak to the latest year, against the country.
	measure 'Economy paragraph' =
			VAR g = CALCULATE ( [GDP per inhabitant (EUR)], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR pps = CALCULATE ( [GDP per inhabitant (PPS, EU = 100)], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR gy = YEAR ( CALCULATE ( [_Ref date GDP], REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( Geo ) ) )
			VAR Years = CALCULATETABLE ( ADDCOLUMNS ( VALUES ( Calendar[Year] ), "@u", [Unemployment rate] ), REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus" )
			VAR Peak = TOPN ( 1, FILTER ( Years, NOT ISBLANK ( [@u] ) ), [@u], DESC )
			VAR PeakRate = MAXX ( Peak, [@u] )
			VAR PeakYear = MAXX ( Peak, Calendar[Year] )
			VAR u = CALCULATE ( [Unemployment rate], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR uy = YEAR ( CALCULATE ( [_Ref date Unemployment], REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( Geo ) ) )
			VAR uc = CALCULATE ( [Unemployment rate], REMOVEFILTERS ( Geo ), Geo[Role] = "Country", REMOVEFILTERS ( Calendar ) )
			RETURN
			    "€" & FORMAT ( g, "#,0" ) & " in " & gy & ", " & FORMAT ( pps, "0" ) & " % of the EU average in purchasing power. Unemployment "
			        & IF ( PeakYear < uy && PeakRate > u, "fell from " & FORMAT ( PeakRate * 100, "0.0" ) & " % in " & PeakYear & " to ", "is " )
			        & FORMAT ( u * 100, "0.0" ) & " % in " & uy & ", against " & FORMAT ( uc * 100, "0.0" ) & " % in " & [Country name] & "."
		displayFolder: Report text
```

- [ ] **Step 5: Education, Provinces, Business.**

```
	/// Education headline, first part, from the focus region's rank among its peers for
	/// tertiary students per 1,000 residents.
	measure 'Education headline lead' =
			VAR r = [_Rank tertiary]
			VAR n = [_Peer count]
			RETURN SWITCH ( TRUE (), ISBLANK ( r ), "University students", r = n, "Fewer university students than", r = 1, "More university students than", "University students per resident:" )
		displayFolder: Report text

	/// Education headline, accent part.
	measure 'Education headline accent' =
			VAR r = [_Rank tertiary]
			VAR n = [_Peer count]
			RETURN SWITCH ( TRUE (), ISBLANK ( r ), "per 1,000 residents", r = n || r = 1, "every peer region", "rank " & r & " of " & n )
		displayFolder: Report text

	/// Education paragraph: tertiary students per 1,000 residents against the country and the
	/// EU; share of women among tertiary students.
	measure 'Education paragraph' =
			VAR d = CALCULATE ( [_Ref date Enrolment], REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( Geo ), REMOVEFILTERS ( ISCED ), ISCED[Group] = "ISCED 5-8" )
			VAR t = CALCULATE ( [Tertiary students per 1,000 residents], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ) )
			VAR tc = CALCULATE ( [Tertiary students per 1,000 residents], REMOVEFILTERS ( Geo ), Geo[Role] = "Country", REMOVEFILTERS ( Calendar ) )
			VAR te = CALCULATE ( [Tertiary students per 1,000 residents], REMOVEFILTERS ( Geo ), Geo[Role] = "EU", REMOVEFILTERS ( Calendar ) )
			VAR Women = CALCULATE ( SUM ( Enrolment[Students] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), Enrolment[Date] = d, REMOVEFILTERS ( Sex ), Sex[Code] = "F", REMOVEFILTERS ( ISCED ), ISCED[Group] = "ISCED 5-8" )
			VAR Everyone = CALCULATE ( SUM ( Enrolment[Students] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Calendar ), Enrolment[Date] = d, REMOVEFILTERS ( Sex ), Sex[Code] = "T", REMOVEFILTERS ( ISCED ), ISCED[Group] = "ISCED 5-8" )
			RETURN
			    FORMAT ( t, "0.0" ) & " tertiary students per 1,000 residents in " & YEAR ( d ) & ", against " & FORMAT ( tc, "0.0" ) & " in " & [Country name]
			        & " and " & FORMAT ( te, "0.0" ) & " in the EU. Women are " & FORMAT ( DIVIDE ( Women, Everyone ) * 100, "0" ) & " % of them."
		displayFolder: Report text

	/// Provinces headline, first part: the indicator on the map.
	measure 'Provinces headline lead' = SELECTEDVALUE ( 'Province indicator'[Province indicator], "Companies per 1,000 residents" ) & " is highest in"
		displayFolder: Report text

	/// Provinces headline, accent part: the province with the highest value.
	measure 'Provinces headline accent' =
			VAR Rows = CALCULATETABLE ( ADDCOLUMNS ( VALUES ( Geo[Name] ), "@v", [Province indicator value] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Province" )
			RETURN MAXX ( TOPN ( 1, FILTER ( Rows, NOT ISBLANK ( [@v] ) ), [@v], DESC ), Geo[Name] )
		displayFolder: Report text

	/// Provinces paragraph: highest and lowest province and the regional value.
	measure 'Provinces paragraph' =
			VAR Rows = CALCULATETABLE ( ADDCOLUMNS ( VALUES ( Geo[Name] ), "@v", [Province indicator value], "@label", [Province indicator label] ), REMOVEFILTERS ( Geo ), Geo[Role] = "Province" )
			VAR Valid = FILTER ( Rows, NOT ISBLANK ( [@v] ) )
			VAR Top = TOPN ( 1, Valid, [@v], DESC )
			VAR Bottom = TOPN ( 1, Valid, [@v], ASC )
			VAR Region = CALCULATE ( [Province indicator label], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus" )
			RETURN
			    MAXX ( Top, Geo[Name] ) & " " & MAXX ( Top, [@label] ) & ", against " & MAXX ( Bottom, [@label] ) & " in " & MAXX ( Bottom, Geo[Name] )
			        & ". The regional figure is " & Region & "."
		displayFolder: Report text

	/// Business headline, first part. Claim in _Business claim.
	measure 'Business headline lead' = IF ( [_Business claim], "Shops, farms and factories shrink;", "Active companies by sector:" )
		displayFolder: Report text

	/// Business headline, accent part.
	measure 'Business headline accent' =
			VAR Total = CALCULATE ( [Active companies change %], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Sector ) )
			RETURN IF ( [_Business claim], "services grow", IF ( Total < 0, "−", "+" ) & FORMAT ( ABS ( Total ) * 100, "0.0" ) & " % in total" )
		displayFolder: Report text

	/// Business paragraph: total change and the best and worst of the ten largest sections.
	measure 'Business paragraph' =
			VAR T =
			    CALCULATETABLE (
			        ADDCOLUMNS ( FILTER ( VALUES ( Sector[Code] ), Sector[Code] <> "X" ), "@name", CALCULATE ( SELECTEDVALUE ( Sector[ShortName] ) ), "@size", [Active companies], "@c", [Active companies change %] ),
			        REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Sector )
			    )
			VAR Largest = TOPN ( 10, T, [@size], DESC )
			VAR Best = TOPN ( 1, Largest, [@c], DESC )
			VAR Worst = TOPN ( 1, Largest, [@c], ASC )
			VAR b = MAXX ( Best, [@c] )
			VAR w = MAXX ( Worst, [@c] )
			VAR Total = CALCULATE ( [Active companies change %], REMOVEFILTERS ( Geo ), Geo[Role] = "Focus", REMOVEFILTERS ( Sector ) )
			VAR FirstYear = YEAR ( CALCULATE ( MIN ( Companies[Date] ), REMOVEFILTERS (), Calendar[MonthNumber] = 12 ) )
			VAR LastYear = YEAR ( CALCULATE ( MAX ( Companies[Date] ), REMOVEFILTERS (), Calendar[MonthNumber] = 12 ) )
			RETURN
			    FORMAT ( ABS ( Total ) * 100, "0.0" ) & " % " & IF ( Total < 0, "fewer", "more" ) & " active companies in December " & LastYear & " than in December " & FirstYear & ". "
			        & MAXX ( Best, [@name] ) & " did best (" & IF ( b < 0, "−", "+" ) & FORMAT ( ABS ( b ) * 100, "0.0" ) & " %); "
			        & MAXX ( Worst, [@name] ) & " did worst (" & IF ( w < 0, "−", "+" ) & FORMAT ( ABS ( w ) * 100, "0.0" ) & " %)."
		displayFolder: Report text
```

- [ ] **Step 6: Benchmark, About, Province detail.**

```
	/// Benchmark headline, first part.
	measure 'Benchmark headline lead' =
			VAR n = [_Peer count]
			VAR R = { [_Rank population change], [_Rank aged 65+], [_Rank death rate], [_Rank GDP], [_Rank unemployment], [_Rank tertiary] }
			VAR Mid = COUNTROWS ( FILTER ( R, [Value] > 1 && [Value] < n ) )
			VAR Extremes = COUNTROWS ( FILTER ( R, [Value] = 1 || [Value] = n ) )
			RETURN IF ( Extremes > 0 && Mid >= 3, "Mid-table, but", "Among its peers," )
		displayFolder: Report text

	/// Benchmark headline, accent part: the indicators where the focus region is lowest, else
	/// highest, among its peers.
	measure 'Benchmark headline accent' =
			VAR n = [_Peer count]
			VAR R =
			    {
			        ( "population change", [_Rank population change] ),
			        ( "the share aged 65+", [_Rank aged 65+] ),
			        ( "the death rate", [_Rank death rate] ),
			        ( "GDP per inhabitant", [_Rank GDP] ),
			        ( "unemployment", [_Rank unemployment] ),
			        ( "university students", [_Rank tertiary] )
			    }
			VAR Lowest = FILTER ( R, [Value2] = n )
			VAR Highest = FILTER ( R, [Value2] = 1 )
			RETURN
			    SWITCH (
			        TRUE (),
			        NOT ISEMPTY ( Lowest ), "lowest for " & CONCATENATEX ( Lowest, [Value1], " and " ),
			        NOT ISEMPTY ( Highest ), "highest for " & CONCATENATEX ( Highest, [Value1], " and " ),
			        "mid-table on every indicator"
			    )
		displayFolder: Report text

	/// Benchmark paragraph: the focus region's rank for each indicator.
	measure 'Benchmark paragraph' =
			"Ranks among the " & [Focus region name] & " and its " & [_Peer count] - 1 & " peers, 1 = highest: population change " & [_Rank population change]
			    & ", aged 65+ " & [_Rank aged 65+] & ", deaths per 1,000 " & [_Rank death rate] & ", GDP per inhabitant " & [_Rank GDP]
			    & ", unemployment " & [_Rank unemployment] & ", tertiary students " & [_Rank tertiary] & "."
		displayFolder: Report text

	/// About headline, first part.
	measure 'About headline lead' = "How this report is"
		displayFolder: Report text

	/// About headline, accent part.
	measure 'About headline accent' = "built and checked"
		displayFolder: Report text

	/// About paragraph, with the reconciliation result.
	measure 'About paragraph' =
			"Public data from Eurostat, GISCO and the Chamber of Commerce of the " & [Focus region name]
			    & ", refreshed in Power BI Desktop. A Python pipeline adds the SARIMA forecast and the totals the report must match: "
			    & CALCULATE ( [Reconciliation status], REMOVEFILTERS ( Reconciliation ) ) & "."
		displayFolder: Report text

	/// Province detail headline, first part: the province from the drill-through.
	measure 'Province detail headline lead' =
			VAR p = SELECTEDVALUE ( Geo[Name] )
			RETURN IF ( SELECTEDVALUE ( Geo[Role] ) = "Province", p & " against", "Right-click a province on" )
		displayFolder: Report text

	/// Province detail headline, accent part.
	measure 'Province detail headline accent' = IF ( SELECTEDVALUE ( Geo[Role] ) = "Province", "the " & [Focus region name], "the Provinces page" )
		displayFolder: Report text

	/// Province detail paragraph: population and its five-year change, companies per 1,000
	/// residents and their change since the first December.
	measure 'Province detail paragraph' =
			VAR Pop = [Population]
			VAR Change = [Population change 5y %]
			VAR Firms = [Active companies change %]
			VAR FirstYear = YEAR ( CALCULATE ( MIN ( Companies[Date] ), REMOVEFILTERS (), Calendar[MonthNumber] = 12 ) )
			RETURN
			    IF (
			        SELECTEDVALUE ( Geo[Role] ) = "Province",
			        "Population on 1 January " & YEAR ( [_Ref date Population] ) & ": " & FORMAT ( Pop, "#,0" ) & " (" & IF ( Change < 0, "−", "+" ) & FORMAT ( ABS ( Change ) * 100, "0.0" )
			            & " % in 5 years). Active companies: " & FORMAT ( [Companies per 1,000 residents], "0.0" ) & " per 1,000 residents, "
			            & IF ( Firms < 0, "−", "+" ) & FORMAT ( ABS ( Firms ) * 100, "0.0" ) & " % since December " & FirstYear & "."
			    )
		displayFolder: Report text
```

- [ ] **Step 7: Reword `Reconciliation status`.** The spec wants a word next to each symbol. Replace its expression and description with:

```
	/// "✓ Match" when Power BI matches the Python pipeline, otherwise "✗ Differs by" and the
	/// difference. Over several checkpoints: "✓ all N match" or "✗ K of N differ".
	measure 'Reconciliation status' =
			IF (
			    HASONEVALUE ( Reconciliation[Checkpoint] ),
			    VAR Expected = [Reconciliation expected]
			    VAR Diff = [Reconciliation in model] - Expected
			    RETURN IF ( NOT ISBLANK ( Expected ), IF ( Diff = 0, "✓ Match", "✗ Differs by " & FORMAT ( Diff, "+#,0;-#,0" ) ) ),
			    VAR Points = COUNTROWS ( VALUES ( Reconciliation[Checkpoint] ) )
			    VAR Failed = COUNTROWS ( FILTER ( VALUES ( Reconciliation[Checkpoint] ), [Reconciliation in model] <> [Reconciliation expected] ) )
			    RETURN IF ( Points > 0, IF ( Failed = 0, "✓ all " & Points & " match", "✗ " & Failed & " of " & Points & " differ" ) )
			)
		displayFolder: Checks
```

Keep its existing `lineageTag` line.

- [ ] **Step 8: Run the model tests.** `pytest tests/test_powerbi_model.py -v`. Expected: all pass.

- [ ] **Step 9: Commit.**

```bash
git add powerbi/marche-regional-profile.SemanticModel tests/test_powerbi_model.py
git commit -m "Add the data-driven headlines and paragraphs of every page"
```

---

### Task 10: Refresh in Power BI Desktop and check the new measures (user)

Only the user can run this task. The executor stops here and hands over these steps.

- [ ] **Step 1: Publish the branch, so the raw URLs of the two new CSV files resolve.** Ask the user before pushing (pushing is outward-facing):

```bash
git push -u origin powerbi-phase-b
```

- [ ] **Step 2: Point `RepoRawBase` at the branch, in Desktop only.** Open `powerbi/marche-regional-profile.pbip`. *Transform data → Manage parameters → RepoRawBase* = `https://raw.githubusercontent.com/simones99/marche-regional-stats/powerbi-phase-b`.

- [ ] **Step 3: Refresh.** Expected: every table loads, including `ProvinceShape` (5 rows), `Seasonality` (12 rows), `Benchmark` (3 rows: Italy, EU, Peers), `Benchmark point` (48 rows), `Data source` (8 rows). If Desktop rejects a measure, it names it: fix the DAX in Desktop, note the change, and the executor copies it back into this plan's task after Step 6.

- [ ] **Step 4: Check the text measures against the values of 13 October 2026.** On the hidden *Model check* page (or a scratch card, deleted afterwards), show each measure in a card:

| Measure | Expected |
|---|---|
| Overview headline lead / accent | An older, smaller region with / fewer firms |
| Overview paragraph | Residents fell from about 1.55 million in 2014 to 1.48 million in 2025. 26.6 % are aged 65 or over. Active companies are 17.1 % fewer than in December 2009. |
| Population headline lead | One resident in four is |
| Population paragraph | 26.6 % on 1 January 2025, against 24.7 % in Italy and 22.0 % in the EU. Among the over-85s there are 1.8 women for every man. |
| Economy headline accent | €3,200 below Italy |
| Economy paragraph | €34,100 in 2024, 89 % of the EU average in purchasing power. Unemployment fell from 11.0 % in 2013 to 5.1 % in 2025, against 6.1 % in Italy. |
| Education headline lead / accent | Fewer university students than / every peer region |
| Education paragraph | 34.7 tertiary students per 1,000 residents in 2024, against 39.2 in Italy and 42.4 in the EU. Women are 58 % of them. |
| Provinces headline (no selection) | Companies per 1,000 residents is highest in / Macerata |
| Provinces paragraph | Macerata 101.7, against 74.4 in Ancona. The regional figure is 88.5. |
| Business headline | Shops, farms and factories shrink; / services grow |
| Business paragraph | 17.1 % fewer active companies in December 2024 than in December 2009. Administrative did best (+48.0 %); Agriculture did worst (−35.2 %). |
| Benchmark headline | Mid-table, but / lowest for university students |
| Benchmark paragraph | Ranks among the Marche and its 5 peers, 1 = highest: population change 5, aged 65+ 3, deaths per 1,000 3, GDP per inhabitant 4, unemployment 3, tertiary students 6. |
| About paragraph | … the totals the report must match: ✓ all 12 match. |
| KPI gaps (no Benchmark selection) | −2.1 % in 5 years · Italy −1.2 % / +1.9 pp vs Italy · 2025 / +0.8 vs Italy · 2024 / −1.0 pp vs Italy · 2025 / −€3,200 vs Italy · 2024 / −17.1 % since December 2009 (cards filtered on the focus region) |
| Latest period (table on Data source) | 1 Jan 2025, 2024, 2024, 2023, 2025, 2024, Mar 2025, to Jan 2026 |
| Map SVG | Starts with `data:image/svg+xml;utf8,%3Csvg` or `data:image/svg+xml;utf8,<svg`; with a Table visual set to show it as an image, the five provinces appear with names and values |

A different number is a finding: compare it with `docs/results.md` and the Phase A check page before changing a measure.

- [ ] **Step 5: Delete the scratch cards, save, close Desktop.**

- [ ] **Step 6: Reset `RepoRawBase` and commit (executor).** In `…/definition/expressions.tmdl`, the `RepoRawBase` line must read exactly:

```
expression RepoRawBase = "https://raw.githubusercontent.com/simones99/marche-regional-stats/main" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

Desktop keeps the refreshed data in its local cache, so the report keeps working until the next refresh. Then:

```bash
pytest -q
git add powerbi/marche-regional-profile.SemanticModel powerbi/marche-regional-profile.Report
git commit -m "Save the model after refreshing the Phase B tables and measures"
```

---

### Task 11: Theme

**Files:**
- Create: `…Report/StaticResources/RegisteredResources/MarcheProfile.json`
- Modify: `…Report/definition/report.json`
- Delete: `…Report/StaticResources/SharedResources/BuiltInThemes/AccessibleCityPark.json`
- Test: `tests/test_powerbi_report.py` (new)

- [ ] **Step 1: Write the failing tests.** Create `tests/test_powerbi_report.py`:

```python
"""Static checks of the report against the Phase B rules (spec, Visual system and
Accessibility): palette, font minimum, registered resources, and, once pages exist, the
page list, the navigator, the 8 px grid and alt text.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "powerbi" / "marche-regional-profile.Report"
DEFINITION = REPORT / "definition"
RESOURCES = REPORT / "StaticResources" / "RegisteredResources"
THEME = RESOURCES / "MarcheProfile.json"
PALETTE = {
    "#F5F6F3",
    "#15201A",
    "#00753A",
    "#4F5A53",
    "#6B746E",
    "#ECEEEA",
    "#C9CEC9",
    "#D0E3D7",
    "#7AB696",
    "#4A9C72",
}
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
MIN_POINTS = 10.5  # 14 px


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _points(value) -> float:
    if isinstance(value, dict):
        value = value["expr"]["Literal"]["Value"]
    return float(str(value).removesuffix("pt").removesuffix("D"))


def font_sizes(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "fontSize":
                yield _points(value)
            else:
                yield from font_sizes(value)
    elif isinstance(node, list):
        for value in node:
            yield from font_sizes(value)


def colours(node) -> set[str]:
    return {c.upper() for c in HEX.findall(json.dumps(node))}


def test_theme_uses_the_palette_segoe_ui_and_the_font_minimum():
    theme = read(THEME)
    assert colours(theme) <= PALETTE
    assert theme["dataColors"][0] == "#00753A"
    assert all(size >= MIN_POINTS for size in font_sizes(theme))
    faces = re.findall(r'"font(?:Face|Family)": "([^"]+)"', json.dumps(theme))
    assert faces and all(face.startswith("Segoe UI") for face in faces)


def test_report_uses_the_registered_theme():
    report = read(DEFINITION / "report.json")
    assert report["themeCollection"]["customTheme"]["name"] == THEME.name
    assert report["themeCollection"]["customTheme"]["type"] == "RegisteredResources"


def test_registered_resources_exist_and_photos_are_small():
    report = read(DEFINITION / "report.json")
    for package in report["resourcePackages"]:
        if package["type"] != "RegisteredResources":
            continue
        for item in package["items"]:
            path = RESOURCES / item["path"]
            assert path.exists(), item["path"]
            if item["type"] == "Image":
                assert path.stat().st_size < 300_000, item["path"]
```

- [ ] **Step 2: Run them.** `pytest tests/test_powerbi_report.py -v`. Expected: FAIL (theme file missing).

- [ ] **Step 3: Create the theme** `…Report/StaticResources/RegisteredResources/MarcheProfile.json`:

```json
{
  "name": "Marche regional profile",
  "dataColors": ["#00753A", "#6B746E", "#15201A", "#4A9C72", "#7AB696", "#D0E3D7", "#4F5A53", "#C9CEC9"],
  "background": "#F5F6F3",
  "foreground": "#15201A",
  "tableAccent": "#00753A",
  "good": "#00753A",
  "neutral": "#6B746E",
  "bad": "#15201A",
  "maximum": "#00753A",
  "center": "#7AB696",
  "minimum": "#D0E3D7",
  "null": "#C9CEC9",
  "textClasses": {
    "callout": {"fontSize": 24, "fontFace": "Segoe UI Semibold", "color": "#15201A"},
    "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#15201A"},
    "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#15201A"},
    "label": {"fontSize": 10.5, "fontFace": "Segoe UI", "color": "#4F5A53"}
  },
  "visualStyles": {
    "page": {
      "*": {
        "background": [{"color": {"solid": {"color": "#F5F6F3"}}, "transparency": 0}],
        "outspace": [{"color": {"solid": {"color": "#F5F6F3"}}, "transparency": 0}]
      }
    },
    "*": {
      "*": {
        "background": [{"show": true, "color": {"solid": {"color": "#F5F6F3"}}, "transparency": 0}],
        "border": [{"show": false, "radius": 8}],
        "dropShadow": [{"show": false}],
        "title": [{"show": true, "fontColor": {"solid": {"color": "#15201A"}}, "fontSize": 12, "fontFamily": "Segoe UI Semibold"}],
        "categoryAxis": [{"fontSize": 10.5, "fontFamily": "Segoe UI", "labelColor": {"solid": {"color": "#4F5A53"}}, "showAxisTitle": false, "gridlineShow": false}],
        "valueAxis": [{"fontSize": 10.5, "fontFamily": "Segoe UI", "labelColor": {"solid": {"color": "#4F5A53"}}, "showAxisTitle": false, "gridlineColor": {"solid": {"color": "#C9CEC9"}}}],
        "legend": [{"show": false, "fontSize": 10.5, "labelColor": {"solid": {"color": "#4F5A53"}}}],
        "labels": [{"fontSize": 10.5, "color": {"solid": {"color": "#15201A"}}}]
      }
    },
    "lineChart": {"*": {"markers": [{"show": true}], "labels": [{"show": false}]}},
    "barChart": {"*": {"labels": [{"show": true}]}},
    "clusteredBarChart": {"*": {"labels": [{"show": true}]}},
    "clusteredColumnChart": {"*": {"labels": [{"show": true}]}},
    "card": {
      "*": {
        "categoryLabels": [{"show": false}],
        "labels": [{"color": {"solid": {"color": "#15201A"}}, "fontSize": 24, "fontFamily": "Segoe UI Semibold"}],
        "title": [{"show": false}]
      }
    },
    "multiRowCard": {"*": {"dataLabels": [{"fontSize": 12}], "categoryLabels": [{"fontSize": 10.5}]}},
    "tableEx": {"*": {"columnHeaders": [{"fontSize": 10.5, "fontColor": {"solid": {"color": "#4F5A53"}}}], "values": [{"fontSize": 10.5, "fontColorPrimary": {"solid": {"color": "#15201A"}}}]}},
    "pivotTable": {"*": {"columnHeaders": [{"fontSize": 10.5, "fontColor": {"solid": {"color": "#4F5A53"}}}], "values": [{"fontSize": 10.5, "fontColorPrimary": {"solid": {"color": "#15201A"}}}]}},
    "slicer": {"*": {"items": [{"fontSize": 10.5, "fontColor": {"solid": {"color": "#15201A"}}}], "header": [{"fontSize": 10.5}]}},
    "textbox": {"*": {"background": [{"show": false}], "title": [{"show": false}]}},
    "shape": {"*": {"background": [{"show": false}], "title": [{"show": false}]}},
    "image": {"*": {"background": [{"show": false}], "title": [{"show": false}]}},
    "pageNavigator": {"*": {"background": [{"show": false}], "title": [{"show": false}]}}
  }
}
```

- [ ] **Step 4: Register it.** In `report.json`, replace the `customTheme` object with

```json
    "customTheme": {
      "name": "MarcheProfile.json",
      "reportVersionAtImport": {
        "visual": "1.8.101",
        "report": "2.0.101",
        "page": "1.3.101"
      },
      "type": "RegisteredResources"
    }
```

and the `resourcePackages` array with

```json
  "resourcePackages": [
    {
      "name": "SharedResources",
      "type": "SharedResources",
      "items": [
        {
          "name": "CY24SU10",
          "path": "BaseThemes/CY24SU10.json",
          "type": "BaseTheme"
        }
      ]
    },
    {
      "name": "RegisteredResources",
      "type": "RegisteredResources",
      "items": [
        {
          "name": "MarcheProfile.json",
          "path": "MarcheProfile.json",
          "type": "CustomTheme"
        }
      ]
    }
  ],
```

Then delete `StaticResources/SharedResources/BuiltInThemes/AccessibleCityPark.json` (`git rm`).

- [ ] **Step 5: Run the tests.** `pytest tests/test_powerbi_report.py -v`. Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add -A powerbi/marche-regional-profile.Report tests/test_powerbi_report.py
git commit -m "Add the three-colour Segoe UI theme and register it in the report"
```

---

### Task 12: Photos

**Files:**
- Create: `…Report/StaticResources/RegisteredResources/photo-overview-valadier.jpg`, `photo-education-urbino.jpg`, `photo-about-due-sorelle.jpg`
- Modify: `…Report/definition/report.json`

- [ ] **Step 1: Download, crop and compress.** The slots are 384 × 304 (story column) and 576 × 160 (About strip); the files are twice that size for sharp exports. Save this script outside the repository (e.g. the scratch folder) and run it from the repository root:

```python
"""Fetch the three Commons photos at 1600 px and crop them to their report slots."""

import io
import sys
from pathlib import Path

import requests
from PIL import Image

OUT = Path("powerbi/marche-regional-profile.Report/StaticResources/RegisteredResources")
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "marche-regional-stats/0.1 (report photos)"}
PHOTOS = {
    "photo-overview-valadier.jpg": ("File:Tempio del Valadier dall'eremo.jpg", (768, 608)),
    "photo-education-urbino.jpg": ("File:Panorama (Urbino) - panoramio.jpg", (768, 608)),
    "photo-about-due-sorelle.jpg": ("File:Spiaggia due sorelle.jpg", (1152, 320)),
}

for name, (title, (width, height)) in PHOTOS.items():
    info = requests.get(
        API,
        params={"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url",
                "iiurlwidth": 1600, "format": "json"},
        headers=HEADERS, timeout=60,
    ).json()
    page = next(iter(info["query"]["pages"].values()))
    url = page["imageinfo"][0]["thumburl"]
    image = Image.open(io.BytesIO(requests.get(url, headers=HEADERS, timeout=60).content)).convert("RGB")
    scale = max(width / image.width, height / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left, top = (image.width - width) // 2, (image.height - height) // 2
    image = image.crop((left, top, left + width, top + height))
    path = OUT / name
    image.save(path, "JPEG", quality=82, optimize=True, progressive=True)
    print(path, path.stat().st_size, file=sys.stderr)
```

Expected: three files, each under 300 KB. Look at each: the Valadier temple and the Urbino skyline are centred; the Due Sorelle beach shows the cliff and the sea. If a crop cuts the subject, change `left`/`top` for that file and rerun.

- [ ] **Step 2: Register the images.** Add to the `RegisteredResources` items in `report.json`:

```json
        {
          "name": "photo-overview-valadier.jpg",
          "path": "photo-overview-valadier.jpg",
          "type": "Image"
        },
        {
          "name": "photo-education-urbino.jpg",
          "path": "photo-education-urbino.jpg",
          "type": "Image"
        },
        {
          "name": "photo-about-due-sorelle.jpg",
          "path": "photo-about-due-sorelle.jpg",
          "type": "Image"
        }
```

- [ ] **Step 3: Run the tests.** `pytest tests/test_powerbi_report.py -v`. Expected: PASS.

- [ ] **Step 4: Commit.**

```bash
git add powerbi/marche-regional-profile.Report
git commit -m "Add the Valadier, Urbino and Due Sorelle photos to the report resources"
```

---

### Task 13: PBIR writer

**Files:**
- Create: `src/marche_stats/pbir.py`
- Test: `tests/test_pbir.py`

- [ ] **Step 1: Write the failing tests.** Create `tests/test_pbir.py`:

```python
import json
import re

import pytest

from marche_stats import pbir
from marche_stats.pbir import C, M, Page, Visual


def test_object_id_is_stable_hex():
    name = pbir.object_id("overview", "kpi")
    assert name == pbir.object_id("overview", "kpi")
    assert re.fullmatch(r"[0-9a-f]{20}", name)
    assert name != pbir.object_id("overview", "kpi-2")


def test_literal_forms():
    assert pbir.literal("it's") == {"expr": {"Literal": {"Value": "'it''s'"}}}
    assert pbir.literal(10.5) == {"expr": {"Literal": {"Value": "10.5D"}}}
    assert pbir.literal(True) == {"expr": {"Literal": {"Value": "true"}}}


def test_visual_json_binds_fields_title_and_alt_text():
    visual = Visual(
        "bars",
        "clusteredBarChart",
        672,
        32,
        576,
        280,
        roles={"Category": [C("Geo", "Name")], "Y": [M("Share aged 65+")]},
        title="Share aged 65+",
        alt="Bar chart of the share aged 65+ by area",
        sort=(M("Share aged 65+"), "Descending"),
    )
    body = pbir.visual_json("page", visual, order=3)
    assert body["name"] == pbir.object_id("page", "bars")
    assert body["position"] == {
        "x": 672, "y": 32, "z": 3000, "height": 280, "width": 576, "tabOrder": 3000
    }
    query = body["visual"]["query"]
    assert query["queryState"]["Category"]["projections"][0]["queryRef"] == "Geo.Name"
    assert "Measure" in query["queryState"]["Y"]["projections"][0]["field"]
    assert query["sortDefinition"]["sort"][0]["direction"] == "Descending"
    container = body["visual"]["visualContainerObjects"]
    assert container["title"][0]["properties"]["text"] == pbir.literal("Share aged 65+")
    assert container["general"][0]["properties"]["altText"] == pbir.literal(
        "Bar chart of the share aged 65+ by area"
    )


def test_in_filter_lists_values():
    roles = pbir.in_filter(C("Geo", "Role"), ["Focus", "Peer"])
    condition = roles["filter"]["Where"][0]["Condition"]["In"]
    assert condition["Values"] == [
        [{"Literal": {"Value": "'Focus'"}}],
        [{"Literal": {"Value": "'Peer'"}}],
    ]
    band = pbir.in_filter(C("AgeGroup", "IsBand"), [True])
    assert band["filter"]["Where"][0]["Condition"]["In"]["Values"] == [
        [{"Literal": {"Value": "true"}}]
    ]


def test_hidden_page():
    body = pbir.page_json(Page("tip", "Tip", [], hidden=True, width=320, height=240))
    assert body["visibility"] == "HiddenInViewMode"
    assert (body["width"], body["height"]) == (320, 240)


def _definition(tmp_path):
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "pages.json").write_text(
        json.dumps({"pageOrder": ["old"], "activePageName": "old"}), encoding="utf-8"
    )
    return tmp_path


def test_scaffold_writes_new_pages_first_and_keeps_the_others(tmp_path):
    definition = _definition(tmp_path)
    page = Page("one", "One", [Visual("a", "shape", 0, 0, 8, 8)])
    assert pbir.scaffold([page], definition) == ["One"]
    meta = json.loads((definition / "pages" / "pages.json").read_text(encoding="utf-8"))
    page_id = pbir.object_id("one")
    assert meta["pageOrder"] == [page_id, "old"]
    assert meta["activePageName"] == page_id
    visual = definition / "pages" / page_id / "visuals" / pbir.object_id("one", "a") / "visual.json"
    assert visual.exists()


def test_scaffold_never_overwrites_a_page_without_force(tmp_path):
    definition = _definition(tmp_path)
    page = Page("one", "One", [Visual("a", "shape", 0, 0, 8, 8)])
    pbir.scaffold([page], definition)
    page_file = definition / "pages" / pbir.object_id("one") / "page.json"
    page_file.write_text("refined in Desktop", encoding="utf-8")
    assert pbir.scaffold([page], definition) == []
    assert page_file.read_text(encoding="utf-8") == "refined in Desktop"
    assert pbir.scaffold([page], definition, force=True) == ["One"]
    assert json.loads(page_file.read_text(encoding="utf-8"))["displayName"] == "One"


def test_duplicate_visual_keys_are_rejected(tmp_path):
    page = Page(
        "one", "One", [Visual("a", "shape", 0, 0, 8, 8), Visual("a", "shape", 8, 0, 8, 8)]
    )
    with pytest.raises(ValueError, match="duplicate"):
        pbir.scaffold([page], _definition(tmp_path))
```

- [ ] **Step 2: Run them.** `pytest tests/test_pbir.py -v`. Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement** `src/marche_stats/pbir.py`:

```python
"""Write Power BI report pages in the PBIR format from a compact layout.

A layout gives each visual a type, a position and the fields it shows. The formatting a
theme cannot set is done once in Power BI Desktop, so scaffold() never overwrites a page
folder that exists unless asked: after the first Desktop session, Desktop's files win.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

SCHEMAS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VISUAL_SCHEMA = f"{SCHEMAS}/visualContainer/2.13.0/schema.json"
PAGE_SCHEMA = f"{SCHEMAS}/page/2.1.0/schema.json"
HIDDEN = "HiddenInViewMode"


@dataclass(frozen=True)
class Field:
    """A model column or measure."""

    table: str
    name: str
    measure: bool = True


def M(name: str) -> Field:
    """A measure of the _Measures table."""
    return Field("_Measures", name)


def C(table: str, name: str) -> Field:
    """A column."""
    return Field(table, name, measure=False)


@dataclass(frozen=True)
class Visual:
    key: str
    type: str
    x: int
    y: int
    w: int
    h: int
    roles: dict[str, list[Field]] = field(default_factory=dict)
    title: str | None = None
    alt: str | None = None
    objects: dict | None = None
    filters: list[dict] = field(default_factory=list)
    sort: tuple[Field, str] | None = None


@dataclass(frozen=True)
class Page:
    key: str
    name: str
    visuals: list[Visual]
    hidden: bool = False
    width: int = 1280
    height: int = 720


def object_id(*parts: str) -> str:
    """Stable 20-character hex name, the form Desktop gives pages and visuals."""
    return hashlib.sha1("/".join(parts).encode("utf-8")).hexdigest()[:20]


def _literal_text(value: str | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return f"{value}D"
    return "'" + value.replace("'", "''") + "'"


def literal(value: str | float | bool) -> dict:
    return {"expr": {"Literal": {"Value": _literal_text(value)}}}


def solid(color: str) -> dict:
    return {"solid": {"color": literal(color)}}


def field_expr(f: Field) -> dict:
    kind = "Measure" if f.measure else "Column"
    return {kind: {"Expression": {"SourceRef": {"Entity": f.table}}, "Property": f.name}}


def projection(f: Field) -> dict:
    return {"field": field_expr(f), "queryRef": f"{f.table}.{f.name}", "nativeQueryRef": f.name}


def in_filter(column: Field, values: list[str | bool]) -> dict:
    """Visual-level filter keeping the rows whose column is one of the values."""
    alias = column.table[0].lower()
    return {
        "name": object_id("filter", column.table, column.name, *map(str, values)),
        "field": field_expr(column),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": alias, "Entity": column.table, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": alias}},
                                        "Property": column.name,
                                    }
                                }
                            ],
                            "Values": [[{"Literal": {"Value": _literal_text(v)}}] for v in values],
                        }
                    }
                }
            ],
        },
    }


def visual_json(page_key: str, v: Visual, order: int) -> dict:
    visual: dict = {"visualType": v.type}
    if v.roles:
        visual["query"] = {
            "queryState": {
                role: {"projections": [projection(f) for f in fields]}
                for role, fields in v.roles.items()
            }
        }
        if v.sort:
            sort_field, direction = v.sort
            visual["query"]["sortDefinition"] = {
                "sort": [{"field": field_expr(sort_field), "direction": direction}]
            }
    if v.objects:
        visual["objects"] = v.objects
    container = {}
    if v.title is not None:
        container["title"] = [{"properties": {"show": literal(True), "text": literal(v.title)}}]
    if v.alt is not None:
        container["general"] = [{"properties": {"altText": literal(v.alt)}}]
    if container:
        visual["visualContainerObjects"] = container
    visual["drillFilterOtherVisuals"] = True
    body = {
        "$schema": VISUAL_SCHEMA,
        "name": object_id(page_key, v.key),
        "position": {
            "x": v.x,
            "y": v.y,
            "z": order * 1000,
            "height": v.h,
            "width": v.w,
            "tabOrder": order * 1000,
        },
        "visual": visual,
    }
    if v.filters:
        body["filterConfig"] = {"filters": v.filters}
    return body


def page_json(p: Page) -> dict:
    body = {
        "$schema": PAGE_SCHEMA,
        "name": object_id(p.key),
        "displayName": p.name,
        "displayOption": "FitToPage",
        "height": p.height,
        "width": p.width,
    }
    if p.hidden:
        body["visibility"] = HIDDEN
    return body


def _write(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(body, indent=2, ensure_ascii=False) + "\n")


def scaffold(pages: list[Page], definition: Path, force: bool = False) -> list[str]:
    """Write the pages that do not exist yet (all of them with force); return their names.

    The layout's pages come first in pages.json, in layout order; pages the layout does not
    know (the Phase A model check page) keep their place after them.
    """
    for page in pages:
        keys = [v.key for v in page.visuals]
        duplicates = {k for k in keys if keys.count(k) > 1}
        if duplicates:
            raise ValueError(f"{page.name}: duplicate visual keys {sorted(duplicates)}")

    written = []
    pages_dir = definition / "pages"
    for page in pages:
        folder = pages_dir / object_id(page.key)
        if folder.exists():
            if not force:
                continue
            shutil.rmtree(folder)
        _write(folder / "page.json", page_json(page))
        for order, v in enumerate(page.visuals):
            _write(
                folder / "visuals" / object_id(page.key, v.key) / "visual.json",
                visual_json(page.key, v, order),
            )
        written.append(page.name)

    meta_path = pages_dir / "pages.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    ours = [object_id(p.key) for p in pages]
    meta["pageOrder"] = ours + [name for name in meta["pageOrder"] if name not in ours]
    meta["activePageName"] = ours[0]
    _write(meta_path, meta)
    return written
```

- [ ] **Step 4: Run them.** `pytest tests/test_pbir.py -v`. Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
ruff check src tests && ruff format src tests
git add src/marche_stats/pbir.py tests/test_pbir.py
git commit -m "Add a PBIR writer that scaffolds report pages without overwriting Desktop's work"
```

---

### Task 14: Layout of the common zones and the Overview page; `scaffold-report`

**Files:**
- Create: `src/marche_stats/report_layout.py`
- Modify: `src/marche_stats/cli.py`, `tests/test_powerbi_report.py`
- Creates (by running the step): `…Report/definition/pages/<Overview>/…`

- [ ] **Step 1: Write the failing layout tests.** Append to `tests/test_powerbi_report.py`, and add `from marche_stats import report_layout` to its imports:

```python
def written_pages():
    meta = read(DEFINITION / "pages" / "pages.json")
    for name in meta["pageOrder"]:
        folder = DEFINITION / "pages" / name
        visuals = [read(p) for p in sorted((folder / "visuals").glob("*/visual.json"))]
        yield read(folder / "page.json"), visuals


def layout_pages():
    return [(p, v) for p, v in written_pages() if p["displayName"] in report_layout.PAGE_NAMES]


def test_pages_follow_the_layout_order():
    names = [p["displayName"] for p, _ in written_pages()]
    assert names[: len(report_layout.PAGE_NAMES)] == report_layout.PAGE_NAMES
    assert names[-1] == "Model check"


def test_visible_pages_are_the_report_pages():
    visible = [
        p["displayName"] for p, _ in written_pages() if p.get("visibility") != "HiddenInViewMode"
    ]
    assert visible == [p.name for p in report_layout.pages() if not p.hidden]


def test_every_visible_page_has_the_navigator():
    for page, visuals in written_pages():
        if page.get("visibility") == "HiddenInViewMode":
            continue
        types = {v["visual"]["visualType"] for v in visuals}
        assert report_layout.NAVIGATOR_TYPE in types, page["displayName"]


def test_visuals_sit_on_the_grid_inside_the_page():
    for page, visuals in layout_pages():
        for v in visuals:
            pos, where = v["position"], f"{page['displayName']}: {v['name']}"
            assert pos["x"] % 8 == 0 and pos["y"] % 8 == 0, where
            for size in (pos["width"], pos["height"]):
                assert size < 8 or size % 8 == 0, where
            assert pos["x"] + pos["width"] <= page["width"], where
            assert pos["y"] + pos["height"] <= page["height"], where


def test_data_visuals_have_alt_text():
    for page, visuals in layout_pages():
        for v in visuals:
            if "query" not in v["visual"]:
                continue
            general = v["visual"].get("visualContainerObjects", {}).get("general", [{}])
            assert "altText" in general[0].get("properties", {}), (
                f"{page['displayName']}: {v['name']}"
            )


def test_pages_use_the_palette_and_the_font_minimum():
    for page, visuals in layout_pages():
        for v in visuals:
            assert colours(v) <= PALETTE, f"{page['displayName']}: {v['name']}"
            assert all(size >= MIN_POINTS for size in font_sizes(v)), v["name"]
```

- [ ] **Step 2: Run them.** `pytest tests/test_powerbi_report.py -v`. Expected: FAIL with `ImportError: cannot import name 'report_layout'`.

- [ ] **Step 3: Create** `src/marche_stats/report_layout.py` with the shared parts and the Overview page:

```python
"""Layout of the report pages: what goes where, in px on the 8 px grid.

Zones (Phase B spec, Visual system): navigation 0-192, story 192-640, dashboard 640-1280.
`marche-stats scaffold-report` writes each page once; the formatting a theme cannot set is
done in Power BI Desktop, and Desktop's saved files are then the source of truth.
"""

from __future__ import annotations

from marche_stats.pbir import C, Field, M, Page, Visual, in_filter, literal, solid

ACCENT, TEXT, MUTED = "#00753A", "#15201A", "#4F5A53"
BASE, SURFACE, RULE = "#F5F6F3", "#ECEEEA", "#C9CEC9"
NAVIGATOR_TYPE = "pageNavigator"

STORY_X, STORY_W = 224, 384
DASH_X, DASH_W = 672, 576
HALF_W, RIGHT_X = 280, 968
THIRD_W, THIRDS = 176, (672, 872, 1072)
SLOT_Y, SLOT_H = 344, 304

FOCUS = in_filter(C("Geo", "Role"), ["Focus"])
AREAS = in_filter(C("Geo", "Role"), ["Focus", "Peer", "Country", "EU"])
LINES = in_filter(C("Geo", "Role"), ["Focus", "Country", "EU"])
PROVINCES = in_filter(C("Geo", "Role"), ["Province"])


def shape(key: str, x: int, y: int, w: int, h: int, color: str) -> Visual:
    return Visual(
        key,
        "shape",
        x,
        y,
        w,
        h,
        objects={
            "shape": [{"properties": {"tileShape": literal("rectangle")}}],
            "fill": [{"properties": {"show": literal(True), "fillColor": solid(color)}}],
            "outline": [{"properties": {"show": literal(False)}}],
        },
    )


def textbox(
    key: str, x: int, y: int, w: int, h: int, lines: list[str] | str, color: str = MUTED
) -> Visual:
    """Static text, 10.5 pt. A line that starts with '# ' is a bold heading."""
    paragraphs = []
    for line in [lines] if isinstance(lines, str) else lines:
        bold = line.startswith("# ")
        style = {
            "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI",
            "fontSize": "10.5pt",
            "color": TEXT if bold else color,
        }
        paragraphs.append({"textRuns": [{"value": line.removeprefix("# "), "textStyle": style}]})
    return Visual(
        key, "textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paragraphs}}]}
    )


def card(
    key: str,
    x: int,
    y: int,
    w: int,
    h: int,
    measure: str,
    size: float = 12,
    color: str = TEXT,
    title: str | None = None,
    alt: str | None = None,
    filters: tuple[dict, ...] = (),
) -> Visual:
    """Classic card showing one measure (a number, or a text measure for the story)."""
    return Visual(
        key,
        "card",
        x,
        y,
        w,
        h,
        roles={"Values": [M(measure)]},
        title=title,
        alt=alt or measure,
        objects={
            "labels": [{"properties": {"color": solid(color), "fontSize": literal(size)}}],
            "categoryLabels": [{"properties": {"show": literal(False)}}],
        },
        filters=list(filters),
    )


def image(key: str, x: int, y: int, w: int, h: int, resource: str, alt: str) -> Visual:
    url = {
        "expr": {
            "ResourcePackageItem": {
                "PackageName": "RegisteredResources",
                "PackageType": 1,
                "ItemName": resource,
            }
        }
    }
    return Visual(
        key,
        "image",
        x,
        y,
        w,
        h,
        alt=alt,
        objects={
            "general": [{"properties": {"imageUrl": url}}],
            "imageScaling": [{"properties": {"imageScalingType": literal("Fill")}}],
        },
    )


def measure_image(key: str, x: int, y: int, w: int, h: int, measure: str, alt: str) -> Visual:
    """Image whose URL comes from a measure (data category Image URL)."""
    return Visual(
        key,
        "image",
        x,
        y,
        w,
        h,
        alt=alt,
        objects={
            "general": [{"properties": {"imageUrl": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": measure}}}}}],
            "imageScaling": [{"properties": {"imageScalingType": literal("Fit")}}],
        },
    )


def slicer(
    key: str,
    x: int,
    y: int,
    w: int,
    h: int,
    column: Field,
    alt: str,
    mode: str = "Basic",
    header: bool = False,
    filters: tuple[dict, ...] = (),
) -> Visual:
    return Visual(
        key,
        "slicer",
        x,
        y,
        w,
        h,
        roles={"Values": [column]},
        alt=alt,
        objects={
            "data": [{"properties": {"mode": literal(mode)}}],
            "selection": [{"properties": {"singleSelect": literal(True)}}],
            "header": [{"properties": {"show": literal(header)}}],
        },
        filters=list(filters),
    )


def chart(
    key: str,
    kind: str,
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    category: Field,
    values: list[Field],
    alt: str,
    series: Field | None = None,
    tooltips: list[Field] | None = None,
    filters: tuple[dict, ...] = (),
    sort: tuple[Field, str] | None = None,
) -> Visual:
    roles: dict[str, list[Field]] = {"Category": [category], "Y": values}
    if series:
        roles["Series"] = [series]
    if tooltips:
        roles["Tooltips"] = tooltips
    return Visual(
        key, kind, x, y, w, h, roles=roles, title=title, alt=alt, filters=list(filters), sort=sort
    )


def ranked_bars(
    key: str, x: int, y: int, w: int, h: int, title: str, measure: str, alt: str
) -> Visual:
    """Bars of the focus region, peers, country and EU, highest first."""
    return chart(
        key, "clusteredBarChart", x, y, w, h, title, C("Geo", "Name"), [M(measure)], alt,
        filters=(AREAS,), sort=(M(measure), "Descending"),
    )


def table(
    key: str, x: int, y: int, w: int, h: int, title: str, fields: list[Field], alt: str,
    filters: tuple[dict, ...] = (),
) -> Visual:
    return Visual(
        key, "tableEx", x, y, w, h, roles={"Values": fields}, title=title, alt=alt,
        filters=list(filters),
    )


def chrome(prefix: str, page_name: str) -> list[Visual]:
    """Navigation, the three zones and the story header (eyebrow, headline, paragraph)."""
    return [
        shape("nav", 0, 0, 192, 720, TEXT),
        shape("surface", 640, 0, 640, 720, SURFACE),
        shape("rule", 640, 0, 1, 720, RULE),
        textbox("nav-kicker", 24, 32, 144, 24, "Regional profile", color=RULE),
        card("nav-region", 24, 56, 144, 32, "Focus region name", size=18, color=BASE,
             alt="Focus region"),
        Visual("navigator", NAVIGATOR_TYPE, 16, 112, 160, 320),
        card("nav-data", 24, 656, 144, 32, "Data up to", size=10.5, color=RULE,
             alt="Latest data"),
        textbox("eyebrow", STORY_X, 32, STORY_W, 24, page_name.upper()),
        card("headline", STORY_X, 72, STORY_W, 96, f"{prefix} headline lead", size=30,
             alt="Headline"),
        card("headline-accent", STORY_X, 168, STORY_W, 48, f"{prefix} headline accent",
             size=30, color=ACCENT, alt="Headline, key phrase"),
        card("paragraph", STORY_X, 232, STORY_W, 96, f"{prefix} paragraph", alt="Summary"),
    ]


def source(text: str) -> Visual:
    return textbox("source", STORY_X, 664, STORY_W, 24, text)


KPIS = (
    ("population", "Population", "Population", "KPI gap Population"),
    ("aged-65", "Aged 65+", "Share aged 65+", "KPI gap Share aged 65+"),
    ("deaths", "Deaths per 1,000", "Crude death rate per 1,000", "KPI gap Crude death rate"),
    ("unemployment", "Unemployment", "Unemployment rate", "KPI gap Unemployment rate"),
    ("gdp", "GDP per inhabitant", "GDP per inhabitant (EUR)", "KPI gap GDP per inhabitant"),
    ("companies", "Active companies", "Active companies", "KPI gap Active companies"),
)


def overview() -> Page:
    v = chrome("Overview", "Overview")
    v.append(
        image(
            "photo", STORY_X, SLOT_Y, STORY_W, SLOT_H, "photo-overview-valadier.jpg",
            "The Tempio del Valadier, a white octagonal church under a rock overhang in the Frasassi gorge",
        )
    )
    v.append(source("Eurostat, Chamber of Commerce of the Marche · Photo: Kimahri88, CC0"))
    v.append(textbox("compare-label", DASH_X, 40, 280, 24, "Compare with"))
    v.append(
        slicer("benchmark", RIGHT_X, 32, HALF_W, 40, C("Benchmark", "Benchmark"),
               "Benchmark for the KPI gaps: country, EU or peer average")
    )
    for i, (key, title, value, gap) in enumerate(KPIS):
        x, y = THIRDS[i % 3], 96 + (i // 3) * 144
        v.append(card(f"kpi-{key}", x, y, THIRD_W, 88, value, size=24, title=title,
                      alt=f"{title} of the focus region", filters=(FOCUS,)))
        v.append(card(f"kpi-{key}-gap", x, y + 88, THIRD_W, 32, gap, size=10.5,
                      alt=f"{title}: gap to the benchmark", filters=(FOCUS,)))
    v.append(
        chart("population", "lineChart", DASH_X, 384, HALF_W, 304, "Population on 1 January",
              C("Calendar", "Year"), [M("Population")],
              "Line chart of the focus region's population on 1 January, by year",
              filters=(FOCUS,))
    )
    v.append(
        chart("companies", "lineChart", RIGHT_X, 384, HALF_W, 304,
              "Active companies in December", C("Calendar", "Year"),
              [M("Active companies, December")],
              "Line chart of the focus region's active companies in December, by year",
              filters=(FOCUS,))
    )
    return Page("overview", "Overview", v)


def pages() -> list[Page]:
    return [overview()]


PAGE_NAMES = [p.name for p in pages()]
```

Run `ruff format src` afterwards: it re-wraps the long lines; the content stays the same.

- [ ] **Step 4: Add the CLI step.** In `cli.py`: add `pbir, report_layout` to the `from marche_stats import …` line; add `"scaffold-report"` to the step choices; add

```python
    parser.add_argument(
        "--force", action="store_true", help="scaffold-report: overwrite existing pages"
    )
```

and, before `if args.step == "check-sources":`,

```python
    if args.step == "scaffold-report":
        definition = args.powerbi / "marche-regional-profile.Report" / "definition"
        written = pbir.scaffold(report_layout.pages(), definition, force=args.force)
        print("\n".join(f"wrote {name}" for name in written) or "no new pages")
        return 0
```

- [ ] **Step 5: Hide the model check page.** The tests expect only the report pages to be visible. In `…Report/definition/pages/5e0c7a1d9b3f2a4c6e81/page.json`, add after `"displayName": "Model check",`:

```json
  "visibility": "HiddenInViewMode",
```

- [ ] **Step 6: Scaffold the Overview page.** With Desktop closed:

```bash
marche-stats scaffold-report
```

Expected output: `wrote Overview`.

- [ ] **Step 7: Run the tests.** `pytest -q`. Expected: all pass, including `test_report_fields_exist_in_model` (Phase A), which checks every field of the new visuals.

- [ ] **Step 8: Commit.**

```bash
ruff check src tests && ruff format --check src tests
git add src/marche_stats tests powerbi/marche-regional-profile.Report
git commit -m "Scaffold the navigation, the story zone and the Overview page"
```

---

### Task 15: Desktop spike on the Overview page (user, then executor)

The PBIR forms of the textbox, shape, image, page navigator and card come from documentation and earlier projects, not from a Desktop save. This task checks them before seven more pages are generated.

- [ ] **Step 1 (user): Open the report.** Open `powerbi/marche-regional-profile.pbip`. Expected on Overview, against the canvas artboard "D · Story + dashboard":
  - the dark navigation bar with "Regional profile", the region name, the page navigator listing the visible pages (only Overview at this point; Model check is hidden) and "Data up to Mar 2025";
  - the light story column with OVERVIEW, the two-part headline, the paragraph, the Valadier photo and the source line;
  - the surface on the right with "Compare with", the benchmark buttons, six KPI cards with their gap lines, and the two line charts.

- [ ] **Step 2 (user): Fix what Desktop did not accept.** For each visual that is missing, blank or shows an error: delete it, insert the same visual type at the same position and size, bind the same fields (Task 14, `overview()`), and set the same title and alt text. Typical cases:
  - the page navigator (*Insert → Buttons → Navigator → Page navigator*);
  - the photo (*Insert → Image*, then pick `photo-overview-valadier.jpg` from the report's resources);
  - a textbox whose text is missing (*Insert → Text box*, type the text, Segoe UI 10.5 pt, colour `#4F5A53`).

  Then save and close Desktop. If the headline text does not wrap in the classic card, switch that card to the new *Card* visual, turn off its label, turn on text wrap, and save.

- [ ] **Step 3 (executor): Learn Desktop's form.** Run `git diff --stat powerbi/marche-regional-profile.Report` and `git diff` on each changed or new `visual.json`. For each visual type Desktop rewrote, update the matching helper in `report_layout.py` (`textbox`, `shape`, `image`, `measure_image`, `card`, `slicer`, or `NAVIGATOR_TYPE`) so that it writes what Desktop wrote: same `visualType`, same object and property names, same expression form. Keep positions, fields, titles and alt text as they are. Do not re-run `scaffold-report` on Overview (Desktop's files stay).

- [ ] **Step 4: Run the tests.** `pytest -q`. If `test_pages_use_the_palette_and_the_font_minimum` fails on a value Desktop wrote, set that value in Desktop to a palette colour or to 10.5 pt and save again.

- [ ] **Step 5: Commit.**

```bash
git add src/marche_stats powerbi/marche-regional-profile.Report
git commit -m "Match the PBIR writer to the visual JSON that Desktop saves"
```

---

### Task 16: Pages 2–4: Population & Health, Economy & Labour, Education

**Files:**
- Modify: `src/marche_stats/report_layout.py`

- [ ] **Step 1: Add the three page functions** before `def pages()`:

```python
def population() -> Page:
    v = chrome("Population", "Population & Health")
    v.append(
        slicer("year", STORY_X, SLOT_Y, 160, 64, C("Calendar", "Year"), "Year of the age pyramid",
               mode="Dropdown", header=True)
    )
    v.append(
        chart("deaths", "lineChart", STORY_X, 424, STORY_W, 224, "Deaths per 1,000 residents",
              C("Calendar", "Year"), [M("Crude death rate per 1,000")],
              "Line chart of the crude death rate by year for the focus region, the country and the EU",
              series=C("Geo", "Name"), filters=(LINES,))
    )
    v.append(source("Eurostat demo_r_pjangrp3, demo_r_magec3"))
    v.append(
        chart("pyramid", "barChart", DASH_X, 32, DASH_W, 352,
              "Residents by age and sex, 1 January (men left, women right)",
              C("AgeGroup", "Name"), [M("Population (men, negative)"), M("Population (women)")],
              "Population pyramid of the focus region by five-year age band; bands aged 65 and over in the accent colour",
              filters=(FOCUS, in_filter(C("AgeGroup", "IsBand"), [True])),
              sort=(C("AgeGroup", "Name"), "Descending"))
    )
    v.append(
        ranked_bars("aged-65", DASH_X, 408, DASH_W, 280, "Share aged 65+", "Share aged 65+",
                    "Bar chart of the share aged 65 and over for the focus region, peers, country and EU")
    )
    return Page("population", "Population & Health", v)


def economy() -> Page:
    v = chrome("Economy", "Economy & Labour")
    v.append(
        ranked_bars("gdp-rank", STORY_X, SLOT_Y, STORY_W, SLOT_H, "GDP per inhabitant, euro",
                    "GDP per inhabitant (EUR)",
                    "Bar chart of GDP per inhabitant for the focus region, peers, country and EU")
    )
    v.append(source("Eurostat nama_10r_2gdp, lfst_r_lfu3rt"))
    v.append(
        textbox("legend", DASH_X, 32, DASH_W, 24,
                "●  Focus region, solid      □  Country, dashed      ▲  EU-27, dotted")
    )
    v.append(
        chart("gdp", "lineChart", DASH_X, 80, DASH_W, 288, "GDP per inhabitant, euro",
              C("Calendar", "Year"), [M("GDP per inhabitant (EUR)")],
              "Line chart of GDP per inhabitant by year for the focus region, the country and the EU",
              series=C("Geo", "Name"), filters=(LINES,))
    )
    v.append(
        chart("unemployment", "lineChart", DASH_X, 392, DASH_W, 296,
              "Unemployment rate, ages 15-74", C("Calendar", "Year"), [M("Unemployment rate")],
              "Line chart of the unemployment rate by year for the focus region, the country and the EU",
              series=C("Geo", "Name"), filters=(LINES,))
    )
    return Page("economy", "Economy & Labour", v)


def education() -> Page:
    v = chrome("Education", "Education")
    v.append(
        image("photo", STORY_X, SLOT_Y, STORY_W, SLOT_H, "photo-education-urbino.jpg",
              "Urbino's historic centre with the cathedral dome and the towers of the Ducal Palace")
    )
    v.append(source("Eurostat educ_uoe_enra11 · Photo: Fabio Poggi, CC BY 3.0"))
    v.append(textbox("level-label", DASH_X, 40, 120, 24, "ISCED level"))
    v.append(
        slicer("level", 800, 32, 448, 40, C("ISCED", "Group"), "Filter by education level",
               filters=(in_filter(C("ISCED", "Group"), ["ISCED 0-3", "ISCED 4", "ISCED 5-8"]),))
    )
    v.append(
        chart("butterfly", "barChart", DASH_X, 96, DASH_W, 304,
              "Students enrolled by level and sex (women left, men right)",
              C("ISCED", "ShortName"), [M("Students (women, negative)"), M("Students (men)")],
              "Butterfly chart of students enrolled in the focus region by level and sex; tertiary levels in the accent colour",
              filters=(FOCUS, in_filter(C("ISCED", "IsTotal"), [False])),
              sort=(C("ISCED", "ShortName"), "Ascending"))
    )
    v.append(
        ranked_bars("tertiary", DASH_X, 424, DASH_W, 264, "Tertiary students per 1,000 residents",
                    "Tertiary students per 1,000 residents",
                    "Bar chart of tertiary students per 1,000 residents for the focus region, peers, country and EU")
    )
    return Page("education", "Education", v)
```

and change `pages()` to `return [overview(), population(), economy(), education()]`.

- [ ] **Step 2: Scaffold.** Desktop closed: `marche-stats scaffold-report`. Expected: `wrote Population & Health`, `wrote Economy & Labour`, `wrote Education` (Overview is skipped).

- [ ] **Step 3: Run the tests.** `pytest -q`. Expected: all pass.

- [ ] **Step 4: Commit.**

```bash
ruff check src tests && ruff format src tests
git add src/marche_stats powerbi/marche-regional-profile.Report
git commit -m "Scaffold the population, economy and education pages"
```

---

### Task 17: Pages 5–8: Provinces, Business deep dive, Benchmark, About

**Files:**
- Modify: `src/marche_stats/report_layout.py`

- [ ] **Step 1: Add the four page functions** before `def pages()`:

```python
PROVINCE_MEASURES = [
    "Population change 5y %",
    "Share aged 65+",
    "Crude death rate per 1,000",
    "Companies per 1,000 residents",
    "GDP per inhabitant (EUR)",
]
BENCHMARK_MEASURES = [
    "Population change 5y %",
    "Share aged 65+",
    "Crude death rate per 1,000",
    "GDP per inhabitant (EUR)",
    "Unemployment rate",
    "Tertiary students per 1,000 residents",
]


def provinces() -> Page:
    v = chrome("Provinces", "Provinces")
    v.append(
        slicer("indicator", STORY_X, SLOT_Y, STORY_W, SLOT_H,
               C("Province indicator", "Province indicator"), "Indicator shown on the map",
               header=True)
    )
    v.append(source("Eurostat, Chamber of Commerce · GISCO boundaries, © EuroGeographics"))
    v.append(
        measure_image("map", DASH_X, 32, DASH_W, 320, "Map SVG",
                      "Map of the provinces shaded by the selected indicator; each province shows its name and value")
    )
    v.append(
        table("table", DASH_X, 376, DASH_W, 280, "All indicators by province",
              [C("Geo", "Name"), *[M(m) for m in PROVINCE_MEASURES]],
              "Table of the five indicators by province", filters=(PROVINCES,))
    )
    v.append(
        textbox("drill-hint", DASH_X, 664, DASH_W, 24,
                "Right-click a province › Drill through › Province detail")
    )
    return Page("provinces", "Provinces", v)


def business() -> Page:
    v = chrome("Business", "Business deep dive · focus region only")
    v.append(
        chart("index", "lineChart", STORY_X, SLOT_Y, STORY_W, SLOT_H,
              "Active companies by province, December 2009 = 100", C("Calendar", "Year"),
              [M("Active companies index")],
              "Line chart of active companies by province as an index, first December = 100; one marker shape per province",
              series=C("Geo", "Name"), filters=(PROVINCES,))
    )
    v.append(source("Chamber of Commerce of the Marche · SARIMA by marche-stats"))
    v.append(
        chart("forecast", "lineChart", DASH_X, 32, DASH_W, 280,
              "Active companies: last 24 months and 12-month SARIMA forecast", C("Calendar", "Date"),
              [M("Forecast chart actual"), M("Forecast chart forecast")],
              "Line chart of active companies in the last 24 months and the SARIMA forecast for the next 12, with its 95 % interval",
              tooltips=[M("Forecast lower 95"), M("Forecast upper 95")])
    )
    v.append(
        chart("sectors", "clusteredBarChart", DASH_X, 336, HALF_W, 352,
              "Change by sector since December 2009", C("Sector", "ShortName"),
              [M("Sector change, ten largest")],
              "Bar chart of the change in active companies for the ten largest ATECO sections; growing sections in the accent colour",
              filters=(FOCUS,), sort=(M("Sector change, ten largest"), "Descending"))
    )
    v.append(
        chart("season", "clusteredColumnChart", RIGHT_X, 336, HALF_W, 184,
              "Seasonal effect by month", C("Seasonality", "MonthName"), [M("Seasonal effect")],
              "Column chart of the average seasonal effect on active companies by calendar month",
              sort=(C("Seasonality", "MonthName"), "Ascending"))
    )
    v.append(
        chart("mape", "clusteredBarChart", RIGHT_X, 536, HALF_W, 152,
              "Forecast error on the 24-month test (MAPE)", C("ForecastAccuracy", "Method"),
              [M("MAPE")],
              "Bar chart of the mean absolute percentage error of SARIMA and two naive forecasts",
              sort=(M("MAPE"), "Ascending"))
    )
    return Page("business", "Business deep dive", v)


def benchmark() -> Page:
    v = chrome("Benchmark", "Benchmark")
    v.append(
        textbox("dot-labels", STORY_X, SLOT_Y, 128, SLOT_H, [
            "Population change, 5 years", "Aged 65+", "Deaths per 1,000",
            "GDP per inhabitant", "Unemployment", "Tertiary students per 1,000",
        ])
    )
    v.append(
        Visual("dots", "scatterChart", 352, SLOT_Y, 256, SLOT_H,
               roles={"Category": [C("Benchmark point", "Point")],
                      "Series": [C("Benchmark point", "Role")],
                      "X": [M("Dot position")], "Y": [M("Dot row")]},
               title="Where the focus region sits, lowest to highest",
               alt="Dot plot of the focus region, its peers, the country and the EU for six indicators, from the lowest value on the left to the highest on the right")
    )
    v.append(source("Eurostat · peers set by the PeerRegions parameter"))
    v.append(textbox("show-label", DASH_X, 40, 120, 24, "Show"))
    v.append(
        slicer("compare", 800, 32, 448, 40, C("Compare to", "Comparison"),
               "Show values or differences from a benchmark",
               filters=(in_filter(C("Compare to", "Comparison"),
                                  ["Value", "vs Country", "vs EU", "vs Peers avg"]),))
    )
    v.append(
        Visual("matrix", "pivotTable", DASH_X, 96, DASH_W, 432,
               roles={"Rows": [C("Geo", "Name")], "Values": [M(m) for m in BENCHMARK_MEASURES]},
               title="Indicators by area",
               alt="Matrix of six indicators for the focus region, its peers, the country and the EU",
               filters=[AREAS])
    )
    v.append(
        table("ranks", DASH_X, 544, DASH_W, 64, "Rank among peers (1 = highest)",
              [M("Rank row label"), *[M(m) for m in BENCHMARK_MEASURES]],
              "Rank of the focus region among its peers for each indicator",
              filters=(FOCUS, in_filter(C("Compare to", "Comparison"), ["Rank among peers"])))
    )
    v.append(card("years", DASH_X, 624, DASH_W, 64, "Benchmark years", size=10.5, color=MUTED,
                  alt="Years compared and rank direction"))
    return Page("benchmark", "Benchmark", v)


def about() -> Page:
    v = chrome("About", "About")
    v.append(
        textbox("about-text", STORY_X, SLOT_Y, STORY_W, SLOT_H, [
            "# Sources",
            "Eurostat: population, deaths, GDP, unemployment, enrolment",
            "GISCO NUTS 2024: codes and province boundaries",
            "Chamber of Commerce of the Marche: active companies, 2009–2025",
            "# Limits",
            "Companies end in March 2025: ATECO 2025 replaces ATECO 2007 from April",
            "February 2025 is dropped: identical to January, so not updated",
            "Provincial GDP lags the regional series by a year",
            "# Refresh",
            "Open the .pbip in Power BI Desktop, choose Refresh, use anonymous access",
            "# Photos (Wikimedia Commons)",
            "Kimahri88, CC0 · Fabio Poggi, CC BY 3.0 · Gaspa, CC BY 2.0",
        ])
    )
    v.append(source("github.com/simones99/marche-regional-stats"))
    checkpoint = [C("Reconciliation", "Checkpoint"), M("Reconciliation in model"),
                  M("Reconciliation status")]
    v.append(
        table("reconciliation-a", DASH_X, 32, HALF_W, 256, "Reconciliation: region and north",
              checkpoint, "Reconciliation checkpoints for the region, Pesaro e Urbino and Ancona",
              filters=(in_filter(C("Reconciliation", "GeoCode"), ["ITI3", "ITI31", "ITI32"]),))
    )
    v.append(
        table("reconciliation-b", RIGHT_X, 32, HALF_W, 256, "Reconciliation: south",
              checkpoint, "Reconciliation checkpoints for Macerata, Ascoli Piceno and Fermo",
              filters=(in_filter(C("Reconciliation", "GeoCode"), ["ITI33", "ITI34", "ITI35"]),))
    )
    v.append(
        table("freshness", DASH_X, 312, DASH_W, 184, "Latest period per source",
              [C("Data source", "Source"), M("Latest period")],
              "Table of the latest period available for each source")
    )
    v.append(
        textbox("flags-note", DASH_X, 504, DASH_W, 24,
                "Tooltips mark Eurostat flags: p provisional, e estimated, b break in series.")
    )
    v.append(
        image("photo", DASH_X, 528, DASH_W, 160, "photo-about-due-sorelle.jpg",
              "The Spiaggia delle Due Sorelle, a white beach below the Conero cliffs, seen from above")
    )
    return Page("about", "About", v)
```

and change `pages()` to `return [overview(), population(), economy(), education(), provinces(), business(), benchmark(), about()]`.

- [ ] **Step 2: Scaffold.** Desktop closed: `marche-stats scaffold-report`. Expected: the four new pages.

- [ ] **Step 3: Run the tests.** `pytest -q`. Expected: all pass.

- [ ] **Step 4: Commit.**

```bash
ruff check src tests && ruff format src tests
git add src/marche_stats powerbi/marche-regional-profile.Report
git commit -m "Scaffold the provinces, business, benchmark and about pages"
```

---

### Task 18: Province detail and tooltip pages

**Files:**
- Modify: `src/marche_stats/report_layout.py`

- [ ] **Step 1: Add the hidden pages** before `def pages()`. The rows of the `Province indicator` field parameter have the same names as its measures, so `PROVINCE_MEASURES` (Task 17) also names the filter values:

```python
def province_detail() -> Page:
    v = chrome("Province detail", "Province detail")
    v.append(
        chart("index", "lineChart", STORY_X, SLOT_Y, STORY_W, SLOT_H,
              "Active companies, December 2009 = 100", C("Calendar", "Year"),
              [M("Active companies index")],
              "Line chart of the province's active companies as an index, first December = 100")
    )
    v.append(source("Eurostat, Chamber of Commerce of the Marche"))
    for i, name in enumerate(PROVINCE_MEASURES):
        only = in_filter(C("Province indicator", "Province indicator"), [name])
        x, y = THIRDS[i % 3], 32 + (i // 3) * 144
        v.append(card(f"kpi-{i}", x, y, THIRD_W, 88, "Province indicator value", size=24,
                      title=name, alt=f"{name} of the province", filters=(only,)))
        v.append(card(f"kpi-{i}-gap", x, y + 88, THIRD_W, 32, "Province gap to region",
                      size=10.5, alt=f"{name}: gap to the region", filters=(only,)))
    v.append(
        chart("sectors", "clusteredBarChart", DASH_X, 320, DASH_W, 368,
              "Change by sector since December 2009", C("Sector", "ShortName"),
              [M("Sector change, ten largest")],
              "Bar chart of the change in active companies in the province for its ten largest ATECO sections",
              sort=(M("Sector change, ten largest"), "Descending"))
    )
    return Page("province-detail", "Province detail", v, hidden=True)


def area_tooltip() -> Page:
    return Page(
        "area-tooltip",
        "Area tooltip",
        [
            card("name", 16, 16, 288, 32, "Area name", alt="Area"),
            Visual("values", "multiRowCard", 16, 56, 288, 136,
                   roles={"Values": [M(m) for m in BENCHMARK_MEASURES]},
                   alt="Indicators of the area"),
            card("flags", 16, 200, 288, 24, "Flags text", size=10.5, color=MUTED,
                 alt="Eurostat flags"),
        ],
        hidden=True,
        width=320,
        height=240,
    )


def province_tooltip() -> Page:
    return Page(
        "province-tooltip",
        "Province tooltip",
        [
            card("name", 16, 16, 288, 32, "Area name", alt="Province"),
            Visual("values", "multiRowCard", 16, 56, 288, 168,
                   roles={"Values": [M(m) for m in PROVINCE_MEASURES]},
                   alt="Indicators of the province"),
        ],
        hidden=True,
        width=320,
        height=240,
    )
```

and change `pages()` to append `province_detail(), area_tooltip(), province_tooltip()`.

- [ ] **Step 2: Scaffold and test.** Desktop closed: `marche-stats scaffold-report`, then `pytest -q`. Expected: three new pages; all tests pass.

- [ ] **Step 3: Commit.**

```bash
ruff check src tests && ruff format src tests
git add src/marche_stats powerbi/marche-regional-profile.Report
git commit -m "Scaffold the province detail and tooltip pages"
```

---

### Task 19: Refine every page in Power BI Desktop (user)

Only the user can run this task. Open the report and the design canvas side by side; for each page, compare with its artboard ("D · Story + dashboard" for Overview, "2 · …" to "8 · …" for the others) and apply the steps below. Save often; close Desktop at the end.

- [ ] **Step 1: Line charts (all pages).** In *Format → Lines* and *Markers*, per series:
  - focus region: accent `#00753A`, solid, 3 px, filled circle;
  - country: `#6B746E`, dashed, hollow square;
  - EU: `#6B746E`, dotted, filled triangle;
  - Business, province index: `#6B746E`, solid, one marker per province (circle, square, triangle, diamond, x).

  Turn on *Series labels* at the line end. Turn the legend off where series labels name the lines.

- [ ] **Step 2: Bar charts.**
  - Ranked bars (Population, Economy, Education): *Bars → Color → fx → Field value → `Area colour`*. If *Bars → Border* can be set per bar, outline the country and EU bars in `#6B746E` instead of the dark fill.
  - Pyramid: *fx → `Pyramid colour`* on both series; overlap 100 %; gap 20 %; legend off.
  - Butterfly: *fx → `Education level colour`*.
  - Sectors (Business, Province detail): *fx → `Change colour`*.
  - Data labels on, 10.5 pt.

- [ ] **Step 3: Forecast chart (Business).** Actual: `#15201A`, solid, filled circles. Forecast: `#15201A`, dashed, hollow circles. *Analytics → Error bars* on *Forecast chart forecast*: upper `Forecast upper 95`, lower `Forecast lower 95`, *Bar* off, *Band* on, `#6B746E` at 80 % transparency.

- [ ] **Step 4: Slicers and interactions.**
  - Set every button slicer to *Style: Tile*, single select, and the Overview benchmark to its first value (the country).
  - *Format → Edit interactions*:
    - the Population year slicer filters only the pyramid;
    - the Benchmark *Compare to* slicer filters only the matrix (none on the ranks table, the dot plot and the text cards);
    - the ISCED slicer filters only the butterfly chart.

- [ ] **Step 5: Provinces.** Map image: scaling *Fit*. Table: *Cell elements → Background color → fx → Field value* for each indicator column with its `Highlight …` measure.

- [ ] **Step 6: Drill-through and tooltips.**
  - Province detail: *Page information → Drill through → Add* `Geo[Name]`. Keep the back button Desktop adds and move it to x 576, y 32, 32 × 24.
  - Area tooltip and Province tooltip: *Page information → Allow use as tooltip*; canvas 320 × 240.
  - Point the ranked bars and the line charts to *Area tooltip* (*Format → Tooltips → Report page*), and the Provinces table to *Province tooltip*.

- [ ] **Step 7: Accessibility pass.**
  - *View → Selection → Tab order*: matches reading order (navigation, story, controls, visuals).
  - Every visual's alt text is set (*General → Alt text*).
  - Text cards: wrap on, label off.
  - Headline 30 pt; nothing under 10.5 pt.

- [ ] **Step 8: Save, close, and hand back.** The executor runs:

```bash
pytest -q
git add powerbi/marche-regional-profile.Report powerbi/marche-regional-profile.SemanticModel
git commit -m "Refine the report pages in Power BI Desktop"
```

If a test fails on a value set in Desktop (a colour outside the palette, a font under 10.5 pt, a visual off the grid), fix it in Desktop and save again.

---

### Task 20: Best Practice Analyzer in CI (timeboxed: 30 minutes)

Carried over from Phase A, Task 18. Record the outcome either way.

- [ ] **Step 1: Try Tabular Editor 2 on the TMDL folder.** Download `TabularEditor.Portable.zip` 2.27.2 from `https://github.com/TabularEditor/TabularEditor/releases/tag/2.27.2` and extract it to a new empty folder outside the repository, for example `$env:TEMP\te2`, then (PowerShell):

```powershell
& "$env:TEMP\te2\TabularEditor.exe" "powerbi\marche-regional-profile.SemanticModel\definition" -A "https://raw.githubusercontent.com/microsoft/Analysis-Services/master/BestPracticeRules/BPARules.json"
```

- [ ] **Step 2: Decide.**
  - **If it loads the model and lists rule results:** add a job `bpa` on `windows-latest` to `.github/workflows/ci.yml` that downloads the same zip and runs the same command with `-V` (fail on errors). Commit with "Run the Best Practice Analyzer on the semantic model in CI".
  - **If it cannot load a TMDL folder:** add one sentence under "Model" in `powerbi/README.md`: "Tabular Editor 2.27.2 cannot load the TMDL folder, so the Best Practice Analyzer does not run in CI." Commit with "Note why the Best Practice Analyzer is not in CI".

---

### Task 21: PDF and PNG exports

- [ ] **Step 1 (user): Export the PDF.** In Desktop: *File → Export → Export to PDF*, current values, without hidden pages. Save it as `powerbi/exports/marche-regional-profile.pdf`. Expected: 8 pages.

- [ ] **Step 2: Render the PNGs.**

```bash
marche-stats export-pngs
```

Expected: eight files `powerbi/exports/png/01-overview.png` … `08-about.png`, 1600 px wide. Open two of them: the text is sharp, the map and the photos are present (the map SVG and the photos must survive the export, spec "Risks").

- [ ] **Step 3: Commit.**

```bash
git add powerbi/exports
git commit -m "Export the report to PDF and one PNG per page"
```

---

### Task 22: Documentation

**Files:**
- Modify: `powerbi/README.md`, `powerbi/sources.md`, `README.md`

- [ ] **Step 1: Rewrite `powerbi/README.md`.** Keep the "Refresh" section as it is. Replace the paragraph starting "Phase A (this version)" and add sections, in this order:
  - **Pages:** a table with page, what it shows, and a link to its PNG in `exports/png/`.
  - **Visual system:** the grid (navigation 192, story 448, dashboard 640, split at the centre, 8 px), the three colours with their contrast ratios, Segoe UI and the sizes. Taken from the spec.
  - **Accessibility:** the nine rules of the spec.
  - **How the map works:** `marche-stats export-powerbi` projects the GISCO outlines into `data/province_shapes.csv`; the `Map SVG` measure writes the SVG; an Image visual shows it, so the map needs no map service and survives the PDF export.
  - **How the pages are built:** `marche-stats scaffold-report` writes each page once from `src/marche_stats/report_layout.py`; formatting is done in Desktop.
  - **Model:** keep the Phase A bullets; add the five new tables in one bullet.

- [ ] **Step 2: Extend `powerbi/sources.md`.** Change the row `Forecast, ForecastAccuracy, Reconciliation` to `Forecast, ForecastAccuracy, Reconciliation, Seasonality, ProvinceShape`. Then add:

```markdown
## Photos

| Page | Photo | Author | Licence |
|---|---|---|---|
| Overview | [Tempio del Valadier dall'eremo](https://commons.wikimedia.org/wiki/File:Tempio_del_Valadier_dall%27eremo.jpg) | Kimahri88 | CC0 1.0 |
| Education | [Panorama (Urbino)](https://commons.wikimedia.org/wiki/File:Panorama_(Urbino)_-_panoramio.jpg) | Fabio Poggi | CC BY 3.0 |
| About | [Spiaggia due sorelle](https://commons.wikimedia.org/wiki/File:Spiaggia_due_sorelle.jpg) | Gaspa | CC BY 2.0 |

The photos are cropped to their slots and compressed; no other change.
```

- [ ] **Step 3: Update the root `README.md`.** Add (or replace, if one exists) a section `## Power BI report` after "Main results", containing:
  - `![Overview page](powerbi/exports/png/01-overview.png)`;
  - a link to `powerbi/exports/marche-regional-profile.pdf`;
  - **What this demonstrates:** a reusable M function for Eurostat; a star schema keyed on NUTS codes; a calculation group with dynamic format strings; a field parameter; an SVG map drawn in DAX; data-driven headlines; Python → Power BI integration; in-report reconciliation; an accessible three-colour design.

- [ ] **Step 4: Commit.**

```bash
git add README.md powerbi/README.md powerbi/sources.md
git commit -m "Document the Phase B pages, design system, map and photo credits"
```

---

### Task 23: Final checks and hand-over

- [ ] **Step 1: Run everything.**

```bash
pytest -q
ruff check src tests
ruff format --check src tests
```

Expected: all pass. `grep -n "RepoRawBase =" powerbi/marche-regional-profile.SemanticModel/definition/expressions.tmdl` shows `…/main`.

- [ ] **Step 2: Tick this plan and record the outcome.** Tick every finished step in this file. Append a section "## Outcome (recorded <date>)" with:
  - what Task 15 changed in the PBIR writer;
  - the result of Task 20;
  - any measure fixed in Desktop in Task 10 and its final DAX;
  - any spec rule that Desktop could not meet, with the fallback used (e.g. benchmark bars in text colour instead of outlined).

  Commit with "Record the Phase B outcome".

- [ ] **Step 3: Open the pull request (ask the user first).** Push the branch and open a PR to `main`. In the description, list the pages, the checks and the outcome, and say that `marche-stats check-sources` reports `province_shapes.csv` and `seasonality.csv` as OK only after the merge (they are read from `main`). End the description with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Done when (Phase B)

- `pytest -q`, `ruff check src tests` and `ruff format --check src tests` pass.
- The eight report pages, the Province detail drill-through and the two tooltip pages open in Desktop without errors, and each page matches its canvas artboard after Task 19.
- The headlines and paragraphs show the values of Task 10, Step 4 (or the values that the data support on the day).
- `powerbi/exports/` holds the PDF and eight PNGs, with the map and photos visible.
- The READMEs and `sources.md` describe the pages, the design system, the map and the photo credits.
- After the merge, `marche-stats check-sources` reports every source as OK.
