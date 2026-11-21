import pandas as pd
import pytest

from campus_energy_forecaster.outage import Backup, rank_load_sets, runtime_hours


def test_runtime_constant_load():
    idx = pd.date_range("2023-01-01", periods=100, freq="h")
    b = Backup(capacity_kwh=100, usable_fraction=1.0, efficiency=1.0)
    assert runtime_hours(pd.Series(10.0, index=idx), idx[0], b) == pytest.approx(10.0)


def test_runtime_follows_hourly_profile_and_losses():
    idx = pd.date_range("2023-01-01", periods=48, freq="h")
    load = pd.Series([20.0] * 5 + [5.0] * 43, index=idx)
    b = Backup(capacity_kwh=200, usable_fraction=0.5, efficiency=1.0)      # 100 kWh usable
    assert runtime_hours(load, idx[0], b) == pytest.approx(5 + (100 - 100) / 5)   # exactly 5 h at 20 kW
    b2 = Backup(capacity_kwh=125, usable_fraction=1.0, efficiency=1.0)
    assert runtime_hours(load, idx[0], b2) == pytest.approx(5 + 25 / 5)
    assert Backup(100, 0.9, 0.9).usable_kwh == pytest.approx(81.0)


def test_inverter_limit_cuts_runtime():
    idx = pd.date_range("2023-01-01", periods=10, freq="h")
    load = pd.Series([5.0] * 3 + [50.0] * 7, index=idx)
    assert runtime_hours(load, idx[0], Backup(1000, 1, 1, max_power_kw=20)) == 3.0


def test_ranking_prefers_shedding_big_loads_and_respects_must_keep():
    idx = pd.date_range("2023-01-01", periods=200, freq="h")
    loads = {"hvac": pd.Series(30.0, index=idx), "lighting": pd.Series(5.0, index=idx), "plug": pd.Series(15.0, index=idx)}
    b = Backup(capacity_kwh=100, usable_fraction=1.0, efficiency=1.0)
    rows = rank_load_sets(loads, idx[0], b, must_keep=("lighting",))
    assert rows[0]["keep"] == ["lighting"] and rows[0]["runtime_h"] == 20.0
    assert all("lighting" in r["keep"] for r in rows) and len(rows) == 4
    assert rows[-1]["keep"] == ["hvac", "lighting", "plug"] and rows[-1]["runtime_h"] == 2.0


def test_missing_load_makes_runtime_unknown_not_infinite():
    idx = pd.date_range("2023-01-01", periods=10, freq="h")
    load = pd.Series([10.0, 10.0, float("nan")] + [10.0] * 7, index=idx)
    b = Backup(capacity_kwh=100, usable_fraction=1.0, efficiency=1.0)
    assert runtime_hours(load, idx[0], b) != runtime_hours(load, idx[0], b)          # NaN
    small = Backup(capacity_kwh=15, usable_fraction=1.0, efficiency=1.0)               # runs out before the gap
    assert runtime_hours(load, idx[0], small) == pytest.approx(1.5)


def test_splice_uses_day_ahead_only_for_the_first_24_hours():
    from campus_energy_forecaster.outage import splice_forecast
    idx = pd.date_range("2023-01-01", periods=72, freq="h")
    day_ahead, baseline = pd.Series(1.0, index=idx), pd.Series(2.0, index=idx)
    out = splice_forecast(day_ahead, baseline, idx[10])
    assert (out.loc[idx[10]:idx[33]] == 1.0).all() and (out.loc[idx[34]:] == 2.0).all() and (out.loc[:idx[9]] == 2.0).all()
