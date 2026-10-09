# Data sources of the Power BI report

The report reads the model tables in `data/model/`, written by `marche-stats model`. Those tables come from the Eurostat datasets below, downloaded by `marche-stats download` through the SDMX 2.1 API (SDMX-CSV, from 2013, for the Marche, its neighbouring regions, Italy and the EU27).

| Raw file | Dataset | Content |
|---|---|---|
| `regional_deaths.csv` | `demo_r_magec` | Deaths by single year of age and sex |
| `regional_population.csv` | `demo_r_pjangroup` | Population on 1 January by five-year age group and sex |
| `death_rate_benchmark.csv` | `hlth_cd_asdr2` | Standardised death rate, all causes (check only) |
| `enrolment.csv` | `educ_uoe_enra11` | Pupils and students by ISCED level and sex |
| `early_leavers.csv` | `edat_lfse_16` | Early leavers from education and training, 18–24 |
| `tertiary_attainment.csv` | `edat_lfse_04` | Tertiary attainment (ISCED 5–8), 25–34 |
| `early_childhood.csv` | `educ_uoe_enra22` | Pupils aged 3 to compulsory school age, % of the age group |
| `gdp.csv` | `nama_10r_2gdp` | GDP per inhabitant in PPS, EU27 = 100 |
| `unemployment.csv` | `lfst_r_lfu3rt` | Unemployment rate, 15–74 |

## Query URLs

**`demo_r_magec`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/demo_r_magec/A.NR.T+M+F..ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`demo_r_pjangroup`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/demo_r_pjangroup/A.NR.T+M+F..ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`hlth_cd_asdr2`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/hlth_cd_asdr2/A.RT.T+M+F.TOTAL.A-R_V-Y.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`educ_uoe_enra11`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/educ_uoe_enra11/A.NR..T+M+F.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`edat_lfse_16`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/edat_lfse_16/A.PC.T+M+F.Y18-24.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`edat_lfse_04`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/edat_lfse_04/A.T+M+F.ED5-8.Y25-34.PC.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`educ_uoe_enra22`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/educ_uoe_enra22/A.PC.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`nama_10r_2gdp`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10r_2gdp/A.PPS_HAB_EU27_2020.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

**`lfst_r_lfu3rt`**

```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/lfst_r_lfu3rt/A.TOTAL.T+M+F.Y15-74.PC.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?format=SDMX-CSV&startPeriod=2013
```

Eurostat data: © European Union, reused under the [Eurostat copyright notice](https://ec.europa.eu/eurostat/about-us/policies/copyright).

The two v0.1 reports (`marche-demography-education.pbix`, `marche-regionali-2025.pbix`) loaded Eurostat directly from Power Query. They and their query URLs are kept in tag [`v0.1.0`](https://github.com/simones99/marche-regional-stats/tree/v0.1.0/powerbi).
