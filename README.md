# marche-regional-stats

Regional statistics for the Marche region (Italy) and its five provinces. The project brings together three pieces of work:

- **Business demography.** Monthly active companies by municipality and economic sector, from 2009 to 2025, after source checks and a boundary correction.
- **Provincial indicators on NUTS 3 maps.** Companies per resident, population ageing and mortality, from Eurostat.
- **Forecasting.** A SARIMA model of active companies, compared out of sample with naive baselines.

It also contains two **Power BI reports** on the region's demography, education, GDP and unemployment, built on the Eurostat API.

![Indicators by province](docs/figures/nuts3_maps.png)

## Main results

The latest figures and every check are in [docs/results.md](docs/results.md).

- Active companies in the region fell from about 160,000 in 2009 to about 130,000 in January 2025, on constant boundaries. The decline ranges from −12 % in Ascoli Piceno to −19 % in Pesaro e Urbino.
- Seasonality is moderate (strength 0.56). Each January to March the stock drops by about 1,000 companies against trend, because closures are concentrated at the turn of the year.
- On the last 24 months, held out from model selection, SARIMA has a mean absolute percentage error of about 1 %. The naive baseline reaches about 3 % and the seasonal naive baseline about 6 %.

![Test period and forecast](docs/figures/forecast.png)

## What the analysis takes care of

The source file has several traps, and each one is handled explicitly. See the [methodology note](docs/methodology.md).
- Every municipality has a `TOTAL` row on top of its sector rows. Summing all rows counts every company twice.
- Nine municipalities moved to Emilia-Romagna in 2010 and 2021. They are removed from every month, so their companies do not look like closures.
- The last month repeats the previous one in every cell, so it is treated as not updated.
- Sudden provincial drops look like administrative clean-ups of the register, not economic events. They are flagged rather than modelled.

## Repository

```
src/marche_stats/   source checks, Eurostat download, time series, figures, report
docs/               results, methodology note, figures
powerbi/            two Power BI reports and their data sources
notebooks/          the first exploratory notebook (kept for reference)
tests/              pytest suite on synthetic data in the same layout as the source
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt -e .

marche-stats download   # business register file, Eurostat population and deaths (NUTS 3), GISCO boundaries
marche-stats report     # checks, indicators, SARIMA, figures -> docs/results.md
pytest -q
```

`marche-stats download` also fetches the active companies file from the Chamber of Commerce open data portal into `data/raw/` (see Data sources). Data files are not committed. The tests run on synthetic data in the same layout.

## Data sources

- **Active companies by municipality and ATECO 2007 section, monthly:** Camera di Commercio delle Marche, *Open Data Imprese Italia*, dataset "Imprese Attive nelle Marche per Comune, Settore Ateco e Tempo (frequenza mensile) – Anni dal 2009 al 2025".
  - Data come from the Chambers of Commerce business register (Registro delle Imprese), with Unioncamere as rights holder.
  - Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  - Portal: [opendata.marche.camcom.it](https://opendata.marche.camcom.it), file [`Stock-Imprese-Attive-Marche-2009-2025.csv`](https://opendata.marche.camcom.it/data/Stock-Imprese-Attive-Marche-2009-2025.csv).
  - This archive covers ATECO 2007 up to March 2025. From April 2025 the portal publishes the series in ATECO 2025.
  - The analysis aggregates and transforms the data as described in the methodology note.
- Eurostat `demo_r_pjanaggr3` and `demo_r_magec3`: © European Union, reused under the Eurostat copyright notice.
- NUTS boundaries: © EuroGeographics, distributed by GISCO.

## License

Code: MIT.
