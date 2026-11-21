"""Peak-load management: forecast tomorrow's demand peak, and estimate how much shifting flexible load out of it would cut it.

Peak demand matters because many commercial tariffs bill on the highest kW of the month and because a high peak is what a
backup system or a weak local grid struggles with. This module reports kW, not dollars: the demand charge is tariff-specific.
"""
import numpy as np
import pandas as pd


def daily_peaks(load: pd.Series, min_hours: int = 20) -> pd.DataFrame:
    """Peak kW and the hour it happened, per calendar day. Days with fewer than ``min_hours`` readings are NaN."""
    g = load.groupby(load.index.normalize())
    out = pd.DataFrame({"kw": g.max(), "hour": g.apply(lambda s: s.idxmax().hour if s.notna().any() else np.nan), "n": g.count()})
    out.loc[out["n"] < min_hours, ["kw", "hour"]] = np.nan
    return out[["kw", "hour"]]


def peak_forecast_accuracy(actual: pd.Series, forecast: pd.Series, top_share: float = 0.1) -> dict:
    """How well the day-ahead forecast predicts each day's peak: size, timing, and whether it finds the highest-peak days."""
    a, f = daily_peaks(actual), daily_peaks(forecast)
    ok = a["kw"].notna() & f["kw"].notna()
    a, f = a[ok], f[ok]
    k = max(1, int(round(top_share * len(a))))
    top_actual = set(a["kw"].nlargest(k).index)
    flagged = set(f["kw"].nlargest(2 * k).index)           # flag twice as many days as the true top set
    hour_gap = (a["hour"] - f["hour"]).abs()
    return {"n_days": int(len(a)), "mae_kw": float(np.mean(np.abs(a["kw"] - f["kw"]))),
            "mape_pct": float(100 * np.mean(np.abs(a["kw"] - f["kw"]) / a["kw"])),
            "peak_hour_within_2h_pct": float(100 * (hour_gap <= 2).mean()),
            "top_days": k, "top_days_caught_pct": float(100 * len(top_actual & flagged) / k)}


def _fill_level(base: np.ndarray, energy: float) -> float:
    """Level L such that raising every value below L up to L adds exactly ``energy`` (water-filling)."""
    lo, hi = float(base.min()), float(base.max()) + energy
    for _ in range(60):
        mid = (lo + hi) / 2
        if np.clip(mid - base, 0, None).sum() < energy:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def shift_flexible_load(total: pd.Series, flexible: pd.Series, window_mask: pd.Series, share: float) -> pd.Series:
    """Move ``share`` of the flexible load drawn inside the ``window_mask`` hours to the lowest-load hours of the same day
    outside the window (pre-cooling, or deferring), filling the valleys first so no new peak is created. Energy is conserved.
    This is the best case a load-shifting schedule could reach, so the estimate is an upper bound on the reduction."""
    out = total.copy()
    moved = flexible.where(window_mask, 0.0).fillna(0.0) * share
    out = out - moved
    for day, m in moved[moved > 0].groupby(moved[moved > 0].index.normalize()):
        day_ix = out.index[out.index.normalize() == day]
        cand = day_ix[~window_mask.reindex(day_ix, fill_value=False).values & out.loc[day_ix].notna().values]
        if len(cand) == 0:
            out.loc[m.index] += m.values                      # nowhere to put it: leave the load where it was
            continue
        base = out.loc[cand].values.astype(float)
        level = _fill_level(base, float(m.sum()))
        out.loc[cand] = np.maximum(base, level)
    return out


def peak_shift_estimate(actual_total: pd.Series, actual_flex: pd.Series, forecast_total: pd.Series, share: float,
                        flag_share: float = 0.1, window_frac: float = 0.9) -> dict:
    """Plan from the forecast, score on what happened. On the days whose forecast peak is in the top ``flag_share`` of the
    year, the hours within ``window_frac`` of that day's forecast peak form the window; ``share`` of the flexible load drawn
    in it is moved to that day's lowest-load hours. The reduction is measured on the actual load."""
    fp = daily_peaks(forecast_total)["kw"].dropna()
    flagged = fp[fp >= fp.quantile(1 - flag_share)].index
    day_peak = forecast_total.groupby(forecast_total.index.normalize()).transform("max")
    mask = (forecast_total >= window_frac * day_peak) & forecast_total.index.normalize().isin(flagged)
    shifted = shift_flexible_load(actual_total, actual_flex, mask.reindex(actual_total.index, fill_value=False), share)
    before, after = daily_peaks(actual_total)["kw"], daily_peaks(shifted)["kw"]
    f = before.index.isin(flagged) & before.notna() & after.notna()
    red = (before[f] - after[f])
    return {"share_shifted_pct": int(round(100 * share)), "days_acted_on": int(f.sum()),
            "mean_peak_reduction_kw": float(red.mean()), "mean_peak_reduction_pct": float(100 * (red / before[f]).mean()),
            "annual_peak_before_kw": float(before.max()), "annual_peak_after_kw": float(after.max()),
            "energy_conserved": bool(abs(np.nansum(actual_total.values) - np.nansum(shifted.values)) < 1e-6 * max(1.0, abs(np.nansum(actual_total.values))))}
