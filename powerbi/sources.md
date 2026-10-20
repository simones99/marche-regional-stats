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
| Population | `demo_r_pjangrp3` | `unit=NR`, `sex=T,M,F`, `age=TOTAL,Y_LT5,Y5-9,Y10-14,…,Y80-84,Y85-89,Y_GE90,UNK` | EU, Country, NUTS2, NUTS3 |
| Deaths | `demo_r_magec3` | as Population | EU, Country, NUTS2, NUTS3 |
| GDP | `nama_10r_2gdp` | `unit=EUR_HAB,PPS_HAB_EU27_2020` | EU, Country, NUTS2 |
| GDP | `nama_10r_3gdp` | `unit=EUR_HAB,PPS_HAB_EU27_2020` | NUTS3 |
| Unemployment | `lfst_r_lfu3rt` | `isced11=TOTAL`, `sex=T`, `age=Y15-74`, `unit=PC` | EU, Country, NUTS2 |
| Enrolment | `educ_uoe_enra11` | `unit=NR`, `sex=T,M,F`, `isced11=ED02-8,ED0,ED1,…,ED8` | EU, Country, NUTS2 |

Population and Deaths keep the age bands of a (geo, sex, year) only when they add up to the TOTAL row (Eurostat lacks some EU27_2020 bands, e.g. 85+ in 2014–2020). `ED02-8` is the enrolment total: `ED0-8` is missing after 2023.

Other sources:

| Table | Source |
|---|---|
| Geo | GISCO, NUTS 2024 attributes: `https://gisco-services.ec.europa.eu/distribution/v2/nuts/csv/NUTS_AT_2024.csv` (© EuroGeographics) |
| Companies | Camera di Commercio delle Marche, active companies by municipality and ATECO 2007 section, monthly, 2009–2025 (CC BY 4.0): parameter `CompaniesSourceUrl` |
| Forecast, ForecastAccuracy, Reconciliation, Seasonality, ProvinceShape | `powerbi/data/*.csv` in this repository, read from `RepoRawBase` (GitHub raw URL) |

## Photos

| Page | Photo | Author | Licence |
|---|---|---|---|
| Overview | [Tempio del Valadier dall'eremo](https://commons.wikimedia.org/wiki/File:Tempio_del_Valadier_dall%27eremo.jpg) | Kimahri88 | CC0 1.0 |
| Education | [Panorama (Urbino)](https://commons.wikimedia.org/wiki/File:Panorama_(Urbino)_-_panoramio.jpg) | Fabio Poggi | CC BY 3.0 |
| About | [Spiaggia due sorelle](https://commons.wikimedia.org/wiki/File:Spiaggia_due_sorelle.jpg) | Gaspa | CC BY 2.0 |

The photos are cropped to their slots and compressed; no other change.
