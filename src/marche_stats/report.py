"""Run the analysis and write docs/results.md with its figures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from marche_stats import companies, eurostat, figures, timeseries


def _table(frame: pd.DataFrame, floatfmt: str = "{:,.1f}") -> str:
    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    divider = "|" + "|".join("---" for _ in frame.columns) + "|"
    rows = []
    for row in frame.itertuples(index=False):
        cells = [floatfmt.format(v) if isinstance(v, float) else str(v) for v in row]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, divider, *rows]) + "\n"


def build(companies_csv: Path, eurostat_dir: Path, docs: Path, holdout: int = 24) -> str:
    figures_dir = docs / "figures"
    wide = companies.read_wide(companies_csv)
    checks = companies.quality_checks(wide)
    stale = companies.stale_months(wide)
    long = companies.to_long(wide)

    series = companies.regional_series(long)
    if stale:
        # A month identical to the previous one in every cell is treated as not updated.
        series = series[series.index < min(stale)]

    strength = timeseries.seasonal_strength(series)
    components = timeseries.decompose(series)
    evaluation = timeseries.evaluate(series, holdout=holdout)
    future = timeseries.forecast(series, evaluation.order, evaluation.seasonal_order, steps=12)

    provinces = companies.province_totals(long)
    provinces = provinces[provinces["date"] <= series.index[-1]]
    december = provinces[provinces["date"].dt.month == 12]
    first_dec, last_dec = december["date"].min(), december["date"].max()

    demo = eurostat.demography(eurostat_dir)
    population_year = int(last_dec.year) + 1  # population on 1 January after the last December
    pop = demo[demo["year"] == population_year].set_index("geo")
    deaths_year = int(demo.dropna(subset=["deaths"])["year"].max())
    rate = demo[demo["year"] == deaths_year].set_index("geo")["crude_death_rate"]
    pop_base = demo[demo["year"] == int(first_dec.year) + 1].set_index("geo")["population"]

    by_province = december.pivot(index="nuts3", columns="date", values="active_companies")
    nuts3 = list(eurostat.NUTS3_NAMES)
    indicators = pd.DataFrame(
        {
            f"Active companies per 1,000 residents, {last_dec:%b %Y}": 1000
            * by_province[last_dec]
            / pop["population"].reindex(by_province.index),
            f"Change in active companies, {first_dec:%Y}-{last_dec:%Y} (%)": 100
            * (by_province[last_dec] / by_province[first_dec] - 1),
            f"Population change, {first_dec.year + 1}-{population_year} (%)": 100
            * (pop["population"] / pop_base - 1),
            f"Residents aged 65+, 1 Jan {population_year} (%)": pop["share_65_plus"],
            f"Crude death rate per 1,000, {deaths_year}": rate,
        }
    ).reindex(nuts3)

    figures.nuts3_maps(
        eurostat_dir / "marche_nuts3.geojson",
        indicators.iloc[:, [0, 1, 3, 4]],
        figures_dir / "nuts3_maps.png",
    )
    figures.province_index(provinces, first_dec, figures_dir / "province_index.png")
    figures.decomposition(components, figures_dir / "decomposition.png")
    figures.forecast_chart(series, evaluation, future, figures_dir / "forecast.png")

    province_table = indicators.copy()
    province_table.insert(0, "Province", [eurostat.NUTS3_NAMES[c] for c in nuts3])
    province_table.insert(0, "NUTS 3", nuts3)
    errors = evaluation.errors.reset_index().rename(columns={"index": "Method"})
    future_table = future.reset_index().rename(columns={"index": "Month"})
    future_table["Month"] = future_table["Month"].dt.strftime("%Y-%m")
    checks_table = pd.DataFrame(
        [(c.name, "pass" if c.passed else "FAIL", c.detail) for c in checks],
        columns=["Check", "Result", "Detail"],
    )
    seasonal_profile = components["seasonal"].groupby(components.index.month).mean().round(0)

    generated = datetime.now(UTC).strftime("%Y-%m-%d")
    lines = [
        "# Results",
        "",
        f"Generated {generated} by `marche-stats run`. Methods and caveats: "
        "[methodology note](methodology.md).",
        "",
        "## 1. Source data checks (active companies file)",
        "",
        _table(checks_table),
        f"Months identical to the previous one in every cell are treated as not updated: "
        f"{', '.join(f'{d:%Y-%m}' for d in stale) or 'none'}. The time series stops before "
        f"the first of them, because SARIMA needs consecutive months, so it runs from "
        f"{series.index[0]:%Y-%m} to {series.index[-1]:%Y-%m} ({len(series)} months) and later "
        f"months in the file are not used.",
        "",
        "## 2. Provinces (NUTS 3)",
        "",
        "![Indicators by province](figures/nuts3_maps.png)",
        "",
        _table(province_table),
        "![Active companies by province, indexed](figures/province_index.png)",
        "",
        "## 3. Seasonality",
        "",
        f"Seasonal strength (STL, 0 = none, 1 = purely seasonal): **{strength:.2f}**. "
        "Average seasonal effect by calendar month, in number of active companies:",
        "",
        _table(
            pd.DataFrame(
                [seasonal_profile.to_numpy()],
                columns=[pd.Timestamp(2000, m, 1).strftime("%b") for m in range(1, 13)],
            ),
            "{:+,.0f}",
        ),
        "![STL decomposition](figures/decomposition.png)",
        "",
        "## 4. SARIMA model",
        "",
        f"Specification chosen by AIC on the training period (up to "
        f"{series.index[-holdout - 1]:%Y-%m}): SARIMA{evaluation.order}"
        f"{evaluation.seasonal_order[:3]}[{evaluation.seasonal_order[3]}], "
        f"AIC {evaluation.aic:,.1f}.",
        "",
        f"Out-of-sample errors over the last {holdout} months "
        f"({series.index[-holdout]:%Y-%m} to {series.index[-1]:%Y-%m}), forecasting from the "
        "end of the training period without updating:",
        "",
        _table(errors, "{:,.2f}"),
        f"Share of test months inside the SARIMA 95 % prediction interval: "
        f"**{100 * evaluation.interval_coverage:.0f} %** (nominal 95 %).",
        "",
        "![Test period and forecast](figures/forecast.png)",
        "",
        "12-month forecast, refitted on the full series:",
        "",
        _table(future_table, "{:,.0f}"),
    ]
    text = "\n".join(lines)
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "results.md").write_text(text, encoding="utf-8")
    return text
