"""Check the method on many buildings: schools and healthcare buildings from the Building Data Genome Project 2 (BDG2).

BDG2 (Miller et al., Scientific Data 2020, CC BY 4.0) has hourly electricity for 1,636 buildings at 19 sites in 2016-2017,
with each building's primary use and site weather. Only the whole-building electricity meter and air temperature are used here.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from campus_energy_forecaster.config import BDG2_DIR
from campus_energy_forecaster.evaluation import FAULT_SIZES, inject_faults, score_detection, score_forecast, seasonal_naive
from campus_energy_forecaster.forecast import walk_forward
from campus_energy_forecaster.waste import detect_waste

USAGES = {"Education": "Schools and colleges", "Healthcare": "Healthcare buildings"}


def select_buildings(root: Path = BDG2_DIR, per_usage: int = 15, min_coverage: float = 0.95, seed: int = 0) -> pd.DataFrame:
    """Random sample (fixed seed) of buildings of each primary use whose electricity meter is at least ``min_coverage`` complete
    in both 2016 and 2017. Returns metadata rows."""
    meta = pd.read_csv(root / "metadata.csv")
    elec = pd.read_csv(root / "electricity_cleaned.csv", index_col=0, parse_dates=True)
    cover = pd.DataFrame({"c16": elec.loc["2016"].notna().mean(), "c17": elec.loc["2017"].notna().mean()})
    ok = cover[(cover.c16 >= min_coverage) & (cover.c17 >= min_coverage)].index
    meta = meta[meta.building_id.isin(ok) & meta.primaryspaceusage.isin(USAGES)]
    rng = np.random.RandomState(seed)
    picks = [g.iloc[rng.permutation(len(g))[:per_usage]] for _, g in meta.groupby("primaryspaceusage")]
    return pd.concat(picks)


def building_frame(building_id: str, site_id: str, root: Path = BDG2_DIR, elec=None, weather=None) -> pd.DataFrame:
    """Hourly frame with ``total`` (kW; the meter is kWh per hour) and ``temp`` (degC)."""
    elec = elec if elec is not None else pd.read_csv(root / "electricity_cleaned.csv", index_col=0, parse_dates=True)
    weather = weather if weather is not None else pd.read_csv(root / "weather.csv", parse_dates=["timestamp"])
    w = weather[weather.site_id == site_id].set_index("timestamp")["airTemperature"].rename("temp")
    w = w[~w.index.duplicated()].asfreq("h").interpolate(limit=6)
    df = pd.DataFrame({"total": elec[building_id]}).join(w)
    df.index.name = "timestamp"
    return df


def evaluate_building(df: pd.DataFrame, n_faults: int = 20, seed: int = 7) -> dict:
    """Walk-forward over 2017 (trailing 12 months, so 2016 is the first training year), scored against same-hour-last-week,
    plus the fault-injection benchmark on the expected-usage band."""
    start, end = "2017-01-01", "2017-12-01"
    day = walk_forward(df, "total", "forecast", start, end, 12)
    base = walk_forward(df, "total", "expected", start, end, 12)
    y = df["total"].loc[day.index]
    m = score_forecast(y, day, seasonal_naive(df["total"]).loc[day.index])
    actual = df["total"].loc[base.index]
    clean = detect_waste("total", actual, base)
    out = {**m, "flagged_events_per_30d": len(clean) * 30 / (len(actual) / 24), "mean_kw": float(actual.mean())}
    for name, share in FAULT_SIZES.items():
        faulty, inj = inject_faults(actual.fillna(actual.median()), n_faults, seed, extra_share=share)
        out[f"recall_{name}_pct"] = score_detection(detect_waste("total", faulty, base), inj).get("recall_pct")
    return out
