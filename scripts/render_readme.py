"""Fill the results block of README.md from web/public/data/results.json, so no number in the README is typed by hand.

    python scripts/render_readme.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from campus_energy_forecaster.config import PROJ_ROOT, RESULTS_JSON

START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"


def n(x, d=0):
    return f"{x:,.{d}f}"


def block(r):
    ov, w, ah, o, a = r["overview"], r["waste"], r["after_hours"], r["outage"], r["assumptions"]
    f = r["forecast"]
    L = []
    L.append(f"Demo building: {r['dataset']['name']}, {r['dataset']['period']}. All figures are for 2019, where each month is predicted by a model "
             "fitted only on earlier months, unless stated. Regenerate with `make analysis` then `python scripts/render_readme.py`.\n")
    L.append("**What the building uses**\n")
    L.append(f"- Electricity (HVAC, lighting, plug loads): {n(ov['annual_kwh']['total'] / 1000)} MWh, about ${n(ov['annual_cost_usd'])} and "
             f"{n(ov['annual_co2_t'])} t CO2 at the assumed price and grid factor (peak {n(ov['peak_kw'])} kW).")
    L.append(f"- {n(ah['total']['after_hours_share_pct'])}% of it is used after hours (nights, weekends, holidays), which are "
             f"{n(ah['share_of_hours_after_hours_pct'])}% of the hours. Overnight plug load is {n(ah['overnight_vs_midday_plug_pct'])}% of the midday level.")
    wi = ah["what_if"]
    L.append("- What-if (arithmetic on measured loads): cutting after-hours HVAC and plug load by "
             + ", ".join(f"{x['cut_pct']}% would save {n(x['kwh'])} kWh (${n(x['cost_usd'])}, {n(x['co2_kg'] / 1000, 1)} t CO2)" for x in wi) + " a year.\n")
    L.append("**Waste detection**\n")
    s = w["summary"]
    L.append(f"- {s['events']} events flagged in {n(w['days'])} days: {n(s['excess_kwh'])} kWh above expected (at least {n(s['excess_kwh_floor'])} kWh beyond the alert "
             f"threshold), ${n(s['cost_usd'])}, {n(s['co2_kg'])} kg CO2 if every one were fixed. These are estimates for flagged hours, not confirmed savings.")
    L.append("- Test on injected faults (there are no labelled faults in public data). Share of 20 injected 6-48 hour faults found, by size of the extra load as a share of the load's median:\n")
    L.append("| Load | " + " | ".join(f"{x['size']} (+{x['extra_load_pct_of_median'][0]}-{x['extra_load_pct_of_median'][1]}%)" for x in w["benchmark"]["hvac"]["by_size"]) + " | alerts per 30 days on real data |")
    L.append("|---|---|---|---|---|")
    for b in w["benchmark"].values():
        L.append(f"| {b['label']} | " + " | ".join(f"{n(x['recall_pct'])}%" for x in b["by_size"]) + f" | {n(b['flagged_events_per_30d'], 1)} |")
    L.append("\n**Forecast accuracy** (next-day forecast refitted monthly, compared with \"same hour last week\")\n")
    L.append("| Load | 2019 mean error (kW) | 2019 naive (kW) | 2019 gain | 2019 CV(RMSE) | 80% band coverage | 2020 gain |")
    L.append("|---|---|---|---|---|---|---|")
    for k in ("total", "hvac", "plug", "lighting"):
        x, y = f[k]["2019"], f[k]["2020"]
        L.append(f"| {f[k]['label']} | {n(x['mae_kw'], 1)} | {n(x['naive_mae_kw'], 1)} | {n(x['mae_gain_vs_naive_pct'])}% | {n(x['cv_rmse_pct'])}% | {n(x['band_coverage_pct'])}% | {n(y['mae_gain_vs_naive_pct'])}% |")
    m20 = ov["mean_kw_by_year"]
    L.append(f"\nIn 2020 the plug and lighting loads dropped sharply (plug averaged {n(m20['2020']['plug'], 1)} kW against {n(m20['2019']['plug'], 1)} kW in 2019), "
             "and a model trained on the earlier year does worse than the naive rule on them. That is reported, not hidden.\n")
    L.append("**Emergency power**\n")
    acc = o["accuracy"]
    L.append(f"- Backup runtime forecast versus the runtime the building's actual load would have given, for {n(acc['n_starts'])} outages starting on weekday 9 am and Saturday 10 pm in 2019 "
             f"({n(acc['n_skipped_missing_data'])} more skipped for missing meter readings; 250 kWh battery, all loads on): mean actual runtime {n(acc['mean_actual_runtime_h'], 1)} h, mean absolute error {n(acc['mae_h'], 1)} h ({n(acc['mape_pct'])}%).")
    sc = o["scenarios"][0]
    b250 = next(b for b in sc["batteries"] if b["capacity_kwh"] == 250)["options"]
    allon = next(x for x in b250 if not x["shed"])
    L.append(f"- Example, {sc['label'].lower()}, 250 kWh battery: everything on lasts {n(allon['runtime_h'], 1)} h; keeping lighting only lasts {n(b250[0]['runtime_h'], 1)} h; "
             f"keeping lighting and plug loads lasts {n(next(x for x in b250 if x['keep'] == ['lighting', 'plug'])['runtime_h'], 1)} h.\n")
    L.append(f"**Assumptions** (editable in `campus_energy_forecaster/config.py`): electricity ${a['tariff_usd_per_kwh']}/kWh ({a['tariff_source']}); "
             f"grid {a['carbon_kg_per_kwh']} kg CO2/kWh ({a['carbon_source']}); battery {n(100 * o['backup_assumptions']['usable_fraction'])}% usable, "
             f"{n(100 * o['backup_assumptions']['efficiency'])}% efficient.")
    return "\n".join(L)


def main():
    r = json.loads(RESULTS_JSON.read_text())
    p = PROJ_ROOT / "README.md"
    s = p.read_text(encoding="utf-8")
    i, j = s.index(START) + len(START), s.index(END)
    p.write_text(s[:i] + "\n" + block(r) + "\n" + s[j:], encoding="utf-8")
    print("README.md updated")


if __name__ == "__main__":
    main()
