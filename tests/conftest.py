"""Synthetic active-companies file in the same layout as the real source.

The real file is not redistributed (see the README), so tests build a small one:
six municipalities, one per province (two in Ancona), plus one transferred municipality, two ATECO
sections and their TOTAL rows, monthly from March 2009, with trend and seasonality.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
MONTHS = pd.date_range("2009-03-31", periods=96, freq="ME")


def _series(level: float, trend: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(len(MONTHS))
    seasonal = -0.01 * level * np.isin(MONTHS.month, [1, 2])
    return np.round(level + trend * t + seasonal + rng.normal(0, 2, len(t))).astype(int)


def synthetic_wide() -> pd.DataFrame:
    territories = {
        "AN-01 Alfa": (400, -0.5, 1),
        "AN-02 Beta": (300, -0.3, 2),
        "MC-01 Gamma": (500, -0.8, 3),
        "PU-01 Delta": (350, -0.4, 5),
        "AP-01 Epsilon": (250, -0.2, 6),
        "FM-01 Zeta": (150, -0.1, 7),
        "PU-42 Pennabilli": (200, 0.0, 4),  # transferred to Emilia-Romagna
    }
    rows = []
    for name, (level, trend, seed) in territories.items():
        section_a = _series(level * 0.6, trend * 0.6, seed)
        section_g = _series(level * 0.4, trend * 0.4, seed + 10)
        if name.startswith("PU-42"):
            section_a[11:] = 0  # leaves the region after one year
            section_g[11:] = 0
        for sector, values in (
            ("A", section_a),
            ("G", section_g),
            ("TOTAL", section_a + section_g),
        ):
            rows.append([name, sector, *values])
    columns = ["Territorio", "Settore Ateco 2007", *MONTHS.strftime("%d/%m/%Y")]
    return pd.DataFrame(rows, columns=columns)


@pytest.fixture
def wide() -> pd.DataFrame:
    return synthetic_wide()


@pytest.fixture
def companies_csv(tmp_path: Path) -> Path:
    path = tmp_path / "companies.csv"
    synthetic_wide().to_csv(path, sep=";", index=False)
    return path
