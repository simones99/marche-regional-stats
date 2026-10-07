# Results

Generated 2026-10-07 by `marche-stats run`. Methods and caveats: [methodology note](methodology.md).

## 1. Source data checks (active companies file)

| Check | Result | Detail |
|---|---|---|
| Unique territory and sector | pass | 0 duplicated rows |
| Known province codes | pass | unknown: none |
| Counts are non-negative integers | pass | 0 missing values |
| TOTAL row equals the sum of sections | pass | 0 territories differ in at least one month |
| No missing months | pass | 193 months from 2009-03 to 2025-03 |
| No month identical to the previous one | FAIL | identical: 28/02/2025; regional total unchanged in 1 month(s) |
| Municipalities merged inside the region (no correction needed) | pass | 18 territories fall to zero and are absorbed by a successor |
| Municipalities transferred to another region (removed from all months) | pass | 9 territories, 2,184 active companies in 31/03/2009 |

Months identical to the previous one in every cell are treated as not updated: 2025-02. The time series stops before the first of them, because SARIMA needs consecutive months, so it runs from 2009-03 to 2025-01 (191 months) and later months in the file are not used.

## 2. Provinces (NUTS 3)

![Indicators by province](figures/nuts3_maps.png)

| NUTS 3 | Province | Active companies per 1,000 residents, Dec 2024 | Change in active companies, 2009-2024 (%) | Population change, 2010-2025 (%) | Residents aged 65+, 1 Jan 2025 (%) | Crude death rate per 1,000, 2024 |
|---|---|---|---|---|---|---|
| ITI31 | Pesaro e Urbino | 87.0 | -18.8 | -3.9 | 25.7 | 11.1 |
| ITI32 | Ancona | 74.4 | -18.3 | -2.7 | 26.5 | 11.6 |
| ITI33 | Macerata | 101.7 | -16.6 | -5.9 | 26.9 | 12.6 |
| ITI34 | Ascoli Piceno | 93.1 | -12.2 | -5.4 | 27.4 | 12.2 |
| ITI35 | Fermo | 101.1 | -17.6 | -4.9 | 27.3 | 12.2 |

![Active companies by province, indexed](figures/province_index.png)

## 3. Seasonality

Seasonal strength (STL, 0 = none, 1 = purely seasonal): **0.56**. Average seasonal effect by calendar month, in number of active companies:

| Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|
| -936 | -967 | -616 | -227 | +153 | +399 | +195 | +347 | +504 | +560 | +453 | +71 |

![STL decomposition](figures/decomposition.png)

## 4. SARIMA model

Specification chosen by AIC on the training period (up to 2023-01): SARIMA(2, 1, 2)(0, 1, 1)[12], AIC 1,903.2.

Out-of-sample errors over the last 24 months (2023-02 to 2025-01), forecasting from the end of the training period without updating:

| Method | MAE | MAPE (%) |
|---|---|---|
| SARIMA | 1,503.68 | 1.13 |
| Naive (last value) | 4,377.62 | 3.31 |
| Seasonal naive | 7,684.79 | 5.76 |

Share of test months inside the SARIMA 95 % prediction interval: **100 %** (nominal 95 %).

![Test period and forecast](figures/forecast.png)

12-month forecast, refitted on the full series:

| Month | forecast | lower_95 | upper_95 |
|---|---|---|---|
| 2025-02 | 129,982 | 129,460 | 130,505 |
| 2025-03 | 130,262 | 129,470 | 131,053 |
| 2025-04 | 130,432 | 129,370 | 131,494 |
| 2025-05 | 130,529 | 129,216 | 131,842 |
| 2025-06 | 130,761 | 129,197 | 132,325 |
| 2025-07 | 130,351 | 128,546 | 132,155 |
| 2025-08 | 130,444 | 128,402 | 132,486 |
| 2025-09 | 130,145 | 127,873 | 132,417 |
| 2025-10 | 129,994 | 127,497 | 132,490 |
| 2025-11 | 129,701 | 126,986 | 132,415 |
| 2025-12 | 129,235 | 126,308 | 132,161 |
| 2026-01 | 127,833 | 124,700 | 130,965 |
