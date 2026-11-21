"""Emergency power planning: how long does a backup battery last during a grid outage, and which loads to keep?"""
from dataclasses import dataclass
from itertools import combinations

import numpy as np
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Backup:
    capacity_kwh: float            # nameplate energy
    usable_fraction: float = 0.9   # depth of discharge the battery may use
    efficiency: float = 0.92       # round-trip-style inverter / conversion efficiency applied to discharge
    max_power_kw: float | None = None   # inverter limit; loads above it cannot be served

    @property
    def usable_kwh(self) -> float:
        return self.capacity_kwh * self.usable_fraction * self.efficiency


def runtime_hours(load_kw: pd.Series, start, backup: Backup, horizon_hours: int = 24 * 14) -> float:
    """Hours the backup serves the hourly load profile (kW) starting at ``start``; fractional final hour.
    Stops early when the hourly load exceeds the inverter limit. Capped at ``horizon_hours``.
    Returns NaN if a missing value is reached before the battery runs out: the runtime is then unknown, not infinite."""
    seg = load_kw.loc[start:].iloc[:horizon_hours].values
    if len(seg) == 0:
        return float("nan")
    left = backup.usable_kwh
    for i, kw in enumerate(seg):
        if np.isnan(kw):
            return float("nan")
        if backup.max_power_kw is not None and kw > backup.max_power_kw:
            return float(i)
        if kw <= 0:
            continue
        if kw >= left:
            return float(i + left / kw)
        left -= kw
    return float(len(seg))


def splice_forecast(day_ahead: pd.Series, baseline: pd.Series, start, hours: int = 24) -> pd.Series:
    """Load forecast available at outage start: the day-ahead forecast (which uses usage from 24 h and 168 h before,
    all known at ``start``) for the first ``hours`` hours, then the baseline model, which needs no recent usage.
    The day-ahead model must not be used past 24 h: its lag-24 input would then come from inside the outage."""
    out = baseline.copy()
    end = start + pd.Timedelta(hours=hours - 1)
    out.loc[start:end] = day_ahead.loc[start:end]
    return out


def rank_load_sets(loads: dict[str, pd.Series], start, backup: Backup, must_keep: tuple[str, ...] = ()) -> list[dict]:
    """Runtime for every subset of loads that includes ``must_keep``, longest first.
    ``loads`` maps load name -> hourly kW profile (the forecast from ``start`` on)."""
    names = list(loads)
    optional = [n for n in names if n not in must_keep]
    rows = []
    for r in range(len(optional) + 1):
        for extra in combinations(optional, r):
            keep = tuple(n for n in names if n in must_keep or n in extra)
            if not keep:
                continue
            prof = sum(loads[n] for n in keep)
            rows.append({"keep": list(keep), "shed": [n for n in names if n not in keep],
                         "mean_kw": round(float(prof.loc[start:].iloc[:24].mean()), 2),
                         "runtime_h": round(runtime_hours(prof, start, backup), 1)})
    return sorted(rows, key=lambda r: -(r["runtime_h"] if not np.isnan(r["runtime_h"]) else -1))
