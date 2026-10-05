"""External validation of the model recipe on public building-energy data (notebook sections 13-14).

The same BlendModel recipe (no changes) is retrained on each dataset converted to the datathon columns, with a
time-based split, and compared with the naive rule "usage = previous reading".

  ashrae  ASHRAE Great Energy Predictor III, site 0, the 12 largest electricity meters (no occupancy data).
          Downloaded with kagglehub (pip install kagglehub). Trains on the first 80% of time, tests on the rest.
  lbnl    LBNL Building 59 (Luo et al. 2022, Scientific Data), with real occupant counts. Each electricity meter is
          treated as one "building". Downloads a 263 MB archive to data/external/. Trains on 2018, tests on 2019.

    python scripts/04_external_validation.py ashrae
    python scripts/04_external_validation.py lbnl
"""
import argparse
import glob
import sys
import urllib.request
import warnings
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from campus_energy_forecaster.config import EXTERNAL_DATA_DIR
from campus_energy_forecaster.evaluation import SEED, r2, rmse
from campus_energy_forecaster.modeling.models import NUMC, BlendModel

warnings.filterwarnings('ignore')
N_TRAIN = 8000   # same training size as the datathon, for a fair comparison
LBNL_URL = 'https://zenodo.org/records/5951008/files/Building_59.zip?download=1'


def report(name, yt, p):
    print(f'{name:22s} RMSE {rmse(yt, p):9.3f} | MAE {np.mean(np.abs(yt - p)):9.3f} | R2 {r2(yt, p):.4f}')
    return rmse(yt, p)


def evaluate(tr, te):
    tr, te = tr.drop(columns='timestamp'), te.drop(columns='timestamp')
    print('train rows', len(tr), '| test rows', len(te), '| buildings', tr.building_id.nunique())
    yt = te.energy_usage.values
    naive = report('Naive (= previous)', yt, te.previous_usage.values)
    p = BlendModel().fit(tr, tr.energy_usage.values).predict(te)
    ours = report('Our blend', yt, p)
    print(f'Improvement over naive: {100 * (1 - ours / naive):.1f}%  (datathon: about 54%)')
    ape = np.abs(yt - p) / yt
    print(f'Median % error: {100 * np.median(ape):.1f}% | within 10%: {100 * (ape <= 0.10).mean():.1f}% | within 20%: {100 * (ape <= 0.20).mean():.1f}%')


# ----------------------------------------------------------------------------- ASHRAE

def ashrae(n_buildings=12, site=0):
    import kagglehub
    path = kagglehub.dataset_download('shishu1421/ashrae-great-energy-predictor-iii-featherdataset')

    def load(name):
        f = glob.glob(f'{path}/**/{name}.*', recursive=True)[0]
        df = pd.read_feather(f) if f.endswith('.feather') else pd.read_csv(f)
        if 'timestamp' in df:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    meta, weather, raw = load('building_metadata'), load('weather_train'), load('train')
    raw['meter_reading'] = raw['meter_reading'].astype('float64')

    bids = meta[meta.site_id == site].building_id.tolist()       # one site = one weather station
    r = raw[(raw.meter == 0) & raw.building_id.isin(bids) & (raw.meter_reading > 0)]   # electricity only
    del raw
    r = r[r.building_id.isin(r.groupby('building_id').meter_reading.mean().nlargest(n_buildings).index)]
    d = (r.merge(meta[['building_id', 'site_id', 'primary_use']], on='building_id')
          .merge(weather, on=['site_id', 'timestamp'], how='left')
          .sort_values(['building_id', 'timestamp']))

    T, Td = d.air_temperature, d.dew_temperature
    ext = pd.DataFrame({
        'id': ['K' + str(i) for i in range(len(d))],
        'building_id': 'B' + d.building_id.astype(str).values,
        'building_type': d.primary_use.values,
        'hour': d.timestamp.dt.hour.values,
        'day_of_week': d.timestamp.dt.day_name().values,
        'month': d.timestamp.dt.month.values,
        'temperature': T.values,
        'humidity': (100 * np.exp(17.625 * Td / (243.04 + Td)) / np.exp(17.625 * T / (243.04 + T))).clip(0, 100).values,
        'occupancy': 0.0,                                                   # ASHRAE has no occupancy
        'previous_usage': d.groupby('building_id').meter_reading.shift(1).values,
        'energy_usage': d.meter_reading.values,
        'timestamp': d.timestamp.values,
    }).dropna(subset=['previous_usage']).reset_index(drop=True)

    cut = ext.timestamp.quantile(0.8)
    tr = ext[ext.timestamp <= cut].sample(n=min(N_TRAIN, (ext.timestamp <= cut).sum()), random_state=SEED)
    te = ext[ext.timestamp > cut]
    return tr, te


# ----------------------------------------------------------------------------- LBNL Building 59

def read_hourly(data_dir, name):
    f = glob.glob(f'{data_dir}/**/{name}', recursive=True)[0]
    df = pd.read_csv(f)
    tcol = next(c for c in df.columns
                if any(k in c.lower() for k in ('date', 'time')) and pd.to_datetime(df[c].head(50), errors='coerce').notna().all())
    df.index = pd.to_datetime(df.pop(tcol), errors='coerce', utc=True).dt.tz_localize(None)
    df = df[df.index.notna()].apply(pd.to_numeric, errors='coerce')
    return df.resample('h').mean()


def lbnl(data_dir=EXTERNAL_DATA_DIR / 'lbnl', train_years=(2018,), test_years=(2019,)):
    if not glob.glob(f'{data_dir}/**/ele.csv', recursive=True):
        data_dir.mkdir(parents=True, exist_ok=True)
        archive = data_dir / 'Building_59.zip'
        print(f'downloading {LBNL_URL} (263 MB) ...', flush=True)
        urllib.request.urlretrieve(LBNL_URL, archive)
        zipfile.ZipFile(archive).extractall(data_dir)

    ele = read_hourly(data_dir, 'ele.csv')                               # electricity meters
    occ = read_hourly(data_dir, 'occ.csv').sum(axis=1, min_count=1).rename('occupancy')   # occupant counts
    wx = read_hourly(data_dir, 'site_weather.csv')                       # outdoor weather station
    weather = pd.DataFrame({'temperature': wx['air_temp_set_1'], 'humidity': wx['relative_humidity_set_1']}, index=wx.index)

    parts = []
    for c in [c for c in ele.columns if ele[c].notna().mean() > 0.5]:
        s = ele[c].rename('energy_usage').to_frame()
        s['building_id'] = c
        s['building_type'] = c.split('_')[0]          # hvac, lig (lighting), mels (plug loads)
        s['previous_usage'] = s['energy_usage'].shift(1)
        parts.append(s)
    d = pd.concat(parts).join(occ).join(weather).rename_axis('timestamp').reset_index()

    ext = pd.DataFrame({
        'id': ['L' + str(i) for i in range(len(d))],
        'building_id': d.building_id, 'building_type': d.building_type,
        'hour': d.timestamp.dt.hour, 'day_of_week': d.timestamp.dt.day_name(), 'month': d.timestamp.dt.month,
        'temperature': d.temperature, 'humidity': d.humidity, 'occupancy': d.occupancy,
        'previous_usage': d.previous_usage, 'energy_usage': d.energy_usage, 'timestamp': d.timestamp,
    }).dropna(subset=['energy_usage', 'previous_usage']).reset_index(drop=True)
    print('units ("buildings"):', ext.building_id.nunique(), '| date range:', ext.timestamp.min(), '->', ext.timestamp.max(), '| rows:', len(ext))
    print('missing share:', ext[NUMC].isna().mean().round(3).to_dict())

    # Time series, so split by whole years: a random split would leak the neighbouring hours into training.
    yr = ext.timestamp.dt.year
    pool, te = ext[yr.isin(train_years)], ext[yr.isin(test_years)]
    tr = pool.sample(n=min(N_TRAIN, len(pool)), random_state=SEED)
    assert tr.timestamp.max() < te.timestamp.min(), 'train and test overlap in time'
    assert not set(tr.id) & set(te.id), 'shared rows'
    return tr, te


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dataset', choices=['ashrae', 'lbnl'])
    a = ap.parse_args()
    np.random.seed(SEED)
    evaluate(*(ashrae() if a.dataset == 'ashrae' else lbnl()))
