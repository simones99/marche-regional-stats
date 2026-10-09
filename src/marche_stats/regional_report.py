"""The v0.2 sections of docs/results.md: mortality, education and economy."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from marche_stats import economy, education, figures, indicators, model, mortality
from marche_stats.eurostat import COMPARISON_GEOS, FOCUS_GEO, GEO_NAMES, read_sdmx
from marche_stats.markdown import table


def _comparison_table(
    compared: pd.DataFrame, codes: tuple[str, ...], with_target: bool = True
) -> pd.DataFrame:
    rows = compared[compared["indicator_code"].isin(codes)].copy()
    rows.insert(0, "Indicator", rows["indicator_code"].map(lambda c: indicators.BY_CODE[c].name))
    rows["Rank"] = (
        rows["rank_among_regions"].astype(str) + " of " + rows["regions_ranked"].astype(str)
    )
    rows["Change since"] = rows["first_year"].astype(str)
    return rows.rename(
        columns={
            "year": "Year",
            "marche": "Marche",
            "italy": "Italy",
            "eu27": "EU27",
            "gap_vs_italy": "Gap vs Italy",
            "gap_vs_eu27": "Gap vs EU27",
            "change_since_first_year": "Change",
            "distance_to_eu_target": "Distance to EU target",
        }
    )[
        [
            "Indicator",
            "Year",
            "Marche",
            "Italy",
            "EU27",
            "Gap vs Italy",
            "Gap vs EU27",
            "Rank",
            "Change since",
            "Change",
            *(["Distance to EU target"] if with_target else []),
        ]
    ]


def sections(eurostat_dir: Path, figures_dir: Path) -> list[str]:
    fact_mortality = mortality.mortality_table(eurostat_dir)
    five_year = mortality.five_year_table(eurostat_dir)
    benchmark = mortality.benchmark_differences(fact_mortality)
    benchmark_all = mortality.benchmark_differences(fact_mortality, geos=COMPARISON_GEOS)
    unknown = mortality.unknown_age_share(read_sdmx(eurostat_dir / "regional_deaths.csv"))
    education_fact = education.education_indicators(eurostat_dir)
    economy_fact = economy.economy_indicators(eurostat_dir)
    compared = indicators.comparisons(pd.concat([education_fact, economy_fact]))
    enrolment_index = education.enrolment_index(education.enrolment(eurostat_dir))

    figures.mortality_chart(fact_mortality, figures_dir / "mortality.png")
    figures.indicator_panels(
        pd.concat([education_fact, economy_fact]), figures_dir / "indicators.png"
    )
    figures.enrolment_index_chart(enrolment_index, figures_dir / "enrolment_index.png")

    total = fact_mortality[fact_mortality["sex_code"] == "T"]
    latest = int(total.loc[total["geo_code"] == FOCUS_GEO, "year"].max())
    latest_rates = total[total["year"] == latest].set_index("geo_code").reindex(COMPARISON_GEOS)
    latest_rates = latest_rates.dropna(subset=["std_rate"]).reset_index()
    latest_rates.insert(0, "Area", latest_rates["geo_code"].map(GEO_NAMES))
    absent = [GEO_NAMES[g] for g in COMPARISON_GEOS if g not in set(latest_rates["geo_code"])]
    absent_note = (
        f"No complete {latest} data (deaths and population in every age group) for: "
        f"{', '.join(absent)}."
        if absent
        else ""
    )
    rates_table = latest_rates[["Area", "crude_rate", "std_rate", "ci_low", "ci_high"]].rename(
        columns={
            "crude_rate": "Crude",
            "std_rate": "Standardised",
            "ci_low": "95 % low",
            "ci_high": "95 % high",
        }
    )
    pooled = five_year[five_year["sex_code"] == "T"].set_index("geo_code")
    left_out = [GEO_NAMES[g] for g in COMPARISON_GEOS if g not in pooled.index]
    pooled = pooled.reindex([g for g in COMPARISON_GEOS if g in pooled.index]).reset_index()
    pooled.insert(0, "Area", pooled["geo_code"].map(GEO_NAMES))
    period = f"{int(pooled['period_start'].iloc[0])}-{int(pooled['period_end'].iloc[0])}"
    pooled_table = pooled[["Area", "std_rate", "ci_low", "ci_high"]].rename(
        columns={
            "std_rate": f"Standardised, {period}",
            "ci_low": "95 % low",
            "ci_high": "95 % high",
        }
    )
    benchmark_table = benchmark.assign(sex_code=benchmark["sex_code"].map(model.SEX_LABELS))
    benchmark_table = benchmark_table.drop(columns="geo_code").rename(
        columns={
            "year": "Year",
            "sex_code": "Sex",
            "std_rate": "This project",
            "eurostat_std_rate": "Eurostat (hlth_cd_asdr2)",
            "difference_pct": "Difference (%)",
        }
    )

    def _extreme(row: pd.Series) -> str:
        sex = model.SEX_LABELS[row["sex_code"]].lower()
        where = f"{GEO_NAMES[row['geo_code']]}, {sex}, {row['year']}"
        return f"{row['difference_pct']:+.1f} % ({where})"

    by_sex = benchmark_all[benchmark_all["sex_code"] != "T"]
    both = benchmark_all[benchmark_all["sex_code"] == "T"]["difference_pct"]
    benchmark_note = (
        "By sex, across every area with a published rate, the difference ranges from "
        f"{_extreme(by_sex.loc[by_sex['difference_pct'].idxmin()])} to "
        f"{_extreme(by_sex.loc[by_sex['difference_pct'].idxmax()])}; for both sexes it ranges "
        f"from {both.min():+.1f} % to {both.max():+.1f} %. Errors of opposite sign for males "
        "and females partly cancel in the total."
    )
    marche_years = set(total.loc[total["geo_code"] == FOCUS_GEO, "year"])
    partial = []
    for geo in COMPARISON_GEOS:
        years = sorted(set(total.loc[total["geo_code"] == geo, "year"]))
        if set(years) < marche_years:
            partial.append(f"{GEO_NAMES[geo]} only in {', '.join(map(str, years)) or 'no year'}")
    coverage_note = (
        "Complete deaths and population by age group: " + "; ".join(partial) + "."
        if partial
        else ""
    )
    marche_unknown = unknown[(unknown["geo"] == FOCUS_GEO) & (unknown["sex"] == "T")]
    unknown_max = float(marche_unknown["unknown_share"].max())

    return [
        "## 5. Mortality (age-standardised)",
        "",
        f"Death rates per 100,000 in {latest}, both sexes. Standardised rates use the European "
        "Standard Population 2013 with an open 85+ group and a Dobson 95 % interval.",
        "",
        table(rates_table),
        absent_note,
        "",
        "![Death rates](figures/mortality.png)",
        "",
        coverage_note,
        "",
        f"Pooled five-year rate, {period} (the latest five years with complete data for the six "
        "regions and Italy):",
        "",
        table(pooled_table),
        (
            f"Left out for lack of complete data in {period}: {', '.join(left_out)}."
            if left_out
            else ""
        ),
        "",
        "Check against Eurostat's published standardised rate for the Marche, by sex:",
        "",
        table(benchmark_table, "{:,.2f}"),
        benchmark_note,
        "",
        f"Deaths of unknown age, Marche: at most {unknown_max:.2f} % of the yearly total, "
        "redistributed in proportion to the known ages.",
        "",
        "## 6. Education",
        "",
        "Latest value of each indicator, both sexes. Gaps are in percentage points; rank 1 is "
        "the best of the six regions; distance to the EU 2030 target is positive when the "
        "target is met.",
        "",
        table(_comparison_table(compared, education.EDUCATION_INDICATORS)),
        "![Indicators](figures/indicators.png)",
        "",
        "Enrolment against Italy (the EU27 aggregate is incomplete in this dataset):",
        "",
        "![Enrolment index](figures/enrolment_index.png)",
        "",
        "## 7. Economy",
        "",
        "GDP per inhabitant in PPS compares areas within a year, not growth over time.",
        "",
        table(_comparison_table(compared, economy.ECONOMY_INDICATORS, with_target=False)),
    ]
