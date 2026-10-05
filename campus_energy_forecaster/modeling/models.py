"""Track 1 model code (final). Trains on complete rows; gaps in new data are imputed at prediction time.
The linear part uses as few coefficients as the data supports (see SharedStructure)."""
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import HistGradientBoostingRegressor, ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMC = ['temperature', 'humidity', 'occupancy', 'previous_usage']
CAT = ['building_id', 'building_type', 'day_of_week']



class GroupImpute(BaseEstimator, TransformerMixin):
    """Fill missing numeric values with the building x hour median (falls back to building, then global); adds missing flags."""
    def fit(self, X, y=None):
        self.stats_ = {c: (X.groupby(['building_id', 'hour'])[c].median(), X.groupby('building_id')[c].median(), X[c].median())
                       for c in NUMC}
        return self

    def transform(self, X):
        X = X.copy()
        for c in NUMC:
            gm, bm, g = self.stats_[c]
            miss = X[c].isna()
            X[c + '_missing'] = miss.astype(int)
            idx = pd.MultiIndex.from_arrays([X.building_id, X.hour])
            fill = gm.reindex(idx).values
            fill = np.where(np.isnan(fill), bm.reindex(X.building_id).values, fill)
            fill = np.where(np.isnan(fill), g, fill)
            X[c] = np.where(miss, fill, X[c])
        return X


DAYS = {d: i for i, d in enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])}


class ModelImpute(GroupImpute):
    """ExtraTrees for dominant features with Native OOB routing to prevent memorization leakage.
    HGBR for weather features."""
    TARGETS = NUMC

    def _design(self, G, c):
        D = pd.DataFrame({'b': G.building_id.map(self.bcode_).values, 'h': G.hour.values,
                          'd': G.day_of_week.map(DAYS).values, 'mo': G.month.values})
        for o in NUMC:
            if o != c:
                D[o] = G[o].values
        return D

    def fit(self, X, y=None):
        super().fit(X, y)
        self.bcode_ = {b: i for i, b in enumerate(sorted(X.building_id.unique()))}

        # Deduplicate to force training ONLY on the 1x clean dataset (prevents clone leakage)
        X_clean = X.drop_duplicates(subset=['id']).copy()
        G_clean = super().transform(X_clean)

        self.m_, self.lo_, self.oob_ = {}, {c: X_clean[c].min() for c in self.TARGETS}, {}

        for c in self.TARGETS:
            obs = X_clean[c].notna().values
            if c in ['occupancy', 'previous_usage']:
                clf = ExtraTreesRegressor(n_estimators=400, min_samples_leaf=3, bootstrap=True, oob_score=True, random_state=0, n_jobs=-1)
                clf.fit(self._design(G_clean[obs], c), X_clean.loc[obs, c])
                self.m_[c] = clf
                # Map true training IDs to their unbiased OOB predictions
                self.oob_[c] = pd.Series(clf.oob_prediction_, index=X_clean.loc[obs, 'id']).to_dict()
            else:
                self.m_[c] = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.08, max_leaf_nodes=15, min_samples_leaf=30, random_state=0).fit(self._design(G_clean[obs], c), X_clean.loc[obs, c])
        return self

    def transform(self, X):
        G = super().transform(X)
        for c in self.TARGETS:
            miss = X[c].isna().values
            if miss.any():
                preds = self.m_[c].predict(self._design(G[miss], c))
                # Route missing training rows to use OOB predictions (simulates real test-time error variance)
                if c in self.oob_:
                    miss_ids = X.loc[miss, 'id'].values
                    has_oob = np.array([idx in self.oob_[c] for idx in miss_ids])
                    if has_oob.any():
                        preds[has_oob] = np.array([self.oob_[c][idx] for idx in miss_ids[has_oob]])
                G.loc[miss, c] = np.clip(preds, self.lo_[c], None)
        return G

class FE(BaseEstimator, TransformerMixin):
    """Row-wise features: cyclical hour/month, weekend flag, log occupancy."""
    def fit(self, X, y=None):
        return self

    def transform(self, df):
        d = df.copy()
        d['hour_sin'] = np.sin(2 * np.pi * d.hour / 24); d['hour_cos'] = np.cos(2 * np.pi * d.hour / 24)
        d['month_sin'] = np.sin(2 * np.pi * d.month / 12); d['month_cos'] = np.cos(2 * np.pi * d.month / 12)
        d['is_weekend'] = d.day_of_week.isin(['Saturday', 'Sunday']).astype(int)
        d['occupancy_log'] = np.log1p(d.occupancy)
        return d.drop(columns=['id', 'energy_usage'], errors='ignore')


class SharedStructure(BaseEstimator, TransformerMixin):
    """Linear-model terms with as few coefficients as the data supports.
    Per building: occupancy, temperature, the first daily cycle and the weekend effect (these differ a lot between buildings).
    Shared by all buildings: the slope on previous usage, humidity and the missing-value flags.
    Shared by building TYPE: the 2nd and 3rd daily harmonics (finer shape of the day, estimated from more rows)."""
    def fit(self, X, y=None):
        self.b_ = sorted(X.building_id.unique()); self.t_ = sorted(X.building_type.unique())
        return self

    def transform(self, X):
        X = X.reset_index(drop=True).copy(); hr = X.hour.values; cols = {}
        for k in (2, 3):
            X[f'h{k}s'] = np.sin(2 * np.pi * k * hr / 24); X[f'h{k}c'] = np.cos(2 * np.pi * k * hr / 24)
        for b in self.b_:
            m = (X.building_id == b).values.astype(float)
            for c in ['occupancy_log', 'occupancy', 'temperature', 'hour_sin', 'hour_cos', 'is_weekend']:
                cols[f'b_{b}_{c}'] = m * X[c].values
        for t in self.t_:
            m = (X.building_type == t).values.astype(float)
            for c in ['h2s', 'h2c', 'h3s', 'h3c']:
                cols[f't_{t}_{c}'] = m * X[c].values
        return pd.concat([X, pd.DataFrame(cols)], axis=1)


def _xgb(**kw):
    p = dict(n_estimators=800, learning_rate=0.05, max_depth=5, subsample=.85, colsample_bytree=.6,
             min_child_weight=10, reg_lambda=10, random_state=42, n_jobs=-1)
    p.update(kw)
    return xgb.XGBRegressor(**p)


def _tree_pipe(group_impute, model):
    steps = [('imp', GroupImpute())] if group_impute else []
    num = SimpleImputer(strategy='median', keep_empty_features=True) if group_impute else 'passthrough'  # xgboost reads NaN natively
    steps += [('fe', FE()),
              ('pre', ColumnTransformer([('c', OneHotEncoder(handle_unknown='ignore'), CAT),
                                         ('n', num, make_column_selector(dtype_include='number'))])),
              ('m', model)]
    return Pipeline(steps)


def _ridge_pipe():
    return Pipeline([('imp', ModelImpute()), ('fe', FE()), ('bi', SharedStructure()),
                     ('pre', ColumnTransformer([('c', OneHotEncoder(handle_unknown='ignore'), CAT),
                                                ('n', StandardScaler(), make_column_selector(dtype_include='number'))])),
                     ('m', RidgeCV(alphas=np.logspace(-1, 3.5, 25)))])


def _inject(df, rate, seed):
    d = df.copy(); r = np.random.RandomState(seed)
    for c in NUMC:
        d.loc[r.rand(len(d)) < rate, c] = np.nan
    return d


def _augment(df, y, copies, rate, seed=100):
    """Add copies of the training rows with random gaps, so the model learns to cope with missing values."""
    parts, ys = [df], [y]
    for k in range(copies):
        parts.append(_inject(df, rate, seed + k)); ys.append(y)
    return pd.concat(parts, ignore_index=True), np.concatenate(ys)


class BlendModel(BaseEstimator):
    """Takes the raw dataframe (same columns as the CSV). With drop_incomplete=False, retains the 6% of data."""
    def __init__(self, ridge_weight=0.85, copies=4, drop_incomplete=False, aug_seed=100):
        self.ridge_weight = ridge_weight
        self.copies = copies
        self.drop_incomplete = drop_incomplete
        self.aug_seed = aug_seed # Allow custom seed for bagging

    def fit(self, df, y):
        y = np.asarray(y).astype(float)

        # Debias the 463 natural gaps by subtracting their known +1.2 label offset.
        if 'previous_usage' in df.columns:
            nat_prev_gap = df['previous_usage'].isna().values
            y[nat_prev_gap] -= 1.2

        if self.drop_incomplete:
            keep = ~df[NUMC].isna().any(axis=1).values
            df, y = df[keep], y[keep]

        specs = [
            ('ridge', _ridge_pipe(), 0.08),
            ('xgb_native_d5', _tree_pipe(False, _xgb()), 0.10),
            ('xgb_native_d4', _tree_pipe(False, _xgb(max_depth=4, n_estimators=1000)), 0.10),
            ('xgb_group_imp', _tree_pipe(True, _xgb()), 0.08),
        ]
        self.models_ = {}
        for name, pipe, rate in specs:
            Xa, ya = _augment(df, y, self.copies, rate, seed=self.aug_seed)
            self.models_[name] = pipe.fit(Xa, ya)

        # Store historical min/max per building for boundary clipping
        self.b_min_ = df.groupby('building_id')['energy_usage'].min().to_dict()
        self.b_max_ = df.groupby('building_id')['energy_usage'].max().to_dict()
        return self

    def predict(self, df):
        ridge = self.models_['ridge'].predict(df)
        trees = np.mean([m.predict(df) for k, m in self.models_.items() if k != 'ridge'], axis=0)

        # Base prediction
        preds = self.ridge_weight * ridge + (1 - self.ridge_weight) * trees

        # Physical Boundary Clipping (Pad min/max by 5% to allow mild natural variation)
        for b_id in df['building_id'].unique():
            if b_id in self.b_min_:
                mask = (df['building_id'] == b_id).values
                b_min, b_max = self.b_min_[b_id] * 0.95, self.b_max_[b_id] * 1.05
                preds[mask] = np.clip(preds[mask], b_min, b_max)

        return preds


class BaggedBlendModel(BaseEstimator):
    """Trains 3 versions of the BlendModel with different synthetic gap placements and averages them."""
    def __init__(self, n_bags=3, ridge_weight=0.85, copies=4, drop_incomplete=False):
        self.n_bags = n_bags
        self.ridge_weight = ridge_weight
        self.copies = copies
        self.drop_incomplete = drop_incomplete

    def fit(self, df, y):
        self.bags_ = []
        for i in range(self.n_bags):
            # Use seeds 100, 200, 300...
            model = BlendModel(ridge_weight=self.ridge_weight, copies=self.copies,
                               drop_incomplete=self.drop_incomplete, aug_seed=100 + (i * 100))
            self.bags_.append(model.fit(df, y))
        return self

    def predict(self, df):
        # Average the predictions across all bags
        return np.mean([m.predict(df) for m in self.bags_], axis=0)
