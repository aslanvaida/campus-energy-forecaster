"""HTTP API used by the web app: train the final model on an uploaded train split and score it on the test split.

Training takes tens of seconds, so it runs as a background job that the page polls:

    POST /jobs        multipart form with `train` and `test` CSV files  -> {"job_id": ...}
    GET  /jobs/{id}   -> {"status": queued|running|done|error, "stage", "progress", "result" | "error"}

Run with:  uvicorn campus_energy_forecaster.api:app --port 8000
"""
import io
import threading
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile

from campus_energy_forecaster.evaluation import r2, rmse
from campus_energy_forecaster.modeling.models import NUMC, BaggedBlendModel

warnings.filterwarnings('ignore')

REQUIRED = ['id', 'building_id', 'building_type', 'hour', 'day_of_week', 'month', 'temperature', 'humidity',
            'occupancy', 'previous_usage', 'energy_usage']
NUMERIC = ['hour', 'month', *NUMC, 'energy_usage']
MIN_TRAIN, MIN_TEST = 100, 20
N_BAGS = 3
MAX_POINTS = 2000  # scatter points sent to the page
JOB_TTL = 3600     # seconds a finished job's results are kept in memory

app = FastAPI(title='Campus Energy Forecaster API')
_jobs: dict[str, dict] = {}
_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=1)  # one training job at a time; later jobs wait in the queue


def _update(job_id, **fields):
    with _lock:
        _jobs[job_id].update(fields)


def _read(upload: UploadFile, name: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(upload.file.read()), dtype={'id': str})
    except Exception as e:  # noqa: BLE001 - surface any parse failure to the user
        raise HTTPException(400, f'Could not read the {name} file: {e}')
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise HTTPException(400, f'The {name} file is missing columns: {", ".join(missing)}')
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def _run(job_id: str, train: pd.DataFrame, test: pd.DataFrame):
    start = time.time()
    try:
        _update(job_id, status='running', stage='Preparing data', progress=0.03)
        y = train['energy_usage'].values

        def on_bag(i, n):
            _update(job_id, stage=f'Training model (bag {i + 1} of {n})', progress=0.05 + 0.8 * i / n)

        model = BaggedBlendModel(n_bags=N_BAGS).fit(train, y, on_bag=on_bag)

        _update(job_id, stage='Predicting the test set', progress=0.88)
        pred = model.predict(test)
        actual = test['energy_usage'].values
        naive = test['previous_usage'].fillna(train['previous_usage'].median()).values

        _update(job_id, stage='Scoring', progress=0.96)
        res = actual - pred
        by_building = (pd.DataFrame({'building_id': test['building_id'].values, 'building_type': test['building_type'].values,
                                     'se': res ** 2, 'ae': np.abs(res)})
                       .groupby(['building_id', 'building_type'])
                       .agg(n=('se', 'size'), mse=('se', 'mean'), mae=('ae', 'mean')).reset_index())
        by_building['rmse'] = np.sqrt(by_building.pop('mse'))
        gaps = test[NUMC].isna().any(axis=1).values

        sample = np.arange(len(test))
        if len(sample) > MAX_POINTS:
            sample = np.sort(np.random.RandomState(0).choice(sample, MAX_POINTS, replace=False))

        result = {
            'n_train': int(len(train)), 'n_test': int(len(test)), 'seconds': round(time.time() - start, 1), 'n_bags': N_BAGS,
            'metrics': {'rmse': rmse(actual, pred), 'mae': float(np.mean(np.abs(res))), 'r2': r2(actual, pred)},
            'naive': {'rmse': rmse(actual, naive), 'mae': float(np.mean(np.abs(actual - naive))), 'r2': r2(actual, naive)},
            'gaps': {'rows_with_gap': int(gaps.sum()),
                     'rmse_with_gap': rmse(actual[gaps], pred[gaps]) if gaps.any() else None,
                     'rmse_complete': rmse(actual[~gaps], pred[~gaps]) if (~gaps).any() else None},
            'by_building': by_building.sort_values('rmse').round(4).to_dict(orient='records'),
            'points': {'actual': actual[sample].round(3).tolist(), 'predicted': pred[sample].round(3).tolist(),
                       'building_id': test['building_id'].values[sample].tolist()},
            'predictions': {'id': test['id'].tolist(), 'actual': actual.round(4).tolist(), 'predicted': pred.round(4).tolist()},
        }
        _update(job_id, status='done', stage='Done', progress=1.0, result=result)
    except Exception as e:  # noqa: BLE001 - report the failure to the page instead of a silent dead job
        _update(job_id, status='error', stage='Failed', error=f'{type(e).__name__}: {e}')


@app.post('/jobs')
def create_job(train: UploadFile = File(...), test: UploadFile = File(...)):
    tr, te = _read(train, 'training'), _read(test, 'test')

    dropped = {'train': int(tr['energy_usage'].isna().sum()), 'test': int(te['energy_usage'].isna().sum())}
    tr, te = tr[tr['energy_usage'].notna()].reset_index(drop=True), te[te['energy_usage'].notna()].reset_index(drop=True)
    if len(tr) < MIN_TRAIN or len(te) < MIN_TEST:
        raise HTTPException(400, f'Need at least {MIN_TRAIN} labelled training rows and {MIN_TEST} labelled test rows '
                                 f'(got {len(tr)} and {len(te)}).')
    shared = set(tr['id']) & set(te['id'])
    if shared:
        raise HTTPException(400, f'Train and test share {len(shared)} ids; the split must not overlap.')

    job_id = uuid.uuid4().hex
    with _lock:
        for old in [k for k, j in _jobs.items() if time.time() - j['created'] > JOB_TTL]:
            del _jobs[old]
        _jobs[job_id] = {'status': 'queued', 'stage': 'Waiting for the previous job', 'progress': 0.0,
                         'dropped_unlabelled': dropped, 'created': time.time()}
    _executor.submit(_run, job_id, tr, te)
    return {'job_id': job_id}


@app.get('/jobs/{job_id}')
def get_job(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(404, 'Unknown job')
        return {k: v for k, v in job.items() if k != 'created'}


@app.get('/health')
def health():
    return {'ok': True}
