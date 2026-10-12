# Power BI reports

Two Power BI Desktop reports on the Marche region (NUTS 2 `ITI3`) and its provinces. They are built on Eurostat data loaded through the SDMX API.

| Project | Pages | Built |
|---|---|---|
| `marche-demography-education.pbip` | Overview, Education Enrollment Overview, ISCED 0-3 | July–August 2025 |
| `marche-regionali-2025.pbip` | Regional Overview, Comparative Analysis, Education Enrollment Overview, ISCED 0-3, plus tooltip pages | September 2025, for the 2025 regional election |

Both reports are saved as Power BI projects (`.pbip`): the report layout sits in `*.Report/` and the semantic model, with its Power Query and DAX code, in `*.SemanticModel/definition/` as TMDL text files.

## What the reports show

**Overview / Regional Overview**
- Population and deaths by year, sex and age group, with filled maps by province.
- KPI cards for selected age groups: under 11, under 15, over 79.
- In the 2025 report:
  - weighted population growth over the last 5 years;
  - weighted mortality rate over the last 5 years;
  - a year slicer.

**Comparative Analysis** (2025 report)
- Unemployment rate and GDP per capita: Marche against its neighbouring regions (Emilia-Romagna, Tuscany, Umbria, Lazio, Abruzzo), Italy and the EU27.
- Map tooltips show the time series and the gap to Italy and to the EU.

**Education Enrollment Overview / ISCED 0-3**
- Enrolments by year, sex and ISCED 2011 level.

## Data sources (Eurostat, SDMX 3.0 API)

| Topic | Dataset | Geography |
|---|---|---|
| Population on 1 January by broad age group and sex | `demo_r_pjanaggr3` | NUTS 2 / NUTS 3 |
| Population on 1 January by five-year age group and sex | `demo_r_pjangroup` | Marche, neighbouring NUTS 2 regions, Italy, EU27 |
| Deaths by age group and sex | `demo_r_magec3`, `demo_r_magec` | NUTS 3 / NUTS 2 |
| GDP at current market prices | `nama_10r_2gdp` | NUTS 2 |
| Unemployment rate, 15–74 | `tgs00010` (regions), `tipsun20` (Italy, EU27) | NUTS 2 / country |
| Pupils and students enrolled by education level and sex | `educ_uoe_enra11` | NUTS 2 |

NUTS 2024 codes and names come from GISCO (`NUTS_AT_2024.csv`, © EuroGeographics).

The query URLs used in Power Query are in [sources.md](sources.md). The education pages of both reports read `educ_uoe_enra11`, pupils and students enrolled by education level, sex and NUTS 2 region.

## Opening the reports

Open the `.pbip` files with Power BI Desktop (Windows). The data cache (`.pbi/cache.abf`) is not committed, so run *Refresh* after cloning: the reports reload the data from the Eurostat and GISCO APIs. To view them without Power BI, export each page to PDF (*File → Export → Export to PDF*) and store the exports in `powerbi/exports/`.
