"""Run the method on a random sample of schools and healthcare buildings from the public BDG2 dataset.

    python scripts/download_data.py bdg2     # once (pip install remotezip)
    python scripts/validate_buildings.py     # several minutes -> web/public/data/multibuilding.json
"""
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from campus_energy_forecaster.config import BDG2_DIR, WEB_DATA_DIR
from campus_energy_forecaster.multibuilding import USAGES, building_frame, evaluate_building, select_buildings

warnings.filterwarnings("ignore")
PER_USAGE = 15
OUT = WEB_DATA_DIR / "multibuilding.json"


def one(row, elec, weather):
    df = building_frame(row.building_id, row.site_id, elec=elec, weather=weather)
    return {"building_id": row.building_id, "usage": row.primaryspaceusage, "site_id": row.site_id, **evaluate_building(df)}


def med(x):
    return float(np.nanmedian(x))


def main():
    chosen = select_buildings(per_usage=PER_USAGE)
    elec = pd.read_csv(BDG2_DIR / "electricity_cleaned.csv", index_col=0, parse_dates=True)
    weather = pd.read_csv(BDG2_DIR / "weather.csv", parse_dates=["timestamp"])
    rows = Parallel(n_jobs=-1)(delayed(one)(r, elec, weather) for r in chosen.itertuples())
    df = pd.DataFrame(rows)
    groups = {}
    for usage, label in USAGES.items():
        g = df[df.usage == usage]
        groups[usage] = {"label": label, "n_buildings": int(len(g)), "n_sites": int(g.site_id.nunique()),
                         "median_mae_gain_vs_naive_pct": round(med(g.mae_gain_vs_naive_pct), 1),
                         "share_buildings_beating_naive_pct": round(100 * float((g.mae_gain_vs_naive_pct > 0).mean()), 0),
                         "median_cv_rmse_pct": round(med(g.cv_rmse_pct), 1),
                         "median_band_coverage_pct": round(med(g.band_coverage_pct), 1),
                         "median_flagged_events_per_30d": round(med(g.flagged_events_per_30d), 1),
                         "median_recall_pct": {k: round(med(g[f"recall_{k}_pct"]), 0) for k in ("small", "medium", "large")}}
    allg = {"n_buildings": int(len(df)), "median_mae_gain_vs_naive_pct": round(med(df.mae_gain_vs_naive_pct), 1),
            "share_buildings_beating_naive_pct": round(100 * float((df.mae_gain_vs_naive_pct > 0).mean()), 0),
            "median_band_coverage_pct": round(med(df.band_coverage_pct), 1)}
    out = {"dataset": {"name": "Building Data Genome Project 2 (BDG2)", "license": "CC BY 4.0", "source": "https://zenodo.org/records/3887306",
                       "citation": "Miller, C., Kathirgamanathan, A., Picchetti, B., et al. (2020). The Building Data Genome Project 2, "
                                   "energy meter data from the ASHRAE Great Energy Predictor III competition. Scientific Data."},
           "method": f"Random sample (fixed seed) of {PER_USAGE} buildings per use with at least 95% complete electricity data in 2016 and 2017. "
                     "Each month of 2017 is predicted by a model fitted on the trailing 12 months. Same code as the demo building, whole-building meter only.",
           "groups": groups, "all": allg,
           "buildings": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k in
                          ("building_id", "usage", "site_id", "mean_kw", "mae_gain_vs_naive_pct", "cv_rmse_pct", "band_coverage_pct")} for r in rows]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print("wrote", OUT)
    print(json.dumps({"groups": groups, "all": allg}, indent=1))


if __name__ == "__main__":
    main()
