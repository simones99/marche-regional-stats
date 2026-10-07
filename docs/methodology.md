# Methodology note

## Purpose

This project describes the business and demographic structure of the Marche region (NUTS 2 `ITI3`) and its five provinces (NUTS 3). It also forecasts the number of active companies in the region over the next 12 months. Results are in [results.md](results.md).

## Data

| Source | Content | Geography | Period |
|---|---|---|---|
| Business register, active companies (see the README for the source) | Active companies at month end, by municipality and ATECO 2007 section | 254 municipal codes, 5 provinces | March 2009 – February 2025 |
| Eurostat `demo_r_pjanaggr3` | Population on 1 January, total and aged 65+ | NUTS 3, Marche, Italy | 2009 onwards |
| Eurostat `demo_r_magec3` | Deaths | NUTS 3, Marche, Italy | 2009 onwards |
| GISCO, NUTS 2024 level 3 (1:3 million) | Province boundaries | NUTS 3 | — |

Eurostat data are downloaded through the SDMX 2.1 API (`marche-stats download`).

## Processing of the business register file

1. **Structure checks.** The file is checked for the following, and every check is reported in [results.md](results.md):
   - one row per municipality and section;
   - known province codes;
   - non-negative integer counts;
   - no missing months;
   - each municipality's `TOTAL` row equals the sum of its sections.
2. **Totals.** Totals come from the `TOTAL` rows only. Summing every row would count each company twice: once in its section and once in the total.
3. **Stale months.** A month identical to the previous one in every cell is treated as not updated and excluded. This is the case for February 2025, which repeats January 2025.
4. **Constant boundaries.** Nine municipalities moved from the province of Pesaro e Urbino to Emilia-Romagna:
   - the Alta Valmarecchia under Law 117/2009 (they leave the file after January 2010);
   - Montecopiolo and Sassofeltrio under Law 84/2021 (after May 2021).

   Their 2,184 companies (March 2009) would otherwise look like closures. They are removed from every month, so all series refer to the current regional boundaries. Mergers inside the region need no correction, because companies move to the successor municipality in the same province (for example Ripe, Monterado and Castel Colonna into Trecastelli in 2014).
5. **Province mapping.** Province codes map to NUTS 3: PU→ITI31, AN→ITI32, MC→ITI33, AP→ITI34, FM→ITI35. The old code `PS` (Pesaro e Urbino), used only for unclassified records, maps to ITI31.

## Indicators by province

- **Active companies per 1,000 residents:** companies at 31 December divided by the population on 1 January of the following year.
- **Change in active companies:** December of the first full year (2009) to December of the last full year.
- **Population change, share aged 65+:** from Eurostat, population on 1 January.
- **Crude death rate:** deaths in the year per 1,000 residents on 1 January of the same year. The average population would be the textbook denominator. The difference is small when population changes slowly, as it does here (under 1 % a year).

## Time series and forecast

- **Series.** Monthly active companies in the region, constant boundaries, March 2009 to January 2025.
- **Seasonality.** An STL decomposition (period 12, robust) gives the seasonal profile. The strength of seasonality is computed as in Wang, Smith and Hyndman (2006). The profile has a clear trough in January–March: in the business register, closures are concentrated at the end and start of the year.
- **Model selection.** The last 24 months are held out. On the training period, SARIMA(p,1,q)(P,D,Q)[12] is selected by AIC over p, q ∈ {0,1,2}, P, Q, D ∈ {0,1}.
- **Evaluation.** The selected model forecasts the 24 test months in one run from the end of training, without updating, and is compared out of sample with two baselines:
  - naive, repeating the last value;
  - seasonal naive, repeating the last 12 months.

  The comparison reports MAE, MAPE and the share of test months inside the 95 % prediction interval.
- **Forecast.** The selected specification is refitted on the full series and forecasts 12 months with a 95 % interval.

## Findings worth knowing

- **Administrative steps.** The province series show sudden drops, for example Ascoli Piceno at the turn of 2023–24 and Macerata in 2022. These are larger and sharper than the usual seasonal pattern. They are typical of batch *ex officio* deregistrations of inactive companies by the Chambers of Commerce, not of a sudden wave of closures. This should be confirmed with the data provider before such drops are read as economic events. The forecast cannot anticipate them.
- **Seasonal naive performs worst.** The series has a strong downward trend, and repeating last year's level carries that year's higher level into the test period.

## Limitations

- Active companies count registered businesses, not employment or output. One large firm and one sole trader weigh the same.
- It has not been checked whether Eurostat's NUTS 3 population for Pesaro e Urbino before 2021 was recalculated for the transfer of Montecopiolo and Sassofeltrio (together about 2,500 residents). If it was not, part of the 2010–2025 population decline of ITI31 (up to about 0.7 points) is a boundary effect.
- The forecast assumes that the trend and seasonal pattern of the last years continue. Administrative clean-ups of the register (see above) are not modelled.

## Earlier exploration

`notebooks/exploration_2025.ipynb` is the first, exploratory analysis of the same file (PCA, k-means clustering, SARIMA and Prophet). It is kept for reference. This package corrects its main issues:
- mixing `TOTAL` and section rows;
- measuring accuracy in sample;
- a seasonal period of 6 instead of 12;
- no treatment of boundary changes.

## Sources and reuse

- Eurostat data: © European Union, reused under the [Eurostat copyright notice](https://ec.europa.eu/eurostat/about-us/policies/copyright).
- NUTS boundaries: © EuroGeographics for the administrative boundaries, distributed by [GISCO](https://ec.europa.eu/eurostat/web/gisco).
