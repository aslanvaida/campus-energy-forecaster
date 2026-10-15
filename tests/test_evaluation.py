import numpy as np
import pandas as pd
import pytest

from campus_energy_forecaster.evaluation import Naive, add_testlike_gaps, gap_pattern, r2, rmse
from campus_energy_forecaster.modeling.models import NUMC


def test_rmse_known_value():
    assert rmse([1, 2, 3], [1, 2, 5]) == pytest.approx(np.sqrt(4 / 3))


def test_rmse_zero_for_identical_inputs():
    assert rmse([4, 5, 6], [4, 5, 6]) == 0.0


def test_r2_perfect_and_mean_baseline():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r2(y, y) == pytest.approx(1.0)
    assert r2(y, np.full(4, y.mean())) == pytest.approx(0.0)


def test_gap_pattern_sums_to_one_and_has_five_bins(frame_with_gaps):
    p = gap_pattern(frame_with_gaps)
    assert len(p) == 5
    assert p.sum() == pytest.approx(1.0)


def test_gap_pattern_counts_missing_values_per_row():
    df = pd.DataFrame({c: [1.0, 1.0, 1.0, 1.0] for c in NUMC})
    df.loc[0, NUMC[0]] = np.nan
    df.loc[1, NUMC[:2]] = np.nan
    assert list(gap_pattern(df)) == [0.5, 0.25, 0.25, 0.0, 0.0]


def test_add_testlike_gaps_does_not_modify_input(frame):
    before = frame.copy()
    add_testlike_gaps(frame, np.array([0.0, 1.0, 0, 0, 0]), seed=1)
    pd.testing.assert_frame_equal(frame, before)


def test_add_testlike_gaps_hits_requested_gap_count_per_row(frame):
    out = add_testlike_gaps(frame, np.array([0.0, 0.0, 1.0, 0.0, 0.0]), seed=1)
    assert (out[NUMC].isna().sum(axis=1) == 2).all()


def test_add_testlike_gaps_is_deterministic_per_seed(frame):
    k = np.array([0.2, 0.3, 0.2, 0.2, 0.1])
    a = add_testlike_gaps(frame, k, seed=3)
    b = add_testlike_gaps(frame, k, seed=3)
    pd.testing.assert_frame_equal(a, b)


def test_naive_fills_missing_previous_usage_with_training_median(frame):
    m = Naive().fit(frame, frame.energy_usage.values)
    test = frame.head(3).copy()
    test.loc[test.index[0], "previous_usage"] = np.nan
    pred = m.predict(test)
    assert pred[0] == pytest.approx(frame.previous_usage.median())
    assert pred[1] == pytest.approx(test.previous_usage.iloc[1])
