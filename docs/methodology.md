# Methodology note

## Purpose

This project describes the business and demographic structure of the Marche region (NUTS 2 `ITI3`) and its five provinces (NUTS 3). It also forecasts the number of active companies in the region over the next 12 months. Results are in [results.md](results.md). From v0.2 it also compares the region with its neighbours, Italy and the EU27 on mortality, education and the economy (see Regional comparisons).

## Data

| Source | Content | Geography | Period |
|---|---|---|---|
| Camera di Commercio delle Marche, Open Data Imprese Italia (business register, CC BY 4.0) | Active companies (registered offices) at month end, by municipality and ATECO 2007 section | 254 municipal codes, 5 provinces | March 2009 – March 2025 |
| Eurostat `demo_r_pjanaggr3` | Population on 1 January, total and aged 65+ | NUTS 3, Marche, Italy | 2009 onwards |
| Eurostat `demo_r_magec3` | Deaths | NUTS 3, Marche, Italy | 2009 onwards |
| GISCO, NUTS 2024 level 3 (1:3 million) | Province boundaries | NUTS 3 | — |
| Eurostat, nine regional datasets (see [powerbi/sources.md](../powerbi/sources.md)) | Deaths and population by age, education, GDP, unemployment | NUTS 2: Marche and five neighbours; Italy; EU27 | 2013 onwards |

All inputs are downloaded by `marche-stats download`: the Eurostat data through the SDMX 2.1 API, and the business register file from the [Chamber of Commerce open data portal](https://opendata.marche.camcom.it/data/Stock-Imprese-Attive-Marche-2009-2025.csv). That file is the archive of the ATECO 2007 series. From April 2025 the portal publishes the series in ATECO 2025, which is not directly comparable by sector. Older downloads of the file label the unclassified records of Pesaro e Urbino `PS`, current ones `PU`. Both are handled.

## Processing of the business register file

1. **Structure checks.** The file is checked for the following, and every check is reported in [results.md](results.md):
   - one row per municipality and section;
   - known province codes;
   - non-negative integer counts;
   - no missing months;
   - each municipality's `TOTAL` row equals the sum of its sections.
2. **Totals.** Totals come from the `TOTAL` rows only. Summing every row would count each company twice: once in its section and once in the total.
3. **Stale months.** A month identical to the previous one in every cell is treated as not updated. This is the case for February 2025, which repeats January 2025 in the published file. The time series stops before that month, because SARIMA needs consecutive months, so March 2025 is not used either.
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

## Regional comparisons

From v0.2 the project compares the Marche (NUTS 2 `ITI3`) with its neighbouring regions (Emilia-Romagna `ITH5`, Toscana `ITI1`, Umbria `ITI2`, Lazio `ITI4`, Abruzzo `ITF1`), Italy and the EU27, on mortality, education and the economy. The same tables feed `docs/results.md` and the Power BI report.

### Data checks

- After each download the data must cover the eight areas in every year the Marche has. The known gaps at the source are listed in the code (`KNOWN_GAPS`): EU27 deaths in 2024 and EU27 enrolment in 2017. Any other gap stops the pipeline.
- Eurostat sometimes answers an oversized query with an XML error and HTTP status 200. The download checks that every answer is SDMX-CSV.
- Missing values (`:`) are kept as missing, with their flag. Nothing is imputed.

### Age-standardised death rates

- **Standard population:** European Standard Population 2013 (ESP), in five-year age groups. Eurostat's population by age group ends at the open group 85+, so the ESP weights for 85–89, 90–94 and 95+ (1,500, 800 and 200) are merged into one 85+ weight of 2,500.
- **Deaths** by single year of age (`demo_r_magec`) are summed into the same groups. Deaths of unknown age are spread over the known ages in proportion; in the current data there are none.
- **Denominator:** the average population of the year, the mean of the populations on 1 January of the year and of the next, as Eurostat does. The provincial crude rate above keeps the 1 January population.
- **Rate:** direct standardisation per 100,000, by sex. An area and year without deaths and population for all 18 age groups gets no rate: standardising on part of the age range would bias it.
- **Interval:** 95 %, Dobson et al. (1991). The exact Poisson interval for the total number of deaths is scaled to the standardised rate.
- **Five-year rate:** deaths and populations are summed over the five years in each age group, then standardised (a pooled rate, not an average of annual rates). The window is the latest five years with complete data for the six regions and Italy. An area without complete data in every year of the window is left out and named in the results.
- **EU27:** the EU27 aggregate in these two datasets lacks some age groups in most years (complete only in 2021 and 2022 in the October 2026 data), so EU27 rates appear only in those years and the EU27 is left out of the five-year table.
- **Check against Eurostat:** Eurostat publishes standardised death rates by region (`hlth_cd_asdr2`, from causes-of-death statistics, 2018–2021). For the Marche, both sexes, the rates of this project are within 0.4 % of Eurostat's; the tests fail above 3 %. The small gap comes from the open 85+ group and the different source.

Why it matters: the Marche population is older than Italy's. The crude death rate of the Marche is therefore higher than Italy's (1,184 against 1,108 per 100,000 in 2024), while the age-standardised rate is lower (741 against 790).

### Education

- **Enrolment** (`educ_uoe_enra11`) by single ISCED 2011 level, compared with Italy as an index (2013 = 100), because counts do not compare across areas of different size. The EU27 aggregate in this dataset is incomplete (2017 missing, several levels missing in other years), so it is not used for comparisons.
- **Indicators** with an EU 2030 target:

  | Indicator | Dataset | EU 2030 target |
  |---|---|---|
  | Early leavers from education and training, 18–24 | `edat_lfse_16` | below 9 % |
  | Tertiary attainment, 25–34 (ISCED 5–8) | `edat_lfse_04` | at least 45 % |
  | Early childhood education, age 3 to compulsory school age | `educ_uoe_enra22` | at least 96 % |

- The first two come from the Labour Force Survey. Regional estimates rest on small samples: Eurostat flags some of them as of low reliability (`u`) and marks breaks in series (`b`). The flags are kept in the tables and drawn as hollow markers; year-to-year changes are not commented on.

### Economy

- **GDP per inhabitant** in purchasing power standards, as an index with EU27 = 100 (`nama_10r_2gdp`, unit `PPS_HAB_EU27_2020`). PPS remove price-level differences between countries, so the index compares areas within a year. It is not a measure of growth over time.
- **Unemployment rate, 15–74** from one dataset, `lfst_r_lfu3rt`, for the regions, Italy and the EU27. (The v0.1 Power BI report mixed `tgs00010` for the regions with `tipsun20` for Italy and the EU.)

### Comparisons

For each indicator and both sexes, the latest year with a Marche value is used for every area. The tables give the gap from Italy and the EU27 in percentage points (index points for GDP), the rank of the Marche among the six regions (1 = best; ties share the best rank), the change since the first year available, and the distance to the EU 2030 target (positive when the target is met).

## Findings worth knowing

- **Administrative steps.** The province series show sudden drops, for example Ascoli Piceno at the turn of 2023–24 and Macerata in 2022. These are larger and sharper than the usual seasonal pattern. They are typical of batch *ex officio* deregistrations of inactive companies by the Chambers of Commerce, not of a sudden wave of closures. This should be confirmed with the data provider before such drops are read as economic events. The forecast cannot anticipate them.
- **Seasonal naive performs worst.** The series has a strong downward trend, and repeating last year's level carries that year's higher level into the test period.

## Limitations

- Active companies count registered businesses, not employment or output. One large firm and one sole trader weigh the same.
- It has not been checked whether Eurostat's NUTS 3 population for Pesaro e Urbino before 2021 was recalculated for the transfer of Montecopiolo and Sassofeltrio (together about 2,500 residents). If it was not, part of the 2010–2025 population decline of ITI31 (up to about 0.7 points) is a boundary effect.
- The forecast assumes that the trend and seasonal pattern of the last years continue. Administrative clean-ups of the register (see above) are not modelled.
- Interval coverage is measured on only 24 test months, forecast from a single origin, so the months are not independent checks. A coverage of 100 % is compatible with the nominal 95 % (with independent months, all 24 would fall inside about 29 % of the time), but it does not show that the intervals are well calibrated. It may also mean that they are too wide, especially at long horizons where they widen with each step.
- The six regions in the comparison are the Marche's neighbours, not a statistical sample: ranks describe this group only.
- Regional Labour Force Survey estimates carry sampling error, which Eurostat does not publish as intervals; only the reliability flags are available.

## Earlier exploration

`notebooks/exploration_2025.ipynb` is the first, exploratory analysis of the same file (PCA, k-means clustering, SARIMA and Prophet). It is kept for reference. This package corrects its main issues:
- mixing `TOTAL` and section rows;
- measuring accuracy in sample;
- a seasonal period of 6 instead of 12;
- no treatment of boundary changes.

## Sources and reuse

- Business register data: Camera di Commercio delle Marche, Open Data Imprese Italia (data from the Registro delle Imprese; rights holder Unioncamere), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Aggregated and transformed by the author.
- Eurostat data: © European Union, reused under the [Eurostat copyright notice](https://ec.europa.eu/eurostat/about-us/policies/copyright).
- NUTS boundaries: © EuroGeographics for the administrative boundaries, distributed by [GISCO](https://ec.europa.eu/eurostat/web/gisco).
