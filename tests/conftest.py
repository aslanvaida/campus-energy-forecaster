import numpy as np
import pandas as pd
import pytest


def make_hourly(days=120, seed=0):
    """Synthetic office-like hourly frame: weekday daytime load driven by occupancy and temperature."""
    r = np.random.RandomState(seed)
    idx = pd.date_range("2022-01-03", periods=24 * days, freq="h")
    hour, wd = idx.hour.values, idx.dayofweek.values < 5
    occ = np.where(wd & (hour >= 8) & (hour < 18), 40, 0) * r.uniform(0.7, 1.1, len(idx))
    temp = 15 + 8 * np.sin(2 * np.pi * (idx.dayofyear.values - 100) / 365) + 4 * np.sin(2 * np.pi * (hour - 9) / 24) + r.normal(0, 1, len(idx))
    load = 20 + 0.5 * occ + 0.8 * np.clip(temp - 18, 0, None) + r.normal(0, 0.8, len(idx))
    return pd.DataFrame({"hvac": load, "temp": temp, "rh": 60.0, "solar": np.clip(np.sin(2 * np.pi * (hour - 6) / 24), 0, None) * 500,
                         "occupancy": occ}, index=idx)


@pytest.fixture
def hourly():
    return make_hourly()
