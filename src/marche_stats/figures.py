"""Static figures (PNG) for the README and the results page."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

from marche_stats.eurostat import NUTS3_NAMES  # noqa: E402

NUTS3_ABBREVIATIONS = {
    "ITI31": "PU",
    "ITI32": "AN",
    "ITI33": "MC",
    "ITI34": "AP",
    "ITI35": "FM",
}
from marche_stats.timeseries import Evaluation  # noqa: E402

# Validated categorical order (blue, orange, aqua, yellow, magenta) and a one-hue
# sequential ramp; text stays in neutral inks.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
)
INK, INK_MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_MUTED,
        "axes.titlecolor": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "font.size": 10,
        "legend.frameon": False,
        "lines.linewidth": 2,
    }
)


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _rings(geometry: dict) -> list[list[list[float]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    return [polygon[0] for polygon in geometry["coordinates"]]


def _centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """Area-weighted centroid and absolute area of a polygon ring (shoelace formula)."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    return cx / (6 * area), cy / (6 * area), abs(area)


def nuts3_maps(geojson_path: Path, indicators: pd.DataFrame, path: Path) -> None:
    """A 2x2 grid of small maps, one per indicator column (index: NUTS 3 code).

    Each region is labelled with its province abbreviation and value, so the map
    can be read without relying on colour alone.
    """
    features = json.loads(geojson_path.read_text(encoding="utf-8"))["features"]
    columns = list(indicators.columns)
    fig, axes = plt.subplots(2, 2, figsize=(9, 9.5))
    for ax, column in zip(axes.flat, columns, strict=True):
        values = indicators[column]
        norm = plt.Normalize(values.min(), values.max())
        for feature in features:
            code = feature["properties"]["NUTS_ID"]
            rings = _rings(feature["geometry"])
            for ring in rings:
                ax.add_patch(
                    Polygon(
                        ring,
                        facecolor=SEQUENTIAL(norm(values[code])),
                        edgecolor=SURFACE,
                        linewidth=1.5,
                    )
                )
            x, y, _ = max((_centroid(ring) for ring in rings), key=lambda c: c[2])
            ax.text(
                x,
                y,
                f"{NUTS3_ABBREVIATIONS[code]}\n{values[code]:,.1f}",
                ha="center",
                va="center",
                fontsize=8.5,
                color=INK if norm(values[code]) < 0.5 else "#ffffff",
            )
        ax.autoscale_view()
        ax.set_aspect(1.3)
        ax.axis("off")
        ax.set_title(textwrap.fill(column, 34), fontsize=10)
    fig.text(
        0.01,
        0.0,
        "PU Pesaro e Urbino · AN Ancona · MC Macerata · AP Ascoli Piceno · FM Fermo. "
        "Darker = higher value within each map.",
        fontsize=8.5,
        color=INK_MUTED,
    )
    _save(fig, path)


def province_index(province_totals: pd.DataFrame, base: pd.Timestamp, path: Path) -> None:
    """Active companies per province, indexed to `base` = 100 (five series: legend only)."""
    wide = province_totals.pivot(index="date", columns="nuts3", values="active_companies")
    index = 100 * wide / wide.loc[base]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for color, code in zip(SERIES, NUTS3_NAMES, strict=True):
        ax.plot(index.index, index[code], color=color, label=NUTS3_NAMES[code])
    ax.axhline(100, color=INK_MUTED, linewidth=0.8)
    ax.set_title(f"Active companies by province, index {base:%B %Y} = 100")
    ax.set_ylabel("Index")
    ax.legend(loc="lower left", ncols=5, fontsize=8.5)
    _save(fig, path)


def decomposition(components: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9, 6.5), sharex=True)
    axes[0].plot(components.index, components["observed"], color=SERIES[0], label="Observed")
    axes[0].plot(
        components.index,
        components["trend"],
        color=INK_MUTED,
        linewidth=1.2,
        linestyle="--",
        label="Trend",
    )
    axes[0].legend(loc="upper right", fontsize=8.5)
    axes[0].set_title("Active companies in the Marche region (monthly, STL decomposition)")
    axes[1].plot(components.index, components["seasonal"], color=SERIES[0])
    axes[1].set_ylabel("Seasonal")
    axes[2].plot(components.index, components["resid"], color=SERIES[0], linewidth=1)
    axes[2].set_ylabel("Remainder")
    _save(fig, path)


def forecast_chart(
    series: pd.Series, evaluation: Evaluation, future: pd.DataFrame, path: Path
) -> None:
    holdout = evaluation.holdout_forecast
    start = series.index[-72]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(series[start:].index, series[start:], color=INK, linewidth=1.5, label="Observed")
    ax.plot(holdout.index, holdout["SARIMA"], color=SERIES[0], label="SARIMA, out-of-sample test")
    ax.plot(
        holdout.index,
        holdout["Naive (last value)"],
        color=SERIES[1],
        linestyle="--",
        label="Naive baseline",
    )
    ax.plot(future.index, future["forecast"], color=SERIES[2], label="SARIMA forecast")
    ax.fill_between(
        future.index,
        future["lower_95"],
        future["upper_95"],
        color=SERIES[2],
        alpha=0.18,
        linewidth=0,
        label="95 % interval",
    )
    ax.axvline(holdout.index[0], color=GRID, linewidth=1)
    ax.set_title("Active companies in the Marche region: test period and 12-month forecast")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.legend(loc="upper right", fontsize=8.5)
    _save(fig, path)


# v0.2: the Marche against Italy and the EU27 (blue, orange, aqua in SERIES order).
COMPARED = {"ITI3": "Marche", "IT": "Italy", "EU27_2020": "EU27"}


def mortality_chart(fact_mortality: pd.DataFrame, path: Path) -> None:
    """Standardised (with the Marche 95 % interval) and crude death rates, both sexes."""
    total = fact_mortality[fact_mortality["sex_code"] == "T"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for color, (code, name) in zip(SERIES, COMPARED.items(), strict=False):
        rows = total[total["geo_code"] == code]
        axes[0].plot(rows["year"], rows["std_rate"], color=color, label=name)
        axes[1].plot(rows["year"], rows["crude_rate"], color=color, label=name)
        if code == "ITI3":
            axes[0].fill_between(
                rows["year"], rows["ci_low"], rows["ci_high"], color=color, alpha=0.18, linewidth=0
            )
    axes[0].set_title("Age-standardised (ESP 2013)")
    axes[1].set_title("Crude")
    axes[0].set_ylabel("Deaths per 100,000")
    axes[0].legend(loc="upper left", fontsize=8.5)
    fig.suptitle("Death rates, both sexes", x=0.01, ha="left", fontweight="bold")
    _save(fig, path)


def indicator_panels(fact_indicator: pd.DataFrame, path: Path) -> None:
    """One panel per indicator: the Marche, Italy and the EU27, with the EU 2030 target.

    Values flagged as low reliability (u) are drawn as hollow markers.
    """
    from marche_stats.indicators import INDICATORS

    total = fact_indicator[fact_indicator["sex_code"] == "T"]
    fig, axes = plt.subplots(2, 3, figsize=(11, 7))
    fig.subplots_adjust(hspace=0.55, wspace=0.3)
    for ax, indicator in zip(axes.flat, INDICATORS, strict=False):
        data = total[total["indicator_code"] == indicator.code]
        for color, (code, name) in zip(SERIES, COMPARED.items(), strict=False):
            rows = data[data["geo_code"] == code]
            ax.plot(rows["year"], rows["value"], color=color, label=name)
            low = rows[rows["flag"].str.contains("u")]
            ax.scatter(low["year"], low["value"], facecolors=SURFACE, edgecolors=color, zorder=3)
        if indicator.eu_2030_target is not None:
            ax.axhline(indicator.eu_2030_target, color=INK_MUTED, linestyle=":", linewidth=1)
        ax.set_title(textwrap.fill(indicator.name, 34), fontsize=9.5)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True, nbins=5))
    axes.flat[0].legend(loc="best", fontsize=8)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0,
        0.5,
        "Dotted line: EU 2030 target.\nHollow marker: low reliability (u).",
        color=INK_MUTED,
        fontsize=9,
    )
    _save(fig, path)


def enrolment_index_chart(index: pd.DataFrame, path: Path) -> None:
    """Enrolment index (2013 = 100) for ISCED 0-3: the Marche against Italy."""
    levels = {"ED0": "Early childhood", "ED1": "Primary", "ED2": "Lower secondary"}
    levels["ED3"] = "Upper secondary"
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.4), sharey=True)
    for ax, (level, label) in zip(axes, levels.items(), strict=True):
        for color, code in zip(SERIES, ("ITI3", "IT"), strict=False):
            rows = index[(index["geo_code"] == code) & (index["isced_code"] == level)]
            ax.plot(rows["year"], rows["index"], color=color, label=COMPARED[code])
        ax.axhline(100, color=INK_MUTED, linewidth=0.8)
        ax.set_title(label, fontsize=9.5)
    axes[0].set_ylabel("Index, 2013 = 100")
    axes[0].legend(loc="lower left", fontsize=8)
    _save(fig, path)
