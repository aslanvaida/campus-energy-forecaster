# Campus Energy Forecaster

A building energy forecasting and efficiency tool. From hourly meter data it forecasts each load a day ahead with an
uncertainty band, flags hours where a load runs above what conditions explain (and prices the waste in energy, money and
CO2), and plans for a grid outage: how long a backup battery lasts and which loads to keep running to make it last longest.

It targets the Sustainable Energy theme, mainly **usage and efficiency**, with **emergency power** as the second feature.

## What it does

1. **Waste alerts.** A quantile model learns what each load (HVAC, lighting, plug loads) normally does for the weather,
   hour and day of week. Hours above its alert threshold for 3 hours or more become events, each with the extra energy,
   cost and CO2.
2. **Quiet-hours report.** A model-free view of how much of each load is drawn at night, at weekends and on holidays, with
   a what-if for cutting it.
3. **Next-day forecast with uncertainty.** P10 / P50 / P90 per load, with the band calibrated on held-out data so the
   coverage is measured, not assumed.
4. **Emergency power planner.** Given a battery size and an outage start, runtime for every combination of loads kept on,
   with the range implied by the forecast band, checked against the load the building actually drew.
5. **Dashboard** (`web/`) for a facilities manager: alerts, savings, the planner and a page on how far to trust each
   number. It is a static page; nothing is trained in the browser.

## Results

<!-- RESULTS:START -->
Demo building: LBNL Building 59 (Berkeley, CA office building), 2018-01 to 2020-12, hourly. All figures are for 2019, where each month is predicted by a model fitted only on earlier months, unless stated. Regenerate with `make analysis` then `python scripts/render_readme.py`.

**What the building uses**

- Electricity (HVAC, lighting, plug loads): 401 MWh, about $53,807 and 140 t CO2 at the assumed price and grid factor (peak 164 kW).
- 54% of it is used after hours (nights, weekends, holidays), which are 66% of the hours. Overnight plug load is 39% of the midday level.
- What-if (arithmetic on measured loads): cutting after-hours HVAC and plug load by 10% would save 21,307 kWh ($2,857, 7.4 t CO2), 20% would save 42,614 kWh ($5,715, 14.8 t CO2), 30% would save 63,921 kWh ($8,572, 22.2 t CO2) a year.

**Waste detection**

- 96 events flagged in 365 days: 3,361 kWh above expected (at least 1,179 kWh beyond the alert threshold), $451, 1,170 kg CO2 if every one were fixed. These are estimates for flagged hours, not confirmed savings.
- Test on injected faults (there are no labelled faults in public data). Share of 20 injected 6-48 hour faults found, by size of the extra load as a share of the load's median:

| Load | small (+25-40%) | medium (+50-75%) | large (+100-150%) | alerts per 30 days on real data |
|---|---|---|---|---|
| HVAC | 5% | 25% | 55% | 0.3 |
| Lighting | 25% | 40% | 60% | 4.8 |
| Plug loads | 80% | 80% | 90% | 2.8 |
| HVAC (2020) | 45% | 55% | 80% | 1.9 |

**Forecast accuracy** (next-day forecast refitted monthly, compared with "same hour last week")

| Load | 2019 mean error (kW) | 2019 naive (kW) | 2019 gain | 2019 CV(RMSE) | 80% band coverage | 2020 gain |
|---|---|---|---|---|---|---|
| Whole building | 14.3 | 19.7 | 27% | 37% | 78% | 18% |
| HVAC | 15.1 | 18.9 | 20% | 60% | 75% | 20% |
| Plug loads | 1.9 | 2.7 | 28% | 21% | 78% | -289% |
| Lighting | 0.5 | 0.6 | 21% | 42% | 79% | -27% |

In 2020 the plug and lighting loads dropped sharply (plug averaged 3.2 kW against 15.7 kW in 2019), and a model trained on the earlier year does worse than the naive rule on them. That is reported, not hidden.

**Emergency power**

- Backup runtime forecast versus the runtime the building's actual load would have given, for 265 outages starting on weekday 9 am and Saturday 10 pm in 2019 (48 more skipped for missing meter readings; 250 kWh battery, all loads on): mean actual runtime 4.1 h, mean absolute error 1.3 h (29%).
- Example, winter weekday, 9 am, 250 kWh battery: everything on lasts 2.4 h; keeping lighting only lasts 103.2 h; keeping lighting and plug loads lasts 7.0 h.

**Assumptions** (editable in `campus_energy_forecaster/config.py`): electricity $0.1341/kWh (US average commercial price 2025, EIA Electric Power Monthly Table 5.3); grid 0.348 kg CO2/kWh (US average grid CO2 rate, EPA eGRID2023 (767.2 lb/MWh)); battery 90% usable, 92% efficient.
<!-- RESULTS:END -->

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate     # on Windows: .venv\Scripts\activate
make requirements                                     # numpy, pandas, scikit-learn, pytest
make data                                             # downloads LBNL Building 59 (263 MB, CC0) into data/external/lbnl
python scripts/compute_predictions.py                 # walk-forward predictions, a few minutes
make analysis                                         # writes web/public/data/results.json
python scripts/render_readme.py                       # fills the Results block above from that file
make web                                              # dashboard on http://localhost:3000
```

`web/public/data/results.json` is committed, so the dashboard runs without downloading anything:
`cd web && npm install && npm run dev`.

### Tests

The tests use small synthetic data and cover the features, the forecaster and its band, the walk-forward split (no leakage),
waste detection and pricing, the fault-injection benchmark, and the outage arithmetic. They run on every push through
GitHub Actions, together with the dashboard's lint and build.

```bash
make test        # or: python -m pytest -q
```

## Method

- **Data.** [LBNL Building 59](https://zenodo.org/records/5951008) (Luo et al., Scientific Data, 2022, CC0): an office building
  in Berkeley, California, 2018 to 2020. Meters are kW at 15-minute intervals and are averaged to hours. The files are
  stamped in UTC and are converted to local time. HVAC is the sum of both wings, plug loads the sum of both wings'
  miscellaneous loads, lighting the south-wing meter (there is no north-wing lighting meter in the data).
- **Models.** Gradient-boosted quantile regression (scikit-learn), one model per load. The *expected-usage* model sees only
  calendar, weather and a holiday flag, so a long fault is not absorbed into its baseline. The *day-ahead* model also sees usage from
  24 and 168 hours earlier. A split-conformal correction on the last fifth of each training window sets the band width.
- **Evaluation.** Walk-forward: for each month of 2019 and 2020, refit on the preceding months (the last 6 for HVAC, 12 for
  plug and lighting) and predict that month. Baseline is "same hour last week". The window lengths were picked by comparing
  6 months, 12 months and all history on 2019, so the 2019 numbers are slightly optimistic; 2020 is a second held-out year.
- **Waste benchmark.** Public data has no labelled faults, so extra load is injected into the held-out data and the detector is
  scored on how many injections it finds. The alert threshold (band plus one more band-width) and the 3-hour minimum were chosen
  on 2019 by looking at the trade-off between found faults and alerts on real data.
- **Outage planner.** Battery energy is drained by the forecast hourly load; usable fraction and efficiency are configurable
  (`outage.Backup`). The load used is the day-ahead forecast for the first 24 hours and the baseline model after that (the day-ahead
  model would otherwise read usage from inside the outage). Each runtime is also computed from the load that actually occurred, so the
  forecast can be checked; a window with a missing meter reading gives no runtime rather than a wrong one. Runtimes cap at 14 days.

## Limitations

- One building. The results show the method works on real data from one office; they do not show it generalises to schools,
  hospitals or other climates. The pipeline only needs hourly kW per meter plus outdoor temperature.
- The outage plan only has three load groups (HVAC, lighting, plug loads) to choose from, and lighting is always kept. Finer
  sub-metering, or a list of critical circuits, would give a better plan.
- The weather used in the day-ahead forecast is the recorded weather, standing in for a weather forecast.
- Flagged energy is "above expected", not a confirmed saving. A person has to find the cause.
- After a sharp change in how a building is used (see 2020 above), the models need a refit on recent data.
- The price and grid factor are US averages. Replace them in `config.py` for a real site.
- The meter data was gap-filled by the dataset authors, and about 7% of 2019 hours still have a missing reading; those hours are skipped.

## Project layout

```
campus_energy_forecaster/
  config.py      paths and the price / carbon assumptions
  data.py        load LBNL Building 59 as one hourly frame (local time)
  forecast.py    quantile forecaster, features, walk-forward refitting
  waste.py       alert events, energy / cost / CO2
  outage.py      backup battery runtime and load-set ranking
  evaluation.py  metrics, seasonal-naive baseline, fault injection benchmark
scripts/         download_data, compute_predictions, run_analysis, render_readme
tests/           pytest suite on synthetic data
web/             Next.js dashboard (reads web/public/data/results.json)
```

## Data and licence

Code: MIT (see `LICENSE`). Data: LBNL Building 59, CC0 1.0. Please cite Luo, N., Wang, Z., Blum, D., et al. (2022), *A three-year
dataset supporting research on building energy, HVAC controls, and occupancy analytics*, Scientific Data.
No raw data is committed; `results.json` holds only derived figures.

--------

<p><small>Project based on the <a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">cookiecutter data science project template</a>.</small></p>
