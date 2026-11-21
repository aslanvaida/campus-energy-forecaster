"""Honest evaluation: forecast accuracy against a seasonal-naive baseline, band coverage, and waste-detector
precision / recall on synthetically injected faults (there are no real fault labels in public data)."""
import numpy as np
import pandas as pd

from campus_energy_forecaster.config import Assumptions
from campus_energy_forecaster.waste import detect_waste


def mae(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean(np.abs(y - p)))


def rmse(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def cv_rmse(y, p):
    """Coefficient of variation of RMSE (%), the usual building-energy accuracy measure (ASHRAE Guideline 14)."""
    return 100 * rmse(y, p) / float(np.mean(y))


def nmbe(y, p):
    """Normalised mean bias error (%): positive means the model under-predicts."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    return 100 * float(np.sum(y - p) / (len(y) * np.mean(y)))


def seasonal_naive(series: pd.Series, lag_hours: int = 168) -> pd.Series:
    """Same hour last week."""
    return series.shift(lag_hours)


def score_forecast(y: pd.Series, pred: pd.DataFrame, naive: pd.Series) -> dict:
    ok = y.notna() & pred["mid"].notna() & naive.notna()
    y, pred, naive = y[ok], pred[ok], naive[ok]
    inside = ((y >= pred["lo"]) & (y <= pred["hi"])).mean()
    return {"n_hours": int(ok.sum()), "mae_kw": round(mae(y, pred["mid"]), 3), "rmse_kw": round(rmse(y, pred["mid"]), 3),
            "cv_rmse_pct": round(cv_rmse(y, pred["mid"]), 2), "nmbe_pct": round(nmbe(y, pred["mid"]), 2),
            "naive_mae_kw": round(mae(y, naive), 3), "naive_cv_rmse_pct": round(cv_rmse(y, naive), 2),
            "mae_gain_vs_naive_pct": round(100 * (1 - mae(y, pred["mid"]) / mae(y, naive)), 1),
            "band_coverage_pct": round(100 * float(inside), 1), "band_nominal_pct": 80.0}


def inject_faults(actual: pd.Series, n_faults: int, seed: int = 0, extra_share=(0.25, 0.6), duration_hours=(6, 48),
                  min_gap_hours: int = 24 * 3) -> tuple[pd.Series, pd.DataFrame]:
    """Add a sustained extra load to ``n_faults`` random, non-overlapping windows.
    The extra load is a share of the typical (median) load, so it is realistic in scale. Returns the modified series
    and a table of the injected windows."""
    rng = np.random.RandomState(seed)
    out = actual.copy()
    typical = float(actual.median())
    n = len(actual)
    taken, rows = [], []
    tries = 0
    while len(rows) < n_faults and tries < 1000:
        tries += 1
        dur = int(rng.randint(duration_hours[0], duration_hours[1] + 1))
        s = int(rng.randint(24, n - dur - 24))
        if any(s < e + min_gap_hours and s + dur + min_gap_hours > b for b, e in taken):
            continue
        extra = typical * rng.uniform(*extra_share)
        out.iloc[s:s + dur] += extra
        taken.append((s, s + dur))
        rows.append({"start": actual.index[s], "end": actual.index[s + dur - 1], "hours": dur,
                     "extra_kw": extra, "extra_kwh": extra * dur})
    return out, pd.DataFrame(rows)


FAULT_SIZES = {"small": (0.25, 0.4), "medium": (0.5, 0.75), "large": (1.0, 1.5)}   # extra load as a share of the median load


def _overlap(s, e, a, b):
    return s <= b and a <= e


def score_detection(events, injected: pd.DataFrame) -> dict:
    """Event-level recall of the injected faults, and the share of the injected kWh that flagged events account for."""
    if injected.empty:
        return {}
    ev = [(pd.Timestamp(e.start), pd.Timestamp(e.end), e.excess_kwh) for e in events]
    found = [any(_overlap(r.start, r.end, s, e) for s, e, _ in ev) for r in injected.itertuples()]
    kwh = sum(k for s, e, k in ev if any(_overlap(r.start, r.end, s, e) for r in injected.itertuples()))
    return {"injected_faults": int(len(injected)), "recall_pct": round(100 * float(np.mean(found)), 1),
            "flagged_kwh_over_injected_kwh_pct": round(100 * kwh / float(injected["extra_kwh"].sum()), 1)}


def run_detection_benchmark(meter: str, actual: pd.Series, band: pd.DataFrame, n_faults=20, seed=0,
                            assumptions: Assumptions = Assumptions(), **detect_kw) -> dict:
    """Inject synthetic faults of three sizes into held-out actuals and see how many the detector finds.
    ``flagged_events_per_30d`` counts events on the unmodified data: they are unlabelled (they may be real faults or
    regime changes) and are the practical alert rate."""
    clean = detect_waste(meter, actual, band, assumptions=assumptions, **detect_kw)
    out = {"flagged_events_per_30d": round(len(clean) * 30 / (len(actual) / 24), 2), "by_size": []}
    for name, share in FAULT_SIZES.items():
        faulty, inj = inject_faults(actual, n_faults, seed, extra_share=share)
        events = detect_waste(meter, faulty, band, assumptions=assumptions, **detect_kw)
        out["by_size"].append({"size": name, "extra_load_pct_of_median": [int(100 * share[0]), int(100 * share[1])],
                               **score_detection(events, inj)})
    return out
