# Campus Energy Forecaster

A building energy forecasting and efficiency tool for schools, clinics and other community buildings. From hourly meter
data it forecasts each load a day ahead with an uncertainty band, flags hours where a load runs above what conditions
explain (and prices the waste in energy, money and CO2), and plans for a grid outage: how long a backup battery keeps
the building running and which loads to keep on to make it last longest.

It targets the Sustainable Energy theme: mainly **usage and efficiency**, with **emergency power for communities when the
grid goes down** as the second feature.

## What it does

1. **Waste alerts.** A quantile model learns what each load (HVAC, lighting, plug loads) normally does for the weather,
   hour and day of week. Hours above its alert threshold for 3 hours or more become events, each with the extra energy,
   cost and CO2.
2. **Quiet-hours report.** A model-free view of how much of each load is drawn at night, at weekends and on holidays, with
   a what-if for cutting it.
3. **Next-day forecast with uncertainty.** P10 / P50 / P90 per load, with the band calibrated on held-out data so the
   coverage is measured, not assumed.
4. **Peak-load management.** The next day's peak demand (size and hour) and an estimate of how much moving flexible HVAC load
   out of the forecast peak hours would cut it.
5. **Emergency power planner.** Given a battery size, an outage start and the loads that must stay on, runtime for every
   combination of loads kept on, with the range implied by the forecast band, checked against the load the building actually drew.
6. **Dashboard** (`web/`) for a facilities manager: alerts, savings, the planner and a page on how far to trust each
   number. It is a static page; nothing is trained in the browser. A section lets you upload your own hourly CSV for a quick in-browser look (typical-week baseline, not the full model; the file never leaves your machine). It also shows the same method run on 30 schools and healthcare buildings.

## Results

<!-- RESULTS:START -->
Demo building: LBNL Building 59 (Berkeley, CA office building), 2018-01 to 2020-12, hourly. All figures are for 2019, where each month is predicted by a model fitted only on earlier months, unless stated. Regenerate with `make analysis` then `python scripts/render_readme.py`.

**What the building uses**

- Electricity (HVAC, lighting, plug loads): 401 MWh, about $104,967 and 78 t CO2 at the assumed price and grid factor (peak 164 kW).
- 54% of it is used after hours (nights, weekends, holidays), which are 66% of the hours. Overnight plug load is 39% of the midday level.
- What-if (arithmetic on measured loads): cutting after-hours HVAC and plug load by 10% would save 21,307 kWh ($5,574, 4.1 t CO2), 20% would save 42,614 kWh ($11,148, 8.3 t CO2), 30% would save 63,921 kWh ($16,722, 12.4 t CO2) a year.

**Waste detection**

- 96 events flagged in 365 days: 3,361 kWh above expected (at least 1,179 kWh beyond the alert threshold), $879, 652 kg CO2 if every one were fixed. These are estimates for flagged hours, not confirmed savings.
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

**Peak-load management**

- Next-day peak forecast over 306 days: off by 14.0 kW on average (22% of the peak); the forecast peak hour is within 2 hours of the real one on 55% of days; 94% of the 31 highest-peak days are among the 62 days flagged.
- Load shifting (best case, planned from the forecast and scored on actual load, on the 31 days with the highest forecast peak): moving 10% of HVAC load out of the peak hours cuts the typical peak by 6.8 kW (5.4%) and the year's highest peak from 164 to 152 kW; moving 20% of HVAC load out of the peak hours cuts the typical peak by 11.5 kW (9.1%) and the year's highest peak from 164 to 142 kW; moving 30% of HVAC load out of the peak hours cuts the typical peak by 13.4 kW (10.6%) and the year's highest peak from 164 to 142 kW.

**Emergency power**

- Backup runtime forecast versus the runtime the building's actual load would have given, for 265 outages starting on weekday 9 am and Saturday 10 pm in 2019 (48 more skipped for missing meter readings; 250 kWh battery, all loads on): mean actual runtime 4.1 h, mean absolute error 1.3 h (29%).
- Example, winter weekday, 9 am, 250 kWh battery: everything on lasts 2.4 h; the longest plan (keep lighting only) lasts 103.2 h; keeping lighting and plug loads lasts 7.0 h.

**Assumptions** (editable in `campus_energy_forecaster/config.py`): electricity $0.2616/kWh (California commercial price 2025, EIA-861 final annual data (US average: 13.37 cents/kWh)); grid 0.194 kg CO2/kWh (CAMX grid CO2 total output rate, EPA eGRID2023 Rev. 2 (428.5 lb/MWh; US average 0.348 kg/kWh)); battery 90% usable, 92% efficient.

**Schools and healthcare buildings (a second public dataset)**

Random sample (fixed seed) of 15 buildings per use with at least 95% complete electricity data in 2016 and 2017. Each month of 2017 is predicted by a model fitted on the trailing 12 months. Same code as the demo building, whole-building meter only. Data: Building Data Genome Project 2 (BDG2), CC BY 4.0.

| Building type | Buildings | Median error vs last week | Buildings that beat it | 80% band held | Large faults found | Alerts per 30 days |
|---|---|---|---|---|---|---|
| Schools and colleges | 15 at 7 sites | 20% lower | 67% | 80% | 95% | 1.9 |
| Healthcare buildings | 15 at 4 sites | 8% lower | 53% | 76% | 100% | 1.2 |

Medians across buildings. The method helps clearly for schools and colleges, only modestly for healthcare buildings, and fails on some individual buildings whose use changed between the training and test year. The emergency planner needs end-use meters, which this dataset lacks, so it is not part of this check.

<!-- RESULTS:END -->

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate     # on Windows: .venv\Scripts\activate
make requirements                                     # numpy, pandas, scikit-learn, pytest
make data                                             # downloads LBNL Building 59 (263 MB, CC0) into data/external/lbnl
python scripts/compute_predictions.py                 # walk-forward predictions, a few minutes
python scripts/download_data.py bdg2                  # optional: Building Data Genome 2 (about 200 MB, CC BY 4.0; pip install remotezip)
python scripts/validate_buildings.py                  # optional: the method on 30 schools and healthcare buildings
make analysis                                         # writes web/public/data/results.json
python scripts/render_readme.py                       # fills the Results block above from that file
make web                                              # dashboard on http://localhost:3000
pip install reportlab matplotlib && python scripts/build_proposal.py   # two-page proposal PDF in proposal/
```

Live dashboard: https://aslanvaida.github.io/campus-energy-forecaster/

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

- The emergency planner and the end-use analysis are demonstrated on one building (an office in California), because that is the only public dataset here with end-use sub-meters. The 30-building check covers whole-building electricity only, and it shows the method is uneven: it helps for most schools, only modestly for healthcare buildings, and fails on some individual buildings. The pipeline only needs hourly kW per meter plus outdoor temperature. No real school or clinic pilot has been done.
- The outage plan only has three load groups (HVAC, lighting, plug loads) to choose from; you choose which must stay on. Finer
  sub-metering, or a list of critical circuits, would give a better plan.
- The peak-shifting estimate is a best case: it assumes HVAC load can be moved freely into the day's quietest hours and reports kW, not dollars, because demand charges are tariff-specific.
- The weather used in the day-ahead forecast is the recorded weather, standing in for a weather forecast.
- Flagged energy is "above expected", not a confirmed saving. A person has to find the cause.
- After a sharp change in how a building is used (see 2020 above), the models need a refit on recent data.
- The price and grid factor are California values, matching the demo building (US averages are in `config.py` comments). Replace them for a real site.
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
  peak.py        next-day peak forecast and load-shifting estimate
  multibuilding.py  the method on schools and healthcare buildings (BDG2)
scripts/         download_data, compute_predictions, run_analysis, validate_buildings, render_readme, build_proposal
proposal/        project proposal PDF (generated from results.json)
tests/           pytest suite on synthetic data
web/             Next.js dashboard (reads web/public/data/results.json)
```

## Data and licence

Code: MIT (see `LICENSE`). Data: LBNL Building 59, CC0 1.0; Building Data Genome Project 2, CC BY 4.0 (Miller et al., Scientific Data, 2020). Please cite Luo, N., Wang, Z., Blum, D., et al. (2022), *A three-year
dataset supporting research on building energy, HVAC controls, and occupancy analytics*, Scientific Data.
No raw data is committed; `results.json` holds only derived figures.

--------

<p><small>Project based on the <a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">cookiecutter data science project template</a>.</small></p>
