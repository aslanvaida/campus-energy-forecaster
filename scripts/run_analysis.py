"""Step 2 of the analysis: turn the predictions into every number the dashboard and README show.

Reads data/processed/predictions_*.csv (from compute_predictions.py) and the LBNL data; writes
web/public/data/results.json. Nothing in the dashboard is typed by hand: it all comes from this file.
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from campus_energy_forecaster.config import DATA_DIR, RESULTS_JSON, Assumptions
from campus_energy_forecaster.data import LOAD_COLUMNS, load_building
from campus_energy_forecaster.evaluation import run_detection_benchmark, score_forecast, seasonal_naive
from campus_energy_forecaster.forecast import calendar_features
from campus_energy_forecaster.outage import Backup, rank_load_sets, runtime_hours, splice_forecast
from campus_energy_forecaster.waste import detect_waste, summarise

A = Assumptions()
PRED = DATA_DIR / "processed"
LABELS = {"hvac": "HVAC", "lighting": "Lighting", "plug": "Plug loads", "total": "Whole building"}
YEARS = {"2019": ("2019-01-01", "2019-12-31 23:00"), "2020": ("2020-01-01", "2020-12-31 23:00")}
BATTERIES_KWH = [100, 250, 500, 1000]
N_EVENTS_SHOWN = 12


def load_pred(target, fs):
    return pd.read_csv(PRED / f"predictions_{target}_{fs}.csv", index_col=0, parse_dates=True)


def r(x, n=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def after_hours_mask(idx):
    """Nights (before 07:00 or from 19:00), weekends and US federal holidays."""
    cal = calendar_features(idx)
    return np.asarray((idx.hour < 7) | (idx.hour >= 19) | (cal["is_weekend"] == 1) | (cal["is_holiday"] == 1))


def forecast_metrics(df):
    out = {}
    for t in ["total", "hvac", "plug", "lighting"]:
        p = load_pred(t, "forecast")
        out[t] = {"label": LABELS[t]}
        for yr, (a, b) in YEARS.items():
            out[t][yr] = score_forecast(df[t].loc[a:b], p.loc[a:b], seasonal_naive(df[t]).loc[a:b])
    return out


def waste_section(df):
    a, b = YEARS["2019"]
    events, bench, per_meter = [], {}, {}
    for t in LOAD_COLUMNS:
        band = load_pred(t, "expected").loc[a:b]
        actual = df[t].loc[a:b]
        ah = pd.Series(after_hours_mask(actual.index), index=actual.index)
        ev = detect_waste(t, actual, band, assumptions=A)
        for e in ev:  # label the likely cause from the calendar
            ix = pd.date_range(e.start, e.end, freq="h")
            e.after_hours = bool(ah.reindex(ix).mean() > 0.5)
        events += ev
        per_meter[t] = summarise(ev, days=len(actual) / 24) | {"label": LABELS[t]}
        bench[t] = run_detection_benchmark(t, actual, band, n_faults=20, seed=7, assumptions=A) | {"label": LABELS[t]}
    # HVAC again on 2020, a second held-out year (plug and lighting are not repeated: the 2020 shutdown broke their baselines)
    a20, b20 = YEARS["2020"]
    bench["hvac_2020"] = run_detection_benchmark("hvac", df["hvac"].loc[a20:b20], load_pred("hvac", "expected").loc[a20:b20],
                                                 n_faults=20, seed=7, assumptions=A) | {"label": "HVAC (2020)"}
    events.sort(key=lambda e: -e.excess_kwh)
    days = len(df.loc[a:b]) / 24
    return {"window": f"{a[:10]} to {b[:10]}", "days": round(days, 1), "summary": summarise(events, days), "per_meter": per_meter,
            "top_events": [e.as_dict() | {"label": LABELS[e.meter]} for e in events[:N_EVENTS_SHOWN]], "all_events": len(events),
            "benchmark": bench}


def after_hours_section(df):
    """Model-free finding: how much of each load is drawn when the building should be quiet."""
    a, b = YEARS["2019"]
    d = df.loc[a:b]
    ah = after_hours_mask(d.index)
    out = {}
    for t in LOAD_COLUMNS + ["total"]:
        s = d[t]
        out[t] = {"label": LABELS[t], "after_hours_share_pct": r(100 * s[ah].sum() / s.sum()),
                  "after_hours_kwh": r(s[ah].sum(), 0), "total_kwh": r(s.sum(), 0)}
    out["share_of_hours_after_hours_pct"] = r(100 * ah.mean())
    # what-if: cut after-hours HVAC and plug load by 10 / 20 / 30 % (arithmetic on the measured loads, not a forecast)
    base = d.loc[ah, ["hvac", "plug"]].sum().sum()
    out["what_if"] = [{"cut_pct": c, "kwh": r(base * c / 100, 0), "cost_usd": r(base * c / 100 * A.tariff_usd_per_kwh, 0),
                       "co2_kg": r(base * c / 100 * A.carbon_kg_per_kwh, 0)} for c in (10, 20, 30)]
    night = d[(d.index.hour < 5) & (d.index.dayofweek < 5)]
    day = d[(d.index.hour >= 10) & (d.index.hour < 16) & (d.index.dayofweek < 5)]
    out["overnight_vs_midday_plug_pct"] = r(100 * night["plug"].mean() / day["plug"].mean())
    return out


def outage_section(df):
    """Backup-battery runtime from the load forecast available at outage start, checked against the load that actually
    occurred. The first 24 hours use the day-ahead forecast; later hours use the baseline model (no recent-usage inputs)."""
    a, b = YEARS["2019"]
    day = {t: load_pred(t, "forecast") for t in LOAD_COLUMNS}
    base = {t: load_pred(t, "expected") for t in LOAD_COLUMNS}
    act = {t: df[t].loc[a:] for t in LOAD_COLUMNS}          # raw readings: a missing hour makes the runtime "n/a"

    def forecast_at(start, col):
        return {t: splice_forecast(day[t][col], base[t][col], start) for t in LOAD_COLUMNS}

    def pick_start(nominal):
        """Nearest day to ``nominal`` (same weekday type) whose day-ahead forecast and next 7 days of meter readings are
        complete, so every runtime shown for it can be checked against what really happened."""
        for off in sorted(range(-30, 31), key=abs):
            t = nominal + pd.Timedelta(days=off)
            if (t.dayofweek < 5) != (nominal.dayofweek < 5):
                continue
            ok_fc = all(day[x]["mid"].loc[t:t + pd.Timedelta(hours=23)].notna().all() for x in LOAD_COLUMNS)
            ok_act = all(act[x].loc[t:t + pd.Timedelta(hours=167)].notna().all() for x in LOAD_COLUMNS)
            if ok_fc and ok_act:
                return t
        raise ValueError(f"no complete window near {nominal}")

    scenarios_def = {
        "winter_weekday_9am": ("Winter weekday, 9 am", pd.Timestamp("2019-01-15 09:00")),
        "summer_weekday_2pm": ("Summer weekday, 2 pm", pd.Timestamp("2019-07-16 14:00")),
        "weekend_night": ("Weekend night, 10 pm", pd.Timestamp("2019-03-09 22:00")),
        "autumn_weekday_6pm": ("Autumn weekday, 6 pm", pd.Timestamp("2019-10-15 18:00")),
    }
    scenarios_def = {k: (lab, pick_start(t)) for k, (lab, t) in scenarios_def.items()}

    def clean(row):
        return {k: (r(v, 2) if isinstance(v, float) else v) for k, v in row.items()}

    scenarios = []
    for key, (label, start) in scenarios_def.items():
        mid, lo, hi = forecast_at(start, "mid"), forecast_at(start, "lo"), forecast_at(start, "hi")
        sc = {"key": key, "label": label, "start": str(start), "batteries": []}
        for cap in BATTERIES_KWH:
            bk = Backup(capacity_kwh=cap)
            rows = rank_load_sets(mid, start, bk, must_keep=("lighting",))
            for row in rows:  # check against actual consumption and add the uncertainty range
                keep = row["keep"]
                row["actual_runtime_h"] = runtime_hours(sum(act[t] for t in keep), start, bk)
                row["runtime_low_h"] = runtime_hours(sum(hi[t] for t in keep), start, bk)    # high load -> short runtime
                row["runtime_high_h"] = runtime_hours(sum(lo[t] for t in keep), start, bk)
            sc["batteries"].append({"capacity_kwh": cap, "options": [clean(x) for x in rows]})
        sc["load_profile"] = [{"hour": i, **{t: r(mid[t].loc[start:].iloc[i], 1) for t in LOAD_COLUMNS}} for i in range(24)]
        scenarios.append(sc)

    # how accurate is the runtime forecast? Every weekday 9 am and Saturday 10 pm of 2019, 250 kWh battery, all loads on.
    # Outages whose real runtime cannot be computed (missing meter readings) are left out and counted.
    bk = Backup(capacity_kwh=250)
    tot_act = sum(act.values())
    starts = [t for t in pd.date_range(a, b, freq="h") if (t.hour == 9 and t.dayofweek < 5) or (t.hour == 22 and t.dayofweek == 5)]
    pairs, skipped = [], 0
    for s0 in starts:
        fc, ac = runtime_hours(sum(forecast_at(s0, "mid").values()), s0, bk), runtime_hours(tot_act, s0, bk)
        if np.isnan(fc) or np.isnan(ac):
            skipped += 1
        else:
            pairs.append((fc, ac))
    e = np.array(pairs)
    acc = {"battery_kwh": 250, "n_starts": int(len(e)), "n_skipped_missing_data": skipped, "mean_actual_runtime_h": r(e[:, 1].mean()),
           "mae_h": r(np.abs(e[:, 0] - e[:, 1]).mean()), "mape_pct": r(100 * np.mean(np.abs(e[:, 0] - e[:, 1]) / e[:, 1])),
           "bias_h": r((e[:, 0] - e[:, 1]).mean())}
    return {"scenarios": scenarios, "accuracy": acc, "batteries_kwh": BATTERIES_KWH, "must_keep": ["lighting"],
            "backup_assumptions": {"usable_fraction": Backup(1).usable_fraction, "efficiency": Backup(1).efficiency}}


def series_section(df):
    """Two weeks of hourly actual vs day-ahead forecast band per end use, for the dashboard chart."""
    a, b = "2019-06-03", "2019-06-16 23:00"
    out = {"window": f"{a} to {b[:10]}", "hours": [str(t) for t in pd.date_range(a, b, freq="h")]}
    for t in LOAD_COLUMNS + ["total"]:
        p = load_pred(t, "forecast").loc[a:b]
        out[t] = {"label": LABELS[t], "actual": [r(v, 2) for v in df[t].loc[a:b]], "lo": [r(v, 2) for v in p["lo"]],
                  "mid": [r(v, 2) for v in p["mid"]], "hi": [r(v, 2) for v in p["hi"]]}
    return out


def overview_section(df):
    a, b = YEARS["2019"]
    d = df.loc[a:b]
    kwh = d[LOAD_COLUMNS].sum()  # hours with a missing reading are skipped, so this is a floor
    return {"annual_kwh": {t: r(kwh[t], 0) for t in LOAD_COLUMNS} | {"total": r(kwh.sum(), 0)},
            "annual_cost_usd": r(kwh.sum() * A.tariff_usd_per_kwh, 0), "annual_co2_t": r(kwh.sum() * A.carbon_kg_per_kwh / 1000, 1),
            "missing_hours_pct": r(100 * d["total"].isna().mean()), "peak_kw": r(d["total"].max()),
            "mean_kw_by_year": {y: {t: r(df.loc[y, t].mean()) for t in LOAD_COLUMNS} for y in ("2018", "2019", "2020")}}


def main():
    df = load_building()
    results = {
        "dataset": {"name": "LBNL Building 59 (Berkeley, CA office building)", "license": "CC0 1.0",
                    "source": "https://zenodo.org/records/5951008", "period": "2018-01 to 2020-12, hourly",
                    "citation": "Luo, N., Wang, Z., Blum, D., et al. (2022). A three-year dataset supporting research on building "
                                "energy, HVAC controls, and occupancy analytics. Scientific Data."},
        "assumptions": {"tariff_usd_per_kwh": A.tariff_usd_per_kwh, "carbon_kg_per_kwh": A.carbon_kg_per_kwh,
                        "tariff_source": "US average commercial price 2025, EIA Electric Power Monthly Table 5.3",
                        "carbon_source": "US average grid CO2 rate, EPA eGRID2023 (767.2 lb/MWh)"},
        "overview": overview_section(df),
        "forecast": forecast_metrics(df),
        "waste": waste_section(df),
        "after_hours": after_hours_section(df),
        "outage": outage_section(df),
        "series": series_section(df),
    }
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(results, indent=1))
    print("wrote", RESULTS_JSON, f"({RESULTS_JSON.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
