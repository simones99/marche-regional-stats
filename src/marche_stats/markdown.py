"""Markdown helpers for the results page."""

from __future__ import annotations

import math

import pandas as pd


def _cell(value: object, floatfmt: str) -> str:
    if isinstance(value, float):
        return "–" if math.isnan(value) else floatfmt.format(value)
    return str(value)


def table(frame: pd.DataFrame, floatfmt: str = "{:,.1f}") -> str:
    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    divider = "|" + "|".join("---" for _ in frame.columns) + "|"
    rows = []
    for row in frame.itertuples(index=False):
        cells = [_cell(v, floatfmt) for v in row]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, divider, *rows]) + "\n"
