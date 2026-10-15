import numpy as np
import pytest

from campus_energy_forecaster.dataset import load_data


def test_load_data_returns_frames_and_target(tmp_path, frame):
    tr, te = tmp_path / "train.csv", tmp_path / "test.csv"
    frame.to_csv(tr, index=False)
    frame.drop(columns="energy_usage").to_csv(te, index=False)
    train, test, y = load_data(tr, te)
    assert len(train) == len(test) == len(frame)
    np.testing.assert_allclose(y, frame.energy_usage.values)


def test_load_data_names_the_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        load_data(tmp_path / "nope.csv", tmp_path / "nope2.csv")
