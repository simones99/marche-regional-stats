# Marche regional profile: Power BI report design

Date: 2026-10-12. Status: approved in brainstorming, waiting for the implementation plan.

## Goal

Merge the two Power BI reports in `powerbi/` (`marche-regionali-2025`, `marche-demography-education`) into one English report for a BI portfolio. It shows Power BI skills on public data: Power Query, a star schema, DAX with a calculation group, and the integration of a Python analysis.

The report is a **regional profile plus a deep dive**. The profile covers population, economy, education and provinces, each against benchmark areas. The deep dive covers active companies and their forecast.

## Decisions

| Topic | Decision |
|---|---|
| Report type | Regional profile with benchmarks, plus a business deep dive |
| Language | English |
| Future extension (all Italian regions, AI) | Not built now. The model must be **region-ready**: keyed on NUTS codes and driven by parameters, so profiling another region means changing parameters, not rebuilding the model |
| Benchmarks | Integrated in each page **and** a dedicated Benchmark page |
| Business data and forecast | **Hybrid**. Power Query cleans the Chamber of Commerce file. Python exports only the SARIMA forecast, its accuracy and reconciliation totals |
| Time dimension | One daily `Calendar` table marked as the date table |
| Comparisons | One calculation group, `Compare to` |
| Distribution | GitHub only: `.pbip`, PDF export, PNG per page, README. The user has no Power BI Service licence. The report stays compatible with Publish to web: standard visuals only, no Python or R visuals, public sources |
| Delivery | Phase A: data, model and checks. Phase B: pages and design, after a dedicated design session |

## Pages

| # | Page | Content |
|---|---|---|
| 1 | Overview | KPI row with the latest value and the gap to the country (to the start of the series for active companies, which exist only for the focus region): population and its 5-year change, share aged 65+, crude death rate, unemployment rate, GDP per inhabitant, active companies. Population and active-company trends below |
| 2 | Population & Health | Age pyramid (sex × five-year group, selectable year), population trend, ageing and mortality against the peer regions |
| 3 | Economy & Labour | GDP per inhabitant and unemployment over time: focus region against peers, country and EU, with gap KPIs. Ranked bars replace the current "vs Marche" maps |
| 4 | Education | One page with an ISCED level slicer. Enrolments by level and sex, and tertiary students per 1,000 residents against peers |
| 5 | Provinces | Map of the NUTS 3 provinces with an indicator selector (field parameter), plus a comparison table. Drill-through to a province detail page |
| 6 | Business deep dive | Active companies, March 2009 to March 2025, on constant boundaries (February 2025 is dropped: identical to January in every cell, so not updated): province index (2009 = 100), change by ATECO section, monthly seasonality, SARIMA forecast with intervals and its out-of-sample accuracy against the naive baselines |
| 7 | Benchmark | Matrix of indicators × areas (focus, peers, country, EU) with conditional formatting and the rank among peers |
| 8 | About | Sources, method, limits, refresh instructions, data checks, link to the repository |

Hidden tooltip pages are rebuilt on the new indicators. A side navigation bar has one entry per page, and every entry works.

Removed from the current reports:
- placeholder sections (Public Finance, Society & Quality of Life, Infrastructure & Transportation);
- ISCED 4-8 buttons without pages;
- the scratch page "Page 1";
- pie charts by sex.

Power BI features shown on purpose:
- field parameter: indicator selector on Provinces;
- report page tooltips;
- drill-through: province detail;
- dynamic titles in DAX;
- conditional formatting: Benchmark;
- bookmarks, only where needed.

## Data model

A star schema. Every relationship uses NUTS or source codes, never labels.

### Power Query parameters

| Parameter | Default | Use |
|---|---|---|
| `FocusRegion` | `ITI3` | Region profiled. Its NUTS 3 children are the provinces |
| `PeerRegions` | `ITI1,ITI2,ITH5,ITI4,ITF1` | Toscana, Umbria, Emilia-Romagna, Lazio, Abruzzo |
| `ProvinceRegions` | `ITI31,ITI32,ITI33,ITI34,ITI35` | NUTS 3 provinces of the focus region. Eurostat filters accept only exact codes (no "starts with"), and a query that read the codes from the GISCO-based `Geo` table would trip the Power Query privacy firewall. `check-sources` verifies that the parameter matches the GISCO children of `FocusRegion` |
| `Country` | `IT` | National benchmark |
| `StartYear` | `2009` | First year requested from Eurostat, the same as the Python pipeline and the business series |
| `RepoRawBase` | `https://raw.githubusercontent.com/simones99/marche-regional-stats/main` | Base URL of the files exported by Python |
| `CompaniesSourceUrl` | `https://opendata.marche.camcom.it/data/Stock-Imprese-Attive-Marche-2009-2025.csv` | Chamber of Commerce archive |

### Dimensions

| Table | Columns | Source |
|---|---|---|
| `Geo` | Code, Name, Level (EU, Country, NUTS2, NUTS3), ParentCode, Role (Focus, Peer, Country, EU, Province), SortOrder | GISCO `NUTS_AT_2024.csv` (Code = `NUTS_ID`, Name = `NAME_LATN`, Level = code length − 2), filtered to the codes in FocusRegion, PeerRegions and ProvinceRegions (the refresh fails if one is missing from GISCO), plus static rows for `IT` ("Italy") and `EU27_2020` ("European Union (27)") |
| `Calendar` | Date, Year, Quarter, MonthNumber, MonthName, YearMonth, MonthEnd | Power Query, daily, 1 January of `StartYear` to 31 December of the current year, marked as the date table |
| `Sex` | Code (T, M, F), Name | static |
| `AgeGroup` | Code (Eurostat five-year codes), Name, SortOrder, BroadGroup (0-14, 15-64, 65+), Is80Plus | static |
| `ISCED` | Code (ED0 … ED8, ED0-8), Name, SortOrder, Group (ISCED 0-3, 4, 5-8) | static |
| `Sector` | Code (ATECO 2007 section), Name (English) | static |

Annual Eurostat facts join `Calendar` on 1 January of their year: population is measured on 1 January. Monthly facts join on the month-end date, the date at which the stock of active companies is recorded.

### Facts

| Table | Grain | Source and filters |
|---|---|---|
| `Population` | geo × year × sex × age | `demo_r_pjangrp3` (EU, country, NUTS 2 and NUTS 3 in one dataset), `unit=NR` |
| `Deaths` | geo × year × sex × age | `demo_r_magec3`, `unit=NR` |
| `GDP` | geo × year × unit | `nama_10r_2gdp` (EU, country, NUTS 2) and `nama_10r_3gdp` (provinces), units `EUR_HAB` and `PPS_HAB_EU27_2020` (EU = 100). Eurostat's per-inhabitant values are used as published |
| `Unemployment` | geo × year | `lfst_r_lfu3rt` (EU, country, NUTS 2) with `isced11=TOTAL`, `sex=T`, `age=Y15-74`, `unit=PC`. It replaces `tgs00010` + `tipsun20` |
| `Enrolment` | geo × year × sex × ISCED | `educ_uoe_enra11` for focus, peers, country and EU, `unit=NR` |
| `Companies` | province × ATECO section × month-end | Chamber of Commerce CSV, cleaned in Power Query (see Data flow). Focus region only. The page says so. Sections A–T plus X (not classified). |
| `Forecast` | month-end × series (actual, forecast, lower, upper) | `powerbi/data/forecast.csv` |
| `ForecastAccuracy` | model (SARIMA, naive, seasonal naive) | `powerbi/data/forecast_accuracy.csv`: MAPE and MAE on the 24-month holdout |
| `Reconciliation` | checkpoint | `powerbi/data/reconciliation.csv`: geo code, month-end, expected active companies |

Each Eurostat fact keeps `OBS_FLAG`.

### Measures

All measures live in a `_Measures` table, in display folders by page, and each one has a description. Base indicators:
- Population, Population change 5y %, Share aged 0-14, Share aged 65+, Share aged 80+;
- Deaths, Crude death rate per 1,000;
- GDP per inhabitant (EUR), GDP per inhabitant (PPS, EU = 100);
- Unemployment rate;
- Students enrolled, Tertiary students per 1,000 residents;
- Active companies, Active companies change %, Companies per 1,000 residents;
- Forecast measures (actual, forecast, interval bounds, MAPE).

Definitions follow `docs/methodology.md`, so the report and the Python results agree:
- Active companies per 1,000 residents: companies at 31 December divided by the population on 1 January of the following year.
- Active companies change: December 2009 to December of the last full year.
- Crude death rate: deaths in the year per 1,000 residents on 1 January of the same year.
- Population change 5y and the age shares: population on 1 January.

Rule for comparisons: an indicator compared across areas uses the **latest year available for all areas in the visual**. The dynamic title states that year. Example: EU deaths stop at 2023 while Italian regions reach 2024.

### Calculation group `Compare to`

| Item | Meaning |
|---|---|
| Value | `SELECTEDMEASURE()` |
| Country / vs Country | the measure for `Geo[Role] = "Country"`, and the difference from it |
| EU / vs EU | the same for `Geo[Role] = "EU"` |
| Peers avg / vs Peers avg | unweighted mean of the measure over the peer regions, and the difference from it |
| Rank among peers | rank of the area among the focus and peer regions |

Rules:
- Differences use dynamic format strings: the format of the selected measure, so rates show as percentage points and amounts in euro.
- `discourageImplicitMeasures` is on, so every visual uses explicit measures.
- Rank is shown only for indicators comparable across regions (rates, shares, per-inhabitant values). The Rank item returns BLANK for other measures, tested with `ISSELECTEDMEASURE`.
- Every item leaves text measures alone (`IF ( ISTEXT ( SELECTEDMEASURE () ), SELECTEDMEASURE (), … )`; `ISTEXT` and not `ISNUMERIC`, so a blank value is still compared). The dynamic titles are text measures, and a calculation group would otherwise apply to them too.

### Field parameter

`Province indicator` = Population change 5y %, Share aged 65+, Crude death rate per 1,000, Companies per 1,000 residents, GDP per inhabitant (EUR).

## Data flow

```
Eurostat SDMX 3.0 (5 datasets) ──► fnEurostat ──► Population, Deaths, GDP, Unemployment, Enrolment
GISCO NUTS_AT_2024.csv ──────────► Geo
Chamber of Commerce CSV ─────────► Companies
marche-stats export-powerbi ─────► powerbi/data/*.csv (GitHub raw) ──► Forecast, ForecastAccuracy, Reconciliation
StartYear parameter ─────────────► Calendar
```

**`fnEurostat(dataset, filters, levels)`** is one M function used by every Eurostat fact. It reads `StartYear` from the parameter. It:
- builds the URL `…/data/dataflow/ESTAT/<dataset>/1.0?c[geo]=<codes>&<filters>&c[TIME_PERIOD]=ge:<StartYear>&format=csvdata&formatVersion=1.0&labels=id&compress=false`;
- filters by dimension name only, with no positional key, so a dataset that gains or loses a dimension still works;
- takes geo codes from the parameters, by level: EU (`EU27_2020`), Country, NUTS2 (focus and peers), NUTS3 (provinces);
- returns untyped columns with codes; each fact query types its own columns;
- rethrows any HTTP or parsing error with the dataset name and the request query in the message.

**`Companies`** repeats the rules of `src/marche_stats/companies.py`:
1. Read the CSV with `;` as separator.
2. Unpivot the month columns and parse the `dd/mm/yyyy` dates.
3. Keep the ATECO section rows and drop the `TOTAL` rows. They are equal: Python checks it.
4. Drop the 9 municipalities transferred to Emilia-Romagna from every month (`TRANSFERRED_OUT`).
5. Map the territory prefix to NUTS 3 (`PU` and `PS` → ITI31, `AN` → ITI32, `MC` → ITI33, `AP` → ITI34, `FM` → ITI35).
6. Drop every month column identical to the previous one in every row (not updated).
7. Aggregate to province × section × month-end.

**`marche-stats export-powerbi`** is a new CLI command. It writes `forecast.csv`, `forecast_accuracy.csv` and `reconciliation.csv` to `powerbi/data/`, and the files are committed. The reconciliation checkpoints are: the regional total in the first month (March 2009) and in the last month the model is fitted on (January 2025), and each province in the first and last full-year December (2009, 2024), which the "change" and "per 1,000 residents" indicators use.

**Refresh** runs in Power BI Desktop only. All sources are public: privacy level Public, anonymous access.

## Checks and error handling

The About page has a "Data checks" section:
1. **Reconciliation:** the Power BI value against `Reconciliation`, with a ✓/✗ per checkpoint.
2. **Freshness:** the last year or month available per source. Every page subtitle reads "Data up to …".
3. **Eurostat flags:** provisional, estimated and break-in-series values are marked in tooltips.

| Risk | Handling |
|---|---|
| Year or code not in the dataset → HTTP 400 | `ge:` periods; codes from GISCO and the parameters |
| A dataset gains or loses a dimension | name-based filters, no positional key |
| Eurostat changes a label | codes in relationships; labels are display text only |
| A source is down | the refresh fails loudly with the dataset and URL. Desktop keeps the previous data. No query returns an empty table silently |
| Areas end in different years | comparisons use the latest common year, shown in the title |
| Chamber of Commerce portal moves | `CompaniesSourceUrl` parameter. The archive is closed, so any copy is equivalent |
| ATECO 2007 → ATECO 2025 break (April 2025) | the series ends in March 2025, as explained on About. Joining the ATECO 2025 series is out of scope |

## Delivery

- `powerbi/marche-regional-profile.pbip` replaces both current projects. They stay in git history.
- `powerbi/data/`: the CSV files exported by Python.
- `powerbi/exports/marche-regional-profile.pdf`: PDF exported from Desktop, plus one PNG per page made from it by a script.
- `powerbi/README.md`: pages, data model with a screenshot of the model view, sources, refresh.
- Root `README.md`: a "Power BI report" section with the Overview image, the PDF link and "What this demonstrates" (reusable M function, star schema on NUTS codes, Calendar, calculation group, field parameter, Python → Power BI integration, in-report data checks).
- Every table and measure has a TMDL description (`///`).

## Verification

1. **pytest** on synthetic data, in the style of the current suite, for `export-powerbi`: file layout, column types, reconciliation totals.
2. **`marche-stats check-sources`:** reads every source URL from the `.tmdl` files, calls it, and reports the HTTP status and the latest period. It also runs as a weekly GitHub Actions workflow, separate from CI.
3. **After every refresh (user):**
   - every reconciliation checkpoint shows ✓;
   - the reference values hold: about 130,000 active companies in January 2025, a Marche crude death rate of about 12.6 per 1,000, SARIMA MAPE of about 1 %.
4. **Best Practice Analyzer (optional):** if the Tabular Editor 2 CLI can load a TMDL folder, run the BPA rules in CI. To be checked in the plan.

## Phases

**Phase A, now:**
- `export-powerbi` and its tests;
- `check-sources` and the weekly workflow;
- the new semantic model: parameters, `fnEurostat`, dimensions, facts, `Calendar`, relationships, measures, calculation group, field parameter;
- reconciliation;
- one technical check page (a matrix of indicators × areas) that shows the model works;
- removal of the two old projects once the new one refreshes.

Done when:
- the user refreshes the new project in Desktop without errors;
- every reconciliation checkpoint shows ✓;
- the check page shows every indicator for focus, peers, country and EU;
- `pytest` and `check-sources` pass.

**Phase B, after the design session:**
- the 8 pages;
- tooltip pages and navigation;
- theme;
- PDF and PNG exports;
- READMEs.

The design session also decides how pages are authored: PBIR JSON written by Claude, the user building visuals in Desktop, or a mix.

## Out of scope

- Profiling other regions from the report UI. The parameters make it possible later.
- AI features.
- The ATECO 2025 series from April 2025.
- Municipality-level analysis.
- Publishing to the Power BI Service.
