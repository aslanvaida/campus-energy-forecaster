"""Waste detection: flag stretches where a load runs above what conditions explain, and price them."""
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from campus_energy_forecaster.config import Assumptions


@dataclass
class WasteEvent:
    meter: str
    start: str
    end: str
    hours: int
    after_hours: bool
    mean_excess_kw: float
    excess_kwh: float           # actual minus expected (P50) over the event: the estimate if the issue were fixed
    excess_kwh_floor: float     # actual minus the alert threshold: a conservative lower bound
    cost_usd: float
    co2_kg: float

    def as_dict(self):
        return asdict(self)


def detect_waste(meter: str, actual: pd.Series, band: pd.DataFrame, occupancy: pd.Series | None = None,
                 min_hours: int = 3, max_gap_hours: int = 1, margin: float = 1.0, after_hours_occ_share: float = 0.1,
                 assumptions: Assumptions = Assumptions()) -> list[WasteEvent]:
    """Events are runs of at least ``min_hours`` consecutive hours above the alert threshold (gaps of up to
    ``max_gap_hours`` inside a run are bridged). The threshold is the upper band plus ``margin`` times the distance from
    the median to the upper band (margin=0 is the most sensitive setting; larger values raise fewer false alarms).
    If ``occupancy`` is given, an event is "after-hours" when mean occupancy during it is below
    ``after_hours_occ_share`` of the 95th-percentile occupancy."""
    thr = band["hi"] + margin * (band["hi"] - band["mid"])
    above = (actual > thr) & actual.notna() & thr.notna()
    flag = above.copy()
    if max_gap_hours > 0:  # bridge short gaps so one fault is not split into many
        grp = (above != above.shift()).cumsum()
        runs = above.groupby(grp).agg(["first", "size"])
        for g, (val, size) in runs.iterrows():
            if not val and size <= max_gap_hours:
                idx = grp[grp == g].index
                if idx[0] != actual.index[0] and idx[-1] != actual.index[-1]:
                    flag.loc[idx] = True
    run_id = (flag != flag.shift()).cumsum()
    occ_ref = float(occupancy.quantile(0.95)) if occupancy is not None and occupancy.notna().any() else None
    events = []
    for _, seg in flag[flag].groupby(run_id[flag]):
        if len(seg) < min_hours:
            continue
        ix = seg.index
        a, mid, hi = actual.loc[ix], band.loc[ix, "mid"], thr.loc[ix]
        kwh = float((a - mid).clip(lower=0).sum())
        floor = float((a - hi).clip(lower=0).sum())
        after = False
        if occ_ref:
            after = bool(occupancy.loc[ix].mean() < after_hours_occ_share * occ_ref)
        events.append(WasteEvent(meter, str(ix[0]), str(ix[-1]), len(ix), after, round(kwh / len(ix), 2), round(kwh, 1),
                                 round(floor, 1), round(kwh * assumptions.tariff_usd_per_kwh, 2),
                                 round(kwh * assumptions.carbon_kg_per_kwh, 1)))
    return events


def summarise(events: list[WasteEvent], days: float) -> dict:
    """Totals over an analysis window of ``days`` days, plus a simple annualisation."""
    tot = lambda f: round(float(sum(getattr(e, f) for e in events)), 1)
    return {"events": len(events), "excess_kwh": tot("excess_kwh"), "excess_kwh_floor": tot("excess_kwh_floor"),
            "cost_usd": tot("cost_usd"), "co2_kg": tot("co2_kg"), "window_days": round(days, 1),
            "after_hours_events": sum(e.after_hours for e in events),
            "annualised_excess_kwh": round(float(sum(e.excess_kwh for e in events)) * 365 / days, 0) if days else 0}
