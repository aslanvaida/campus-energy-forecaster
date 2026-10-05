# Campus Energy Forecaster

Predicting the energy usage of campus buildings from their usage history, weather, occupancy and building information.
Built for **NTU Datathon 2026 (Deep Learning Week), Track 1: Smart Campus Analytics**.

The final model is a bagged blend of a ridge model with per-building / per-building-type structure and several XGBoost
pipelines, trained with synthetic missing-value augmentation so it holds up on the gap-heavy test set.
The full analysis (EDA, missing-value study, feature engineering, model comparison, error analysis and external
validation on ASHRAE and LBNL Building 59) is in the notebook.

## Project Organization

```
├── LICENSE
├── Makefile           <- `make requirements`, `make pipeline`, `make train`, `make predict`
├── README.md
├── data
│   ├── external       <- Data from third party sources (ASHRAE, LBNL Building 59)
│   ├── interim        <- Intermediate transformed data
│   ├── processed      <- Final data sets / predictions
│   └── raw            <- Original datathon CSVs (not committed)
├── docs
├── models             <- Trained models (model.pkl, not committed)
├── notebooks
│   └── Track1_Smart_Campus_Analytics_bagged-2.ipynb   <- Original exploratory notebook (reference only)
├── pyproject.toml
├── references         <- Data dictionaries, manuals, explanatory material
├── reports
│   └── figures
├── requirements.txt
├── scripts            <- The notebook as reproducible Python scripts, run in order
│   ├── 01_eda.py                   <- EDA, missing-value study, train/test differences
│   ├── 02_evaluate.py              <- CV model comparison, learning curve, error analysis, assumption checks
│   ├── 03_train_and_predict.py     <- Fit final model, save model.pkl + predictions.csv, reload check
│   └── 04_external_validation.py   <- Same recipe on ASHRAE / LBNL Building 59
└── campus_energy_forecaster
    ├── __init__.py
    ├── config.py      <- Paths
    ├── dataset.py     <- Load the datathon CSVs
    ├── evaluation.py  <- Metrics, test-like gap injection, cross-validation, baselines
    └── modeling
        ├── models.py  <- Feature engineering, imputation and model classes
        ├── train.py   <- Fit BaggedBlendModel and save models/model.pkl
        └── predict.py <- Score a CSV and write id,prediction
```

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
make requirements
```

Put `Track 1 Training Dataset.csv` and `Track 1 Testing Dataset.csv` in `data/raw/`, then run the scripts in order
(or `make pipeline` for steps 1-3):

```bash
python scripts/01_eda.py                # stats to stdout, figures -> reports/figures/
python scripts/02_evaluate.py           # -> reports/model_comparison.csv (several minutes)
python scripts/03_train_and_predict.py  # -> models/model.pkl, data/processed/predictions.csv
```

Each script takes `--train` / `--test` paths (see `--help`). The external validation is optional and downloads data:

```bash
pip install kagglehub
python scripts/04_external_validation.py ashrae
python scripts/04_external_validation.py lbnl
```

To score any CSV with the same columns as the test file using a saved model:

```bash
python -m campus_energy_forecaster.modeling.predict --input path/to/file.csv --output predictions.csv
```

On macOS, XGBoost needs the OpenMP runtime (`brew install libomp`).

The pickled model needs the same `scikit-learn` / `xgboost` versions it was trained with (pinned in `requirements.txt`).

--------

<p><small>Project based on the <a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">cookiecutter data science project template</a>.</small></p>
