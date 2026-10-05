"""Train the final model and write the submission (notebook sections 11-12).

Fits BaggedBlendModel on all labelled rows, saves models/model.pkl and data/processed/predictions.csv
(header id,prediction), then reloads the pickle and checks it reproduces the predictions.

    python scripts/03_train_and_predict.py
"""
import argparse
import pickle
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from campus_energy_forecaster.config import MODEL_PATH, PROCESSED_DATA_DIR, TEST_CSV, TRAIN_CSV
from campus_energy_forecaster.dataset import load_data
from campus_energy_forecaster.evaluation import SEED
from campus_energy_forecaster.modeling.models import BaggedBlendModel

warnings.filterwarnings('ignore')


def main(train_path=TRAIN_CSV, test_path=TEST_CSV, model_path=MODEL_PATH, out_path=PROCESSED_DATA_DIR / 'predictions.csv', n_bags=3):
    np.random.seed(SEED)
    train, test, y = load_data(train_path, test_path)

    model = BaggedBlendModel(n_bags=n_bags).fit(train, y)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    pred = model.predict(test)
    submission = pd.DataFrame({'id': test['id'], 'prediction': pred})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    submission.to_csv(out_path, index=False)
    assert list(submission.columns) == ['id', 'prediction']
    assert len(submission) == len(test) and submission.id.is_unique and submission.prediction.notna().all()
    print(f'saved {model_path} and {out_path} {submission.shape}')
    print(submission.prediction.describe().round(2).to_string())

    # The model takes the raw dataframe and does all feature engineering and imputation itself.
    with open(model_path, 'rb') as f:
        loaded = pickle.load(f)
    diff = np.abs(loaded.predict(pd.read_csv(test_path)) - pred).max()
    print('Reloaded model reproduces the predictions (max abs difference): %.2e' % diff)
    assert diff < 1e-6


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--train', type=Path, default=TRAIN_CSV)
    ap.add_argument('--test', type=Path, default=TEST_CSV)
    ap.add_argument('--model', type=Path, default=MODEL_PATH)
    ap.add_argument('--output', type=Path, default=PROCESSED_DATA_DIR / 'predictions.csv')
    ap.add_argument('--n-bags', type=int, default=3)
    a = ap.parse_args()
    main(a.train, a.test, a.model, a.output, a.n_bags)
