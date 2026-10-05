"""Validation helpers: metrics, test-like gap injection, K-fold CV and the baseline models."""
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from campus_energy_forecaster.modeling.models import CAT, FE, NUMC, _xgb

SEED = 42


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def r2(y, p):
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))


def gap_pattern(test):
    """Share of test rows with 0..4 missing numeric values."""
    return test[NUMC].isna().sum(axis=1).value_counts(normalize=True).reindex(range(5), fill_value=0).values


def add_testlike_gaps(df, k_dist, seed):
    """Blank out values so the number of gaps per row follows the test set's pattern (columns chosen at random)."""
    d = df.copy(); r = np.random.RandomState(seed)
    k = r.choice(5, size=len(d), p=k_dist)
    mask = r.rand(len(d), 4).argsort(axis=1).argsort(axis=1) < k[:, None]
    for j, c in enumerate(NUMC):
        d.loc[mask[:, j], c] = np.nan
    return d


def cross_validate(make, name, train, y, k_dist):
    """5-fold shuffled CV. Scores each fold as is (complete rows) and with test-like gaps added."""
    clean, gaps = np.zeros(len(train)), np.zeros(len(train))
    for a, b in KFold(5, shuffle=True, random_state=SEED).split(train):
        m = make().fit(train.iloc[a], y[a]); v = train.iloc[b]
        clean[b] = m.predict(v); gaps[b] = m.predict(add_testlike_gaps(v, k_dist, 11))
    row = {'model': name, 'RMSE (complete rows)': rmse(y, clean), 'MAE (complete rows)': float(np.mean(np.abs(y - clean))),
           'R2 (complete rows)': r2(y, clean), 'RMSE (test-like gaps)': rmse(y, gaps)}
    return row, clean, gaps


class Naive(BaseEstimator):
    """usage = previous usage (median-filled when missing)."""
    def fit(self, df, y):
        self.med_ = df.previous_usage.median(); return self

    def predict(self, df):
        return df.previous_usage.fillna(self.med_).values


def global_model(kind):
    """One Ridge or XGBoost model for all buildings, median imputation, no tuning."""
    num = Pipeline([('i', SimpleImputer(strategy='median', keep_empty_features=True))] + ([('s', StandardScaler())] if kind == 'ridge' else []))
    est = RidgeCV(alphas=np.logspace(-2, 3, 20)) if kind == 'ridge' else _xgb(n_estimators=400, learning_rate=0.03, max_depth=4)
    return Pipeline([('fe', FE()), ('pre', ColumnTransformer([('c', OneHotEncoder(handle_unknown='ignore'), CAT),
                                                              ('n', num, make_column_selector(dtype_include='number'))])), ('m', est)])
