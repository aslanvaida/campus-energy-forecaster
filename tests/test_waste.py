import pandas as pd

from campus_energy_forecaster.config import Assumptions
from campus_energy_forecaster.evaluation import inject_faults, run_detection_benchmark
from campus_energy_forecaster.forecast import QuantileForecaster
from campus_energy_forecaster.waste import detect_waste, summarise


def _band(idx, mid=10.0, width=2.0):
    return pd.DataFrame({"lo": mid - width, "mid": mid, "hi": mid + width}, index=idx)


def test_detects_sustained_excess_and_prices_it():
    idx = pd.date_range("2023-01-01", periods=96, freq="h")
    actual = pd.Series(10.0, index=idx)
    actual.iloc[30:40] = 16.0                       # 10 hours, +6 kW over expected, +4 kW over the band
    ev = detect_waste("hvac", actual, _band(idx), margin=0, assumptions=Assumptions(tariff_usd_per_kwh=0.5, carbon_kg_per_kwh=0.4))
    assert len(ev) == 1
    e = ev[0]
    assert e.hours == 10 and e.excess_kwh == 60.0 and e.excess_kwh_floor == 40.0
    assert e.cost_usd == 30.0 and e.co2_kg == 24.0


def test_ignores_short_spikes_and_bridges_single_hour_gaps():
    idx = pd.date_range("2023-01-01", periods=96, freq="h")
    a = pd.Series(10.0, index=idx)
    a.iloc[10:12] = 20.0                            # 2 h spike: below min_hours
    a.iloc[50:54] = 20.0; a.iloc[55:58] = 20.0      # one normal hour inside one fault
    ev = detect_waste("hvac", a, _band(idx), margin=0)
    assert len(ev) == 1 and ev[0].start.endswith("02:00:00") and ev[0].hours == 8


def test_after_hours_label_uses_occupancy():
    idx = pd.date_range("2023-01-01", periods=96, freq="h")
    a = pd.Series(10.0, index=idx); a.iloc[30:36] = 20.0
    occ = pd.Series(50.0, index=idx); occ.iloc[30:36] = 0.0
    assert detect_waste("hvac", a, _band(idx), occ, margin=0)[0].after_hours is True
    assert detect_waste("hvac", a, _band(idx), pd.Series(50.0, index=idx), margin=0)[0].after_hours is False


def test_margin_raises_the_alert_threshold():
    idx = pd.date_range("2023-01-01", periods=96, freq="h")
    a = pd.Series(10.0, index=idx); a.iloc[30:40] = 13.0          # 1 kW above the P90 band (hi = 12)
    assert len(detect_waste("hvac", a, _band(idx), margin=0)) == 1
    assert detect_waste("hvac", a, _band(idx), margin=1.0) == []   # threshold is 14 kW


def test_summarise_annualises():
    idx = pd.date_range("2023-01-01", periods=96, freq="h")
    a = pd.Series(10.0, index=idx); a.iloc[30:40] = 16.0
    s = summarise(detect_waste("hvac", a, _band(idx), margin=0), days=4)
    assert s["events"] == 1 and s["excess_kwh"] == 60.0 and s["annualised_excess_kwh"] == round(60 * 365 / 4)


def test_injected_faults_are_non_overlapping_and_found(hourly):
    faulty, inj = inject_faults(hourly["hvac"], 5, seed=1)
    assert len(inj) == 5
    assert ((faulty - hourly["hvac"]) > 0).sum() == inj["hours"].sum()
    train, test = hourly.iloc[:24 * 70], hourly.iloc[24 * 70:]
    band = QuantileForecaster("hvac", "expected").fit(train).predict(test)
    res = run_detection_benchmark("hvac", test["hvac"], band, n_faults=4, seed=2)
    big = res["by_size"][-1]
    assert big["injected_faults"] == 4 and big["recall_pct"] >= 75
