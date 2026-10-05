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
├── Makefile           <- `make requirements`, `make train`, `make predict`
├── README.md
├── data
│   ├── external       <- Data from third party sources (ASHRAE, LBNL Building 59)
│   ├── interim        <- Intermediate transformed data
│   ├── processed      <- Final data sets / predictions
│   └── raw            <- Original datathon CSVs (not committed)
├── docs
├── models             <- Trained models (model.pkl, not committed)
├── notebooks
│   └── Track1_Smart_Campus_Analytics_bagged-2.ipynb
├── pyproject.toml
├── references         <- Data dictionaries, manuals, explanatory material
├── reports
│   └── figures
├── requirements.txt
└── campus_energy_forecaster
    ├── __init__.py
    ├── config.py      <- Paths
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

Put `Track 1 Training Dataset.csv` and `Track 1 Testing Dataset.csv` in `data/raw/`, then:

```bash
make train     # -> models/model.pkl
make predict   # -> data/processed/predictions.csv
```

The pickled model needs the same `scikit-learn` / `xgboost` versions it was trained with (pinned in `requirements.txt`).

--------

<p><small>Project based on the <a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">cookiecutter data science project template</a>.</small></p>
