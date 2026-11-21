import numpy as np
import pandas as pd
import pytest

from campus_energy_forecaster.peak import daily_peaks, peak_forecast_accuracy, peak_shift_estimate, shift_flexible_load


def _profile(days=10, base=10.0, peak=50.0, peak_hour=15):
    idx = pd.date_range("2023-06-01", periods=24 * days, freq="h")
    s = pd.Series(base, index=idx)
    s[idx.hour == peak_hour] = peak
    return s


def test_daily_peaks_value_hour_and_incomplete_days():
    s = _profile(3)
    s.iloc[24:24 + 10] = np.nan                          # day 2 has only 14 readings
    p = daily_peaks(s)
    assert list(p["kw"].iloc[[0, 2]]) == [50.0, 50.0] and list(p["hour"].iloc[[0, 2]]) == [15, 15]
    assert p["kw"].iloc[1] != p["kw"].iloc[1]            # NaN


def test_peak_forecast_accuracy_perfect_and_biased():
    a = _profile(10)
    a[a.index.normalize() == pd.Timestamp("2023-06-04")] += 30        # one clearly highest-peak day
    res = peak_forecast_accuracy(a, a)
    assert res["mae_kw"] == 0 and res["peak_hour_within_2h_pct"] == 100 and res["top_days_caught_pct"] == 100
    assert peak_forecast_accuracy(a, a - 5)["mae_kw"] == pytest.approx(5.0)


def test_shift_conserves_energy_and_lowers_the_peak():
    total = _profile(4)
    flex = total * 0.8
    mask = pd.Series(total.index.hour == 15, index=total.index)
    out = shift_flexible_load(total, flex, mask, share=0.5)
    assert out.sum() == pytest.approx(total.sum())
    assert out.max() < total.max()
    assert out[total.index.hour == 15].iloc[1] == pytest.approx(50 - 0.5 * 40)
    assert out[total.index.hour == 3].iloc[1] == pytest.approx(10 + 20 / 23)        # the 20 kWh is spread over the 23 other hours


def test_peak_shift_estimate_acts_only_on_flagged_days_and_scores_on_actuals():
    total = _profile(20)
    total[total.index.normalize() >= pd.Timestamp("2023-06-19")] += 20     # last 2 days (top 10%) are the peak days
    res = peak_shift_estimate(total, total * 0.8, total, share=0.5)
    assert res["days_acted_on"] == 2 and res["energy_conserved"]
    assert res["mean_peak_reduction_kw"] == pytest.approx(0.5 * 0.8 * 70)         # window is the single peak hour; filled hours stay below it
    assert res["annual_peak_after_kw"] < res["annual_peak_before_kw"]
