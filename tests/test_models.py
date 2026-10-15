import numpy as np
import pytest

from campus_energy_forecaster.modeling.models import (
    FE, NUMC, BaggedBlendModel, BlendModel, GroupImpute, SharedStructure, _augment, _inject,
)


def test_fe_adds_features_and_drops_id_and_target(frame):
    out = FE().fit(frame).transform(frame)
    assert "id" not in out and "energy_usage" not in out
    for c in ["hour_sin", "hour_cos", "month_sin", "month_cos", "is_weekend", "occupancy_log"]:
        assert c in out
    assert out.hour_sin.between(-1, 1).all()


def test_fe_flags_weekends_only(frame):
    out = FE().fit(frame).transform(frame)
    assert (out.is_weekend == frame.day_of_week.isin(["Saturday", "Sunday"]).astype(int)).all()


def test_group_impute_removes_all_gaps_and_adds_flags(frame_with_gaps):
    out = GroupImpute().fit(frame_with_gaps).transform(frame_with_gaps)
    assert not out[NUMC].isna().any().any()
    for c in NUMC:
        assert (out[c + "_missing"] == frame_with_gaps[c].isna().astype(int)).all()


def test_group_impute_keeps_observed_values(frame_with_gaps):
    out = GroupImpute().fit(frame_with_gaps).transform(frame_with_gaps)
    seen = frame_with_gaps.temperature.notna()
    np.testing.assert_allclose(out.temperature[seen], frame_with_gaps.temperature[seen])


def test_group_impute_falls_back_for_unseen_building(frame_with_gaps):
    imp = GroupImpute().fit(frame_with_gaps)
    new = frame_with_gaps.head(5).copy()
    new["building_id"] = "UNSEEN"
    new["temperature"] = np.nan
    out = imp.transform(new)
    assert out.temperature.notna().all()
    assert out.temperature.iloc[0] == pytest.approx(frame_with_gaps.temperature.median())


def test_shared_structure_builds_per_building_and_per_type_columns(frame):
    d = FE().fit(frame).transform(frame)
    out = SharedStructure().fit(d).transform(d)
    assert "b_B1_occupancy" in out and "t_lab_h2s" in out
    only_b1 = out.loc[(d.building_id != "B1").values, "b_B1_occupancy"]
    assert (only_b1 == 0).all()


def test_inject_blanks_roughly_the_requested_share(frame):
    out = _inject(frame, 0.2, seed=0)
    share = out[NUMC].isna().to_numpy().mean()
    assert 0.1 < share < 0.3
    assert not frame[NUMC].isna().any().any()


def test_augment_stacks_copies_and_repeats_targets(frame):
    y = frame.energy_usage.values
    df, ya = _augment(frame, y, copies=2, rate=0.1)
    assert len(df) == 3 * len(frame)
    assert len(ya) == 3 * len(y)
    np.testing.assert_array_equal(ya[: len(y)], ya[len(y): 2 * len(y)])


@pytest.fixture(scope="module")
def fitted_blend():
    from conftest import make_frame
    df = make_frame()
    return df, BlendModel(copies=1).fit(df, df.energy_usage.values)


def test_blend_predicts_one_finite_value_per_row(fitted_blend):
    df, m = fitted_blend
    pred = m.predict(df)
    assert pred.shape == (len(df),)
    assert np.isfinite(pred).all()


def test_blend_handles_missing_values_at_predict_time(fitted_blend, frame_with_gaps):
    _, m = fitted_blend
    pred = m.predict(frame_with_gaps)
    assert np.isfinite(pred).all()


def test_blend_clips_to_padded_per_building_range(fitted_blend):
    df, m = fitted_blend
    pred = m.predict(df)
    for b, g in df.groupby("building_id"):
        p = pred[(df.building_id == b).values]
        assert p.min() >= g.energy_usage.min() * 0.95 - 1e-9
        assert p.max() <= g.energy_usage.max() * 1.05 + 1e-9


def test_blend_beats_predicting_the_mean(fitted_blend):
    df, m = fitted_blend
    y = df.energy_usage.values
    model_err = np.sqrt(np.mean((m.predict(df) - y) ** 2))
    mean_err = np.sqrt(np.mean((y.mean() - y) ** 2))
    assert model_err < mean_err


def test_bagged_blend_reports_progress_and_averages_bags():
    from conftest import make_frame
    df = make_frame(n=240)
    calls = []
    m = BaggedBlendModel(n_bags=2, copies=1).fit(df, df.energy_usage.values, on_bag=lambda i, n: calls.append((i, n)))
    assert calls == [(0, 2), (1, 2)]
    expected = np.mean([b.predict(df) for b in m.bags_], axis=0)
    np.testing.assert_allclose(m.predict(df), expected)
