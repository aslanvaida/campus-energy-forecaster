"""Load the datathon CSVs."""
from pathlib import Path

import pandas as pd

from campus_energy_forecaster.config import TEST_CSV, TRAIN_CSV


def load_data(train_path=TRAIN_CSV, test_path=TEST_CSV):
    """Return (train, test, y) where y is the training target as a numpy array."""
    for p in (train_path, test_path):
        if not Path(p).exists():
            raise FileNotFoundError(f"{p} not found. Put the datathon CSVs in data/raw/ or pass --train / --test.")
    train, test = pd.read_csv(train_path), pd.read_csv(test_path)
    return train, test, train["energy_usage"].values
