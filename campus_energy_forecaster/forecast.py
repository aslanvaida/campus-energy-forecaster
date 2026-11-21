"""Quantile forecasting of hourly building load, with bands calibrated on held-out data.

Two feature sets share one model class:

``expected``  calendar + weather + occupancy. Answers "what should this load be right now, given conditions?"
              It deliberately has no recent-usage inputs, so a sustained waste event is not absorbed into the baseline.
``forecast``  calendar + weather + usage from 24 h and 168 h ago. Answers "what will this load be tomorrow?"
              Every input is known at midnight the day before (weather is the observed weather, standing in for a
              weather forecast; see the README).
"""
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from sklearn.ensemble import HistGradientBoostingRegressor

QUANTILES = (0.1, 0.5, 0.9)
WEATHER = ["temp", "rh", "solar"]


def calendar_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    hol = USFederalHolidayCalendar().holidays(index.min().normalize(), index.max().normalize())
    hour = index.hour.values
    doy = index.dayofyear.values
    return pd.DataFrame({
        "hour_sin": np.sin(2 * np.pi * hour / 24), "hour_cos": np.cos(2 * np.pi * hour / 24),
        "doy_sin": np.sin(2 * np.pi * doy / 365.25), "doy_cos": np.cos(2 * np.pi * doy / 365.25),
        "dow": index.dayofweek.values,
        "is_weekend": (index.dayofweek.values >= 5).astype(int),
        "is_holiday": index.normalize().isin(hol).astype(int),
    }, index=index)


def build_features(df: pd.DataFrame, target: str, feature_set: str) -> pd.DataFrame:
    """df: hourly frame indexed by timestamp with weather columns, ``occupancy`` and the target column."""
    X = calendar_features(df.index)
    for c in WEATHER:
        if c in df:
            X[c] = df[c]
    if "temp" in df:
        X["temp_24h_mean"] = df["temp"].rolling(24, min_periods=6).mean()
    if feature_set == "expected":
        if "occupancy" in df:
            X["occupancy"] = df["occupancy"]
    elif feature_set == "forecast":
        s = df[target]
        X["lag_24"], X["lag_168"] = s.shift(24), s.shift(168)
        X["same_hour_week_mean"] = pd.concat([s.shift(24 * k) for k in range(1, 8)], axis=1).mean(axis=1)
    else:
        raise ValueError(f"unknown feature_set {feature_set!r}")
    return X


class QuantileForecaster:
    """Gradient-boosted quantile regression (P10 / P50 / P90) with a split-conformal correction of the band.

    The last ``calib_frac`` of the training period is held back to calibrate the band, so the stated coverage is
    measured rather than assumed.
    """

    def __init__(self, target: str, feature_set: str, quantiles=QUANTILES, calib_frac: float = 0.2, seed: int = 0):
        self.target, self.feature_set = target, feature_set
        self.quantiles, self.calib_frac, self.seed = tuple(quantiles), calib_frac, seed

    def _model(self, q):
        return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=200, learning_rate=0.05,
                                             max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0,
                                             random_state=self.seed)

    def fit(self, df: pd.DataFrame):
        X = build_features(df, self.target, self.feature_set)
        y = df[self.target]
        ok = y.notna()
        X, y = X[ok], y[ok]
        cut = int(len(X) * (1 - self.calib_frac))
        Xa, ya, Xb, yb = X.iloc[:cut], y.iloc[:cut], X.iloc[cut:], y.iloc[cut:]
        self.columns_ = list(X.columns)
        self.models_ = {q: self._model(q).fit(Xa, ya) for q in self.quantiles}
        # split-conformal quantile regression: widen (or narrow) the band so ~80% of calibration points fall inside
        lo, hi = (self.models_[min(self.quantiles)].predict(Xb), self.models_[max(self.quantiles)].predict(Xb))
        scores = np.maximum(lo - yb.values, yb.values - hi)
        alpha = 1 - (max(self.quantiles) - min(self.quantiles))
        n = len(scores)
        self.band_offset_ = float(np.quantile(scores, min(1.0, (1 - alpha) * (1 + 1 / n))))
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Columns lo, mid, hi (kW), same index as ``df``. NaN where an input lag is unavailable."""
        X = build_features(df, self.target, self.feature_set)[self.columns_]
        qs = sorted(self.quantiles)
        raw = np.column_stack([self.models_[q].predict(X) for q in qs])
        raw = np.sort(raw, axis=1)                       # quantiles must not cross
        out = pd.DataFrame({"lo": raw[:, 0] - self.band_offset_, "mid": raw[:, len(qs) // 2],
                            "hi": raw[:, -1] + self.band_offset_}, index=df.index)
        out[["lo", "mid", "hi"]] = out[["lo", "mid", "hi"]].clip(lower=0)
        if self.feature_set == "forecast":
            out[X[["lag_24", "lag_168"]].isna().any(axis=1).values] = np.nan
        return out


def walk_forward(df: pd.DataFrame, target: str, feature_set: str, start: str, end: str, train_months: int | None) -> pd.DataFrame:
    """Out-of-sample predictions for every hour in [start, end]: for each calendar month, refit on the data before it
    (the trailing ``train_months`` months, or everything if None) and predict that month. This mimics a deployed tool
    that is refreshed monthly, and it lets the model follow level shifts in a building's operation."""
    parts = []
    for m in pd.date_range(start, end, freq="MS"):
        m_end = m + pd.DateOffset(months=1) - pd.Timedelta(hours=1)
        lo = None if train_months is None else m - pd.DateOffset(months=train_months)
        train = df.loc[lo:m - pd.Timedelta(hours=1)]
        model = QuantileForecaster(target, feature_set).fit(train)
        context = df.loc[m - pd.Timedelta(days=8):m_end]          # earlier hours feed the lag features
        parts.append(model.predict(context).loc[m:m_end])
    return pd.concat(parts)
