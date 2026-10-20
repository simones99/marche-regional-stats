# Power BI report

`marche-regional-profile.pbip` is a Power BI project on the Marche region (NUTS 2 `ITI3`), its provinces and its neighbouring regions, against Italy and the EU. It replaces the two earlier reports (`marche-regionali-2025`, `marche-demography-education`), which remain in the git history.

The report has eight pages, a province drill-through, two tooltip pages and a hidden model check page. Exports: [PDF](exports/marche-regional-profile.pdf) and one PNG per page in [`exports/png/`](exports/png/). Design: [Phase A spec](../docs/superpowers/specs/2026-10-12-marche-regional-profile-report-design.md), [Phase B spec](../docs/superpowers/specs/2026-10-13-marche-regional-profile-phase-b-design.md).

## Pages

| Page | What it shows | PNG |
|---|---|---|
| Overview | Six KPI cards (population, share aged 65+, crude death rate, unemployment, GDP per inhabitant, active companies) with the gap to Italy, the EU or the neighbouring regions; population and active companies over time | [01](exports/png/01-overview.png) |
| Population & Health | Age pyramid of the region, share aged 65+ against the neighbouring regions, Italy and the EU, crude death rate since 2014 | [02](exports/png/02-population-health.png) |
| Economy & Labour | GDP per inhabitant ranked and over time, unemployment rate since 2009, the region against Italy and the EU | [03](exports/png/03-economy-labour.png) |
| Education | Students by level and sex (ISCED buttons), tertiary students per 1,000 residents against the neighbouring regions | [04](exports/png/04-education.png) |
| Provinces | SVG map of the indicator chosen with the field parameter, and a table of the five indicators by province; drill-through to Province detail | [05](exports/png/05-provinces.png) |
| Business deep dive | Active companies by province (December 2009 = 100), the last 24 months and the 12-month SARIMA forecast, change by ATECO section, seasonal effect by month, forecast error on the test period | [06](exports/png/06-business.png) |
| Benchmark | Dot plot of the region among its neighbours, Italy and the EU for six indicators; matrix of areas × indicators with the `Compare to` buttons and the region's rank | [07](exports/png/07-benchmark.png) |
| About | Sources, limits, refresh, photo credits; the 12 reconciliation checkpoints of `Companies` against Python; the latest period per source | [08](exports/png/08-about.png) |

Every page has the navigation, an eyebrow, a headline, a paragraph and a source line. Headlines and paragraphs are DAX text measures: each states its claim only when the data support it, and otherwise falls back to a neutral title.

## Visual system

Pages are 1280 × 720 px on an 8 px grid, in three zones:

| Zone | x | Width | Content |
|---|---|---|---|
| Navigation | 0 | 192 | Page navigator, region name, "Data up to …" |
| Story | 192 | 448 | Eyebrow, headline, paragraph, one visual or photo, source line |
| Dashboard | 640 | 640 | Controls, cards and charts on cards with 8 px corners |

The story and the dashboard split at the page centre.

Three colours; every grey is the text colour mixed into the base.

| Colour | Hex | Contrast on base |
|---|---|---|
| Base | `#F5F6F3` | — |
| Text | `#15201A` | 15.5 : 1 |
| Accent | `#00753A` | 5.4 : 1 |
| Muted text (tint) | `#4F5A53` | 6.6 : 1 |
| Benchmark grey (tint, graphics only) | `#6B746E` | 4.4 : 1 |

The accent marks the focus region and one key phrase per page. Other areas are grey, told apart by line style and marker shape (Italy dashed with squares, EU dotted with triangles, neighbouring regions solid with hollow circles).

Type is Segoe UI:

| Role | Size |
|---|---|
| Headline | 30 pt (40 px), semibold |
| KPI value | 24 pt (32 px), semibold |
| Region name | 18 pt (24 px), semibold |
| Body, card titles | 12 pt (16 px) |
| Labels, axes, legends, tables, navigation | 10.5 pt (14 px) |

The theme is `marche-regional-profile.Report/StaticResources/RegisteredResources/MarcheProfile.json`.

## Accessibility

1. Body 16 px (12 pt), labels and axes 14 px. Nothing smaller.
2. Text contrast at least 4.5 : 1; lines, bars and markers at least 3 : 1.
3. A marker on every point. When five or more lines share a chart, a marker every third year.
4. Values are written on bars and at line ends, so no legend lookup is needed.
5. The map prints each province's value, and a table next to it repeats the data.
6. Every visual has a title that says what and when, and alt text that names the chart and what it compares.
7. Tab order follows reading order: navigation, story, controls, visuals. Buttons are 40 px tall.
8. No red against green. Gaps carry a sign and a word ("+1.9 pp vs Italy").
9. A tooltip is never the only place a number appears.

## How the map works

`marche-stats export-powerbi` projects the GISCO province outlines into a 400 × 400 box and writes them to `data/province_shapes.csv`. The `Map SVG` measure classes the selected `Province indicator` into four shades, writes the SVG with the name and value of each province and a legend, and an Image visual shows it. The map needs no map service and survives the PDF export.

## How the pages are built

`marche-stats scaffold-report` writes each page once from `src/marche_stats/report_layout.py`: pages, zones, visuals, bindings, titles, alt text and tab order. Pages that already exist are left alone; `--force <page>` rewrites one (`overview`, `population`, …, `province-tooltip`). Formatting the theme cannot set is done in Power BI Desktop, and Desktop's saved files are then the source of truth.

`marche-stats export-pngs` renders `exports/marche-regional-profile.pdf` (exported from Desktop) to one PNG per page.

## Model

- A star schema keyed on NUTS codes. Dimensions: `Geo`, `Calendar` (daily, the date table), `Sex`, `AgeGroup`, `ISCED`, `Sector`. Facts: `Population`, `Deaths`, `GDP`, `Unemployment`, `Enrolment`, `Companies`, `Forecast`, plus the unrelated check tables `ForecastAccuracy` and `Reconciliation`.
- Power Query parameters choose the areas: `FocusRegion`, `PeerRegions`, `ProvinceRegions`, `Country`, `StartYear`. Every Eurostat query goes through one function, `fnEurostat`.
- The calculation group `Compare to` adds Country, EU, the average of the neighbouring regions, differences and rank to any indicator.
- Province rows are compared among provinces only: provincial GDP lags the regional series by a year, so Compare to is not used on province rows.
- `Companies` is cleaned in Power Query with the rules of `src/marche_stats/companies.py`.
- Phase B tables: `ProvinceShape` (map outlines) and `Seasonality` (seasonal effect by month), both from `data/`; `Benchmark` (the Overview comparison buttons), `Benchmark point` (the dot plot), `Tooltip indicator` (rows of the tooltip pages) and `Data source` (the About freshness table).
- The model check page shows the reconciliation of `Companies` with the totals that Python writes to `data/reconciliation.csv`, the indicators by area and the Compare to matrix.
- `data/` holds the files exported by `marche-stats export-powerbi`: the SARIMA forecast, its accuracy, the reconciliation totals, the province shapes and the seasonal effect.

## Refresh

Open `marche-regional-profile.pbip` in Power BI Desktop (Windows) and choose *Refresh*. All sources are public: use anonymous access. The data cache (`.pbi/cache.abf`) is not committed, so refresh after cloning.

`marche-stats check-sources` requests every source the model uses, from the TMDL files. It runs weekly in GitHub Actions.

Sources and query details: [sources.md](sources.md).
