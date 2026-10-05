"""Exploratory data analysis (notebook sections 3-5).

Prints summary statistics, the missing-value study and the train/test differences, and saves figures to reports/figures/.

    python scripts/01_eda.py
"""
import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold, cross_val_predict, cross_val_score

from campus_energy_forecaster.config import FIGURES_DIR, TEST_CSV, TRAIN_CSV
from campus_energy_forecaster.dataset import load_data
from campus_energy_forecaster.evaluation import SEED, r2, rmse
from campus_energy_forecaster.modeling.models import NUMC

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid')


def section(title):
    print(f'\n{"=" * 80}\n{title}\n{"=" * 80}')


def overview(train, y, fig_dir):
    section('3. Exploratory data analysis')
    print(train.dtypes.to_string(), '\n')
    print(train.describe().T.round(2).to_string())

    fig, ax = plt.subplots(1, 3, figsize=(17, 4))
    sns.histplot(train.energy_usage, kde=True, ax=ax[0]); ax[0].set_title('Energy usage')
    order = train.groupby('building_id').energy_usage.mean().sort_values().index
    sns.boxplot(data=train, x='building_id', y='energy_usage', order=order, ax=ax[1]); ax[1].tick_params(axis='x', rotation=60); ax[1].set_title('Usage by building')
    sns.lineplot(data=train, x='hour', y='energy_usage', hue='building_type', errorbar=None, ax=ax[2]); ax[2].set_title('Daily profile by building type'); ax[2].legend(fontsize=7)
    plt.tight_layout(); fig.savefig(fig_dir / 'eda_usage.png', dpi=120); plt.close(fig)

    fig, ax = plt.subplots(1, 3, figsize=(17, 4))
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    sns.barplot(data=train, x='day_of_week', y='energy_usage', order=days, errorbar=None, ax=ax[0]); ax[0].tick_params(axis='x', rotation=45); ax[0].set_title('Usage by weekday')
    sns.scatterplot(data=train, x='previous_usage', y='energy_usage', hue='building_type', s=8, alpha=.5, ax=ax[1], legend=False); ax[1].set_title('Usage vs previous usage')
    sns.heatmap(train.select_dtypes('number').corr(), annot=True, fmt='.2f', cmap='coolwarm', cbar=False, ax=ax[2]); ax[2].set_title('Correlations')
    plt.tight_layout(); fig.savefig(fig_dir / 'eda_drivers.png', dpi=120); plt.close(fig)

    naive = train.previous_usage.fillna(train.previous_usage.median()).values
    print('\nNaive rule "usage = previous_usage": RMSE %.2f, R2 %.3f' % (rmse(y, naive), r2(y, naive)))
    print('Mean usage by building:', train.groupby('building_id').energy_usage.mean().round(0).astype(int).to_dict())


def gap_table(d, name):
    k = d[NUMC].isna().sum(axis=1).value_counts().reindex(range(5), fill_value=0)
    p = d[NUMC].isna().mean().mean()
    expected = stats.binom.pmf(range(5), 4, p) * len(d)
    return pd.DataFrame({f'{name} observed': k.values, f'{name} if gaps were independent': expected.round(0)},
                        index=[f'{i} gaps' for i in range(5)])


def missing_values(train, test):
    section('4. Missing values: the biggest difference between train and test')
    rates = pd.DataFrame({'train': train[NUMC].isna().mean(), 'test': test[NUMC].isna().mean()}).round(4)
    print('Share of values missing per column\n' + rates.to_string())
    print('Share of rows with at least one gap: train %.1f%%, test %.1f%%'
          % (100 * train[NUMC].isna().any(axis=1).mean(), 100 * test[NUMC].isna().any(axis=1).mean()))
    print('\n' + pd.concat([gap_table(train, 'train'), gap_table(test, 'test')], axis=1).to_string())

    # Does the chance of a gap depend on the values in the row? AUC near 0.5 means no.
    out = {}
    for c in NUMC:
        others = [o for o in NUMC if o != c]
        d = test[test[others].notna().all(axis=1)]
        X = d.drop(columns=['id', c]).copy()
        for col in X.select_dtypes(exclude='number'):
            X[col] = X[col].astype('category').cat.codes
        t = d[c].isna().astype(int)
        p = cross_val_predict(HistGradientBoostingClassifier(max_iter=100, learning_rate=0.05, max_depth=3, random_state=0), X, t,
                              cv=KFold(5, shuffle=True, random_state=0), method='predict_proba')[:, 1]
        out[c] = round(roc_auc_score(t, p), 3)
    print('\nAUC of predicting "is missing" from the other columns (test rows):', out)

    complete = ~train[NUMC].isna().any(axis=1)
    print('\n4.1 Cleaning step')
    print('training rows:', len(train), '| with a missing numeric value:', int((~complete).sum()), '| complete:', int(complete.sum()))
    print('Validation and test rows are never dropped, so every row still gets a prediction.')


def train_test_shift(train, test):
    section('5. Other differences between train and test')
    prof = train.groupby(['building_id', 'hour']).energy_usage.mean().rename('profile')

    def dev(d):
        return d.join(prof, on=['building_id', 'hour']).eval('previous_usage - profile')

    dtr, dte = dev(train), dev(test)
    print('Share of rows where previous_usage is more than 20 above that building and hour typical usage: train %.1f%%, test %.1f%%'
          % (100 * (dtr > 20).mean(), 100 * (dte > 20).mean()))
    sel = ['LectureHall', 'Library', 'Sports']
    for name, d, dv in (('train', train, dtr), ('test', test, dte)):
        m = d.building_type.isin(sel) & d.hour.isin([22, 23])
        print(f'  hours 22-23 in lecture hall / library / sports, {name}: {100 * (dv[m] > 20).mean():.0f}% of rows have a previous_usage spike')

    feat = ['hour', 'month', 'temperature', 'humidity', 'occupancy', 'previous_usage']
    adv = pd.concat([train[feat].assign(t=0), test[feat].assign(t=1)])
    auc = cross_val_score(HistGradientBoostingClassifier(max_iter=100, random_state=SEED), adv[feat], adv.t,
                          cv=KFold(5, shuffle=True, random_state=SEED), scoring='roc_auc').mean()
    print('Train vs test classifier AUC (0.5 = identical): %.2f' % auc)


def main(train_path=TRAIN_CSV, test_path=TEST_CSV, fig_dir=FIGURES_DIR):
    np.random.seed(SEED)
    fig_dir.mkdir(parents=True, exist_ok=True)
    train, test, y = load_data(train_path, test_path)
    print('train', train.shape, '| test', test.shape)
    overview(train, y, fig_dir)
    missing_values(train, test)
    train_test_shift(train, test)
    print(f'\nfigures saved to {fig_dir}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--train', type=Path, default=TRAIN_CSV)
    ap.add_argument('--test', type=Path, default=TEST_CSV)
    ap.add_argument('--figures', type=Path, default=FIGURES_DIR)
    a = ap.parse_args()
    main(a.train, a.test, a.figures)
