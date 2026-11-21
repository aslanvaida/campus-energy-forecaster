"""Step 1 of the analysis: out-of-sample walk-forward predictions for every end use, 2019-01 to 2020-12.

Writes data/processed/predictions_<target>_<feature_set>.csv (lo, mid, hi per hour). Takes several minutes.
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from joblib import Parallel, delayed

from campus_energy_forecaster.config import DATA_DIR
from campus_energy_forecaster.data import load_building
from campus_energy_forecaster.forecast import walk_forward

warnings.filterwarnings("ignore")
TARGETS = ["hvac", "lighting", "plug", "total"]
FEATURE_SETS = ["expected", "forecast"]
# Trailing training window in months. HVAC (and so the total) changed operating level several times in 2018-19 (see the
# README), so those models use the most recent 6 months; the stable plug and lighting meters use 12.
# These were chosen by comparing 6 / 12 months / all history on the 2019 results, so 2019 metrics are mildly optimistic.
TRAIN_MONTHS = {"hvac": 6, "total": 6, "plug": 12, "lighting": 12}
START, END = "2019-01-01", "2020-12-01"
OUT = DATA_DIR / "processed"


def run(df, target, fs):
    p = walk_forward(df, target, fs, START, END, TRAIN_MONTHS[target])
    p.to_csv(OUT / f"predictions_{target}_{fs}.csv")
    return target, fs, len(p)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_building()
    for t, fs, n in Parallel(n_jobs=-1)(delayed(run)(df, t, fs) for t in TARGETS for fs in FEATURE_SETS):
        print(f"{t:9s} {fs:9s} {n} hours")
