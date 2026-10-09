# marche-regional-stats

Regional statistics for the Marche region (Italy), its five provinces and its neighbours. The project brings together four pieces of work:

- **Business demography.** Monthly active companies by municipality and economic sector, from 2009 to 2025, after source checks and a boundary correction.
- **Provincial indicators on NUTS 3 maps.** Companies per resident, population ageing and mortality, from Eurostat.
- **Forecasting.** A SARIMA model of active companies, compared out of sample with naive baselines.
- **Regional comparisons.** Age-standardised mortality, education against the EU 2030 targets, GDP per inhabitant in PPS and unemployment: the Marche against its neighbouring regions, Italy and the EU27.

A **Power BI project** in `powerbi/` presents the regional comparisons. It reads the model tables that the pipeline writes to `data/model/`, so the report and this repository show the same numbers.

![Indicators by province](docs/figures/nuts3_maps.png)

## Main results

The latest figures and every check are in [docs/results.md](docs/results.md).

- Active companies in the region fell from about 160,000 in 2009 to about 130,000 in January 2025, on constant boundaries. The decline ranges from −12 % in Ascoli Piceno to −19 % in Pesaro e Urbino.
- Seasonality is moderate (strength 0.56). Each January to March the stock drops by about 1,000 companies against trend, because closures are concentrated at the turn of the year.
- On the last 24 months, held out from model selection, SARIMA has a mean absolute percentage error of about 1 %. The naive baseline reaches about 3 % and the seasonal naive baseline about 6 %.
- The Marche population is older than Italy's, so its crude death rate is higher (1,184 against 1,108 per 100,000 in 2024) while its age-standardised rate is lower (741 against 790). The standardised rates agree with Eurostat's published ones within 0.4 %.
- In 2025, 7.7 % of 18–24-year-olds in the Marche left education early (Italy 8.2 %; EU 2030 target: below 9 %), and 32.8 % of 25–34-year-olds had a tertiary degree (EU27 44.8 %; target: 45 %).
- GDP per inhabitant in PPS is 89 % of the EU27 average (2024; Italy 98 %). Unemployment is 5.1 % (2025; Italy 6.1 %, EU27 6.0 %).

![Death rates, crude and age-standardised](docs/figures/mortality.png)

![Test period and forecast](docs/figures/forecast.png)

## What the analysis takes care of

The source file has several traps, and each one is handled explicitly. See the [methodology note](docs/methodology.md).
- Every municipality has a `TOTAL` row on top of its sector rows. Summing all rows counts every company twice.
- Nine municipalities moved to Emilia-Romagna in 2010 and 2021. They are removed from every month, so their companies do not look like closures.
- The last month repeats the previous one in every cell, so it is treated as not updated.
- Sudden provincial drops look like administrative clean-ups of the register, not economic events. They are flagged rather than modelled.

## Repository

```
src/marche_stats/   source checks, Eurostat download, mortality, indicators, model tables, figures, report
docs/               results, methodology note, figures
data/model/         model tables for Power BI (committed; data/raw/ is not)
powerbi/            Power BI project (TMDL model, PBIR report) and its data sources
notebooks/          the first exploratory notebook (kept for reference)
tests/              pytest suite on synthetic data in the same layout as the sources
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt -e .

marche-stats download   # business register file, Eurostat NUTS 3 and regional datasets, GISCO boundaries
marche-stats report     # checks, indicators, SARIMA, figures -> docs/results.md
marche-stats model      # model tables for Power BI -> data/model/
pytest -q
```

`marche-stats download` also fetches the active companies file from the Chamber of Commerce open data portal into `data/raw/` (see Data sources). Raw data files are not committed; the model tables in `data/model/` are. `marche-stats run` runs the three steps. The tests run on synthetic data in the same layout.

## Data sources

- **Active companies by municipality and ATECO 2007 section, monthly:** Camera di Commercio delle Marche, *Open Data Imprese Italia*, dataset "Imprese Attive nelle Marche per Comune, Settore Ateco e Tempo (frequenza mensile) – Anni dal 2009 al 2025".
  - Data come from the Chambers of Commerce business register (Registro delle Imprese), with Unioncamere as rights holder.
  - Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  - Portal: [opendata.marche.camcom.it](https://opendata.marche.camcom.it), file [`Stock-Imprese-Attive-Marche-2009-2025.csv`](https://opendata.marche.camcom.it/data/Stock-Imprese-Attive-Marche-2009-2025.csv).
  - This archive covers ATECO 2007 up to March 2025. From April 2025 the portal publishes the series in ATECO 2025.
  - The analysis aggregates and transforms the data as described in the methodology note.
- Eurostat `demo_r_pjanaggr3`, `demo_r_magec3` and the regional datasets listed in [powerbi/sources.md](powerbi/sources.md): © European Union, reused under the Eurostat copyright notice.
- NUTS boundaries: © EuroGeographics, distributed by GISCO.

## License

Code: MIT.
