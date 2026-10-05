"""Fit the final bagged blend model on the training CSV and save it to models/model.pkl."""
import argparse
import pickle

import pandas as pd

from campus_energy_forecaster.config import MODEL_PATH, TRAIN_CSV
from campus_energy_forecaster.modeling.models import BaggedBlendModel


def main(train_path=TRAIN_CSV, model_path=MODEL_PATH, n_bags=3):
    train = pd.read_csv(train_path)
    model = BaggedBlendModel(n_bags=n_bags).fit(train, train["energy_usage"].values)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"saved {model_path}")


if __name__ == "__main__":
    from pathlib import Path

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", type=Path, default=TRAIN_CSV)
    ap.add_argument("--model", type=Path, default=MODEL_PATH)
    ap.add_argument("--n-bags", type=int, default=3)
    a = ap.parse_args()
    main(a.train, a.model, a.n_bags)
