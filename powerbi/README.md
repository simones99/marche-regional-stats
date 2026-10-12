# Power BI report

`marche-regional-profile.pbip` is a Power BI project on the Marche region (NUTS 2 `ITI3`), its provinces and its neighbouring regions, against Italy and the EU. It replaces the two earlier reports (`marche-regionali-2025`, `marche-demography-education`), which remain in the git history.

Phase A (this version) contains the semantic model and one model check page. The report pages follow in Phase B. Design: [spec](../docs/superpowers/specs/2026-10-12-marche-regional-profile-report-design.md).

## Model

- A star schema keyed on NUTS codes. Dimensions: `Geo`, `Calendar` (daily, the date table), `Sex`, `AgeGroup`, `ISCED`, `Sector`. Facts: `Population`, `Deaths`, `GDP`, `Unemployment`, `Enrolment`, `Companies`, `Forecast`.
- Power Query parameters choose the areas: `FocusRegion`, `PeerRegions`, `ProvinceRegions`, `Country`, `StartYear`. Every Eurostat query goes through one function, `fnEurostat`.
- The calculation group `Compare to` adds Country, EU, peer average, differences and rank to any indicator.
- Province rows are compared among provinces only: provincial GDP lags the regional series by a year, so Compare to is not used on province rows.
- `Companies` is cleaned in Power Query with the rules of `src/marche_stats/companies.py`.
- The model check page shows the reconciliation of `Companies` with the totals that Python writes to `data/reconciliation.csv`, the indicators by area and the Compare to matrix.
- `data/` holds the files exported by `marche-stats export-powerbi`: the SARIMA forecast, its accuracy and the reconciliation totals.

## Refresh

Open `marche-regional-profile.pbip` in Power BI Desktop (Windows) and choose *Refresh*. All sources are public: use anonymous access. The data cache (`.pbi/cache.abf`) is not committed, so refresh after cloning.

`marche-stats check-sources` requests every source the model uses, from the TMDL files. It runs weekly in GitHub Actions.

Sources and query details: [sources.md](sources.md).
