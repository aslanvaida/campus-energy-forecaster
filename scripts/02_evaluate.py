"""Model comparison and evaluation (notebook sections 8-10b).

5-fold CV of the baselines and the final model (complete rows and test-like gaps), the learning curve of the
linear part, error analysis, permutation importance and the Ridge assumption checks. Writes
reports/model_comparison.csv and figures to reports/figures/. Takes several minutes.

    python scripts/02_evaluate.py
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
from sklearn.model_selection import KFold

from campus_energy_forecaster.config import FIGURES_DIR, REPORTS_DIR, TEST_CSV, TRAIN_CSV
from campus_energy_forecaster.dataset import load_data
from campus_energy_forecaster.evaluation import SEED, Naive, cross_validate, gap_pattern, global_model, rmse
from campus_energy_forecaster.modeling.models import NUMC, BaggedBlendModel, BlendModel, _augment, _ridge_pipe

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid')
FINAL = 'Final blend (linear model + XGBoost)'


def section(title):
    print(f'\n{"=" * 80}\n{title}\n{"=" * 80}')


def compare_models(train, test, y):
    section('9. Model comparison (5-fold CV)')
    k_dist = gap_pattern(test)
    rows, oof = [], {}
    for name, make in [('Naive: previous usage', Naive), ('Ridge (global)', lambda: global_model('ridge')),
                       ('XGBoost (global)', lambda: global_model('xgb')), (FINAL, BaggedBlendModel)]:
        print('  cross-validating', name, '...', flush=True)
        r, c, g = cross_validate(make, name, train, y, k_dist); rows.append(r); oof[name] = (c, g)
    results = pd.DataFrame(rows).set_index('model').round(3)
    print('\n' + results.to_string())
    return results, oof


def learning_curve(train, y):
    section('9.1 Learning curve of the linear part (complete rows)')
    complete = ~train[NUMC].isna().any(axis=1)
    sizes = [1000, 2000, 4000, 6000]
    mse_n = {n: [] for n in sizes}
    rng = np.random.RandomState(SEED)
    for a, b in KFold(5, shuffle=True, random_state=SEED).split(train):
        a = a[complete.values[a]]; b = b[complete.values[b]]
        for n in sizes:
            sub = rng.choice(a, size=min(n, len(a)), replace=False)
            Xa, ya = _augment(train.iloc[sub], y[sub], 4, 0.08)
            m = _ridge_pipe().fit(Xa, ya)
            mse_n[n].append(np.mean((y[b] - m.predict(train.iloc[b])) ** 2))
    n_arr = np.array(sizes, float); v = np.array([np.mean(mse_n[k]) for k in sizes])
    (noise, c_est), *_ = np.linalg.lstsq(np.vstack([np.ones_like(n_arr), 1.0 / n_arr]).T, v, rcond=None)
    n_full = int(complete.sum())
    print('training rows -> validation RMSE:', {k: round(float(np.sqrt(x)), 3) for k, x in zip(sizes, v)})
    print('fitted noise floor (RMSE with unlimited data): %.3f' % np.sqrt(noise))
    print('expected RMSE with all %d complete training rows: %.3f' % (n_full, np.sqrt(noise + c_est / n_full)))
    print('so at most %.3f of RMSE is lost to estimating coefficients' % (np.sqrt(noise + c_est / n_full) - np.sqrt(noise)))


def error_analysis(train, y, c, fig_dir):
    section('10. Error analysis of the final model (out-of-fold)')
    res = y - c
    fig, ax = plt.subplots(1, 3, figsize=(17, 4))
    ax[0].scatter(c, y, s=5, alpha=.35); lim = [y.min(), y.max()]; ax[0].plot(lim, lim, 'r--'); ax[0].set_xlabel('predicted'); ax[0].set_ylabel('actual'); ax[0].set_title('Predicted vs actual (out-of-fold)')
    ax[1].scatter(c, res, s=5, alpha=.35); ax[1].axhline(0, color='r'); ax[1].set_xlabel('predicted'); ax[1].set_ylabel('residual'); ax[1].set_title('Residuals')
    sns.histplot(res, kde=True, ax=ax[2]); ax[2].set_title('Residual distribution (skew %.2f)' % stats.skew(res))
    plt.tight_layout(); fig.savefig(fig_dir / 'error_analysis.png', dpi=120); plt.close(fig)

    print('RMSE by building:')
    print(pd.Series(res ** 2).groupby(train.building_id.values).mean().pow(.5).round(2).sort_values().to_frame('RMSE').T.to_string())
    pattern = np.where(train.previous_usage.isna() & train.occupancy.isna(), 'previous + occupancy',
                       np.where(train.previous_usage.isna(), 'previous_usage',
                                np.where(train.occupancy.isna(), 'occupancy',
                                         np.where(train[NUMC].isna().any(axis=1), 'temperature / humidity', 'no gap'))))
    print('\nRMSE by which values were already missing in the original training rows:')
    print(pd.Series(res ** 2).groupby(pattern).agg(['mean', 'count']).assign(RMSE=lambda d: d['mean'] ** .5)[['count', 'RMSE']].round(2).T.to_string())
    return res


def permutation_importance(train, fig_dir):
    print('\nPermutation importance (BlendModel fit on all training rows, scored on a 2000 row sample)')
    model = BlendModel().fit(train, train['energy_usage'].values)
    samp = train.sample(2000, random_state=SEED); ys = samp.energy_usage.values
    base = rmse(ys, model.predict(samp)); rng = np.random.RandomState(SEED); imp = {}
    for col in ['previous_usage', 'building_id', 'building_type', 'occupancy', 'temperature', 'humidity', 'hour', 'day_of_week', 'month']:
        d = []
        for _ in range(2):
            s2 = samp.copy(); s2[col] = rng.permutation(s2[col].values); d.append(rmse(ys, model.predict(s2)) - base)
        imp[col] = np.mean(d)
    imp = pd.Series(imp).sort_values()
    print(imp.round(3).to_string())
    fig = plt.figure(figsize=(7, 4))
    imp.plot.barh(color='darkorange'); plt.xlabel('increase in RMSE when the column is shuffled'); plt.title('Permutation importance')
    plt.tight_layout(); fig.savefig(fig_dir / 'permutation_importance.png', dpi=120); plt.close(fig)
    return model


def assumption_checks(train, test, y, c, res, model, fig_dir):
    section('10b. Ridge assumption checks (out-of-fold residuals)')
    r = pd.Series(res)
    fig, ax = plt.subplots(1, 3, figsize=(17, 4))
    # (1) linearity: mean residual should stay near 0 across the range of each main input
    worst = {}
    for col in ['previous_usage', 'occupancy', 'temperature']:
        bins = pd.qcut(train[col], 10, duplicates='drop')
        m = r.groupby(bins.values, observed=True).mean()
        worst[col] = float(m.abs().max())
        ax[0].plot(range(len(m)), m.values, marker='o', label=col)
    ax[0].axhline(0, color='k', lw=1); ax[0].set_title('(1) Linearity: mean residual by input decile'); ax[0].set_xlabel('decile of the input'); ax[0].legend()
    # (2) constant variance: residual spread across the range of predictions
    sd = r.groupby(pd.qcut(pd.Series(c), 8).values, observed=True).std()
    ax[1].bar(range(len(sd)), sd.values, color='steelblue'); ax[1].set_title('(2) Residual std by predicted-usage octile'); ax[1].set_xlabel('low usage ... high usage')
    # (3) normality
    stats.probplot(res, dist='norm', plot=ax[2]); ax[2].set_title('(3) Normal Q-Q plot of residuals')
    plt.tight_layout(); fig.savefig(fig_dir / 'assumption_checks.png', dpi=120); plt.close(fig)

    print('(1) Linearity: largest mean residual in any input decile (usage units):', {k: round(v, 2) for k, v in worst.items()})
    print('(2) Residual std in the lowest predicted-usage octile %.2f vs %.2f in the highest.' % (sd.iloc[0], sd.iloc[-1]))
    print('(3) Residual skew %.2f, excess kurtosis %.2f.' % (stats.skew(res), stats.kurtosis(res)))
    ids = train['id'].str[2:].astype(int)
    rs = res[ids.argsort().values]
    print('(4) Independence: lag-1 correlation of residuals in id order = %.3f, correlation of residual with id = %.3f.'
          % (np.corrcoef(rs[:-1], rs[1:])[0, 1], np.corrcoef(ids, res)[0, 1]))
    outside = {col: round(float(((test[col] < train[col].min()) | (test[col] > train[col].max())).mean()), 4)
               for col in ['hour', 'month', 'temperature', 'humidity', 'occupancy', 'previous_usage']}
    tp = model.predict(test)
    print('(5) Share of test values outside the training range:', outside,
          '| predicted test usage range %.1f to %.1f vs training targets %.1f to %.1f' % (tp.min(), tp.max(), y.min(), y.max()))


def main(train_path=TRAIN_CSV, test_path=TEST_CSV, reports_dir=REPORTS_DIR, fig_dir=FIGURES_DIR, skip_learning_curve=False):
    np.random.seed(SEED)
    fig_dir.mkdir(parents=True, exist_ok=True); reports_dir.mkdir(parents=True, exist_ok=True)
    train, test, y = load_data(train_path, test_path)
    print('train', train.shape, '| test', test.shape)

    results, oof = compare_models(train, test, y)
    results.to_csv(reports_dir / 'model_comparison.csv')
    if not skip_learning_curve:
        learning_curve(train, y)
    c, _ = oof[FINAL]
    res = error_analysis(train, y, c, fig_dir)
    model = permutation_importance(train, fig_dir)
    assumption_checks(train, test, y, c, res, model, fig_dir)
    print(f'\nresults saved to {reports_dir / "model_comparison.csv"}, figures to {fig_dir}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--train', type=Path, default=TRAIN_CSV)
    ap.add_argument('--test', type=Path, default=TEST_CSV)
    ap.add_argument('--reports', type=Path, default=REPORTS_DIR)
    ap.add_argument('--figures', type=Path, default=FIGURES_DIR)
    ap.add_argument('--skip-learning-curve', action='store_true', help='skip section 9.1 (saves about a minute)')
    a = ap.parse_args()
    main(a.train, a.test, a.reports, a.figures, a.skip_learning_curve)
