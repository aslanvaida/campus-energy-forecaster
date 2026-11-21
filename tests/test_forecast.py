import pandas as pd
import numpy as np
import pytest

from campus_energy_forecaster.evaluation import cv_rmse, mae, nmbe, score_forecast, seasonal_naive
from campus_energy_forecaster.forecast import QuantileForecaster, build_features


def test_expected_features_have_no_usage_inputs(hourly):
    cols = build_features(hourly, "hvac", "expected").columns
    assert not any(c.startswith("lag") or "same_hour" in c for c in cols)
    assert "occupancy" in cols


def test_forecast_features_use_only_lags_of_a_day_or_more(hourly):
    X = build_features(hourly, "hvac", "forecast")
    assert (X["lag_24"].iloc[24:].values == hourly["hvac"].iloc[:-24].values).all()
    assert X["lag_168"].iloc[:168].isna().all()
    with pytest.raises(ValueError):
        build_features(hourly, "hvac", "bogus")


def test_forecaster_beats_naive_and_band_is_ordered(hourly):
    train, test = hourly.iloc[:24 * 90], hourly.iloc[24 * 90:]
    m = QuantileForecaster("hvac", "expected").fit(train)
    p = m.predict(test)
    assert (p["lo"] <= p["mid"]).all() and (p["mid"] <= p["hi"]).all()
    s = score_forecast(test["hvac"], p, seasonal_naive(hourly["hvac"]).loc[test.index])
    assert s["mae_kw"] < s["naive_mae_kw"]
    assert 60 < s["band_coverage_pct"] <= 100


def test_day_ahead_forecast_has_nan_without_history(hourly):
    m = QuantileForecaster("hvac", "forecast").fit(hourly.iloc[:24 * 90])
    p = m.predict(hourly)
    assert p.iloc[:168].isna().all().all() and p.iloc[200:].notna().all().all()


def test_metrics():
    y = np.array([10.0, 20.0, 30.0])
    assert mae(y, y + 2) == pytest.approx(2.0)
    assert cv_rmse(y, y + 2) == pytest.approx(10.0)
    assert nmbe(y, y - 2) == pytest.approx(100 * 2 / 20)


def test_walk_forward_never_sees_the_month_it_predicts(hourly):
    from campus_energy_forecaster.forecast import walk_forward
    spiked = hourly.copy()
    spiked.loc["2022-04-01":"2022-04-30", "hvac"] += 500          # a huge change confined to the month being predicted
    p = walk_forward(spiked, "hvac", "expected", "2022-04-01", "2022-04-01", train_months=None)
    assert p.index.min() == pd.Timestamp("2022-04-01") and len(p) == 30 * 24
    assert p["hi"].max() < 100                                     # a model that saw April would predict ~500+
