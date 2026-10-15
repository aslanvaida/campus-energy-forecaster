import numpy as np
import pandas as pd
import pytest

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def make_frame(n=360, seed=0):
    """Small synthetic frame with the same columns as the datathon CSV."""
    r = np.random.RandomState(seed)
    df = pd.DataFrame({
        "id": np.arange(n),
        "building_id": r.choice(["B1", "B2", "B3"], n),
        "building_type": "office",
        "day_of_week": r.choice(DAYS, n),
        "hour": r.randint(0, 24, n),
        "month": r.randint(1, 13, n),
        "temperature": r.normal(25, 5, n),
        "humidity": r.uniform(40, 90, n),
        "occupancy": r.uniform(0, 100, n),
        "previous_usage": r.uniform(50, 150, n),
    })
    df.loc[df.building_id == "B3", "building_type"] = "lab"
    df["energy_usage"] = 0.8 * df.previous_usage + 0.3 * df.occupancy + r.normal(0, 2, n)
    return df


@pytest.fixture
def frame():
    return make_frame()


@pytest.fixture
def frame_with_gaps():
    df = make_frame(seed=1)
    r = np.random.RandomState(5)
    for c in ["temperature", "humidity", "occupancy", "previous_usage"]:
        df.loc[r.rand(len(df)) < 0.1, c] = np.nan
    return df
