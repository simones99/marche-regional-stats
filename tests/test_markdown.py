import pandas as pd

from marche_stats.markdown import table


def test_table_formats_floats_and_shows_missing_values_as_a_dash():
    frame = pd.DataFrame({"Area": ["Marche", "EU27"], "Rate": [7.66, float("nan")]})
    assert table(frame) == ("| Area | Rate |\n|---|---|\n| Marche | 7.7 |\n| EU27 | – |\n")
