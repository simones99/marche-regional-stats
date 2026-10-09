"""GDP per inhabitant in PPS and the unemployment rate."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from marche_stats import indicators

ECONOMY_INDICATORS = ("gdp_pps_index", "unemployment_15_74")


def economy_indicators(raw_dir: Path) -> pd.DataFrame:
    return indicators.load_many(raw_dir, ECONOMY_INDICATORS)
