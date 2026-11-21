"""Build the two-page project proposal PDF. Every number is read from web/public/data/results.json
(written by scripts/run_analysis.py), so the proposal cannot drift from the code.

    python scripts/build_proposal.py        # -> proposal/Campus_Energy_Forecaster_Proposal.pdf
Needs: pip install reportlab matplotlib
"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from campus_energy_forecaster.config import PROJ_ROOT, RESULTS_JSON

OUT = PROJ_ROOT / "proposal" / "Campus_Energy_Forecaster_Proposal.pdf"
US_PRICE = 0.1337   # US commercial average 2025, EIA-861 final annual data (cents/kWh / 100); for a sensitivity line only
INK, ACCENT, BLUE, GREEN, GREY = "#1f2933", "#d9822b", "#2a6fb0", "#2e8b57", "#8a949e"

R = json.loads(RESULTS_JSON.read_text())
OV, W, AH, O, F, A = R["overview"], R["waste"], R["after_hours"], R["outage"], R["forecast"], R["assumptions"]
PK = R["peak"]
M = json.loads((RESULTS_JSON.parent / "multibuilding.json").read_text())
DEMO_URL = "https://aslanvaida.github.io/campus-energy-forecaster/"   # hosted dashboard (GitHub Pages)


def n(x, d=0):
    return f"{x:,.{d}f}"


def figure() -> io.BytesIO:
    s = R["series"]
    fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.15), gridspec_kw={"width_ratios": [1, 1.5, 1.25]})
    plt.rcParams.update({"font.size": 7, "axes.edgecolor": GREY, "text.color": INK, "axes.labelcolor": INK})
    # A: share of each load used after hours
    rows = [("HVAC", AH["hvac"]), ("Plug loads", AH["plug"]), ("Lighting", AH["lighting"]), ("Whole building", AH["total"])]
    ax[0].barh([r[0] for r in rows][::-1], [r[1]["after_hours_share_pct"] for r in rows][::-1], color=ACCENT)
    for i, (_, v) in enumerate(rows[::-1]):
        ax[0].text(v["after_hours_share_pct"] + 1.5, i, f"{v['after_hours_share_pct']:.0f}%", va="center", fontsize=7)
    ax[0].set_xlim(0, 80)
    ax[0].set_title("A. Share used after hours", fontsize=7.5, loc="left", fontweight="bold")
    ax[0].tick_params(labelsize=6.5)
    # B: forecast band
    t = pd.to_datetime(s["hours"])
    d = s["total"]
    ax[1].fill_between(t, [v if v is not None else float("nan") for v in d["lo"]], [v if v is not None else float("nan") for v in d["hi"]], color=BLUE, alpha=0.22, lw=0)
    ax[1].plot(t, [v if v is not None else float("nan") for v in d["mid"]], color=BLUE, lw=0.9, ls="--")
    ax[1].plot(t, [v if v is not None else float("nan") for v in d["actual"]], color=ACCENT, lw=1.1)
    ax[1].set_ylabel("kW", fontsize=7)
    ax[1].set_title("B. Next-day forecast and 80% band", fontsize=7.5, loc="left", fontweight="bold")
    ax[1].tick_params(labelsize=6.5)
    ax[1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d"))
    ax[1].xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=4))
    # C: outage plans
    sc = O["scenarios"][0]
    opts = next(b for b in sc["batteries"] if b["capacity_kwh"] == 250)["options"]
    names = {"hvac": "HVAC", "lighting": "Lighting", "plug": "Plug"}
    lab = [" + ".join(names[k] for k in o["keep"]) for o in opts][::-1]
    y = range(len(opts))
    ax[2].barh([i + 0.2 for i in y], [o["runtime_h"] for o in opts][::-1], height=0.38, color=BLUE, label="Forecast")
    ax[2].barh([i - 0.2 for i in y], [o["actual_runtime_h"] for o in opts][::-1], height=0.38, color=GREEN, label="Real load")
    ax[2].set_yticks(list(y))
    ax[2].set_yticklabels(lab, fontsize=6.2)
    ax[2].set_xscale("log")
    ax[2].set_xlabel("hours of backup (log scale)", fontsize=6.5)
    ax[2].tick_params(labelsize=6.5)
    ax[2].legend(fontsize=6, frameon=False, loc="lower right")
    ax[2].set_title("C. Loads to keep on", fontsize=7, loc="left", fontweight="bold")
    for a in ax:
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout(pad=0.6, w_pad=1.0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300)
    plt.close(fig)
    buf.seek(0)
    return buf


def evidence_table():
    hdr = ["Load", "Error vs last week (2019)", "CV(RMSE)", "80% band held", "Large faults found", "Medium", "Small"]
    rows = [hdr]
    for k in ("total", "hvac", "plug", "lighting"):
        f = F[k]["2019"]
        b = R["waste"]["benchmark"].get(k)
        rec = [f"{n(x['recall_pct'])}%" for x in b["by_size"][::-1]] if b else ["n/a"] * 3
        rows.append([F[k]["label"], f"{n(f['mae_gain_vs_naive_pct'])}% lower", f"{n(f['cv_rmse_pct'])}%", f"{n(f['band_coverage_pct'])}%", *rec])
    t = Table(rows, colWidths=[27 * mm, 38 * mm, 20 * mm, 25 * mm, 28 * mm, 17 * mm, 17 * mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.4), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.6),
                           ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(INK)), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3e7d8")),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d5dae0")), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return KeepTogether([t, Paragraph("Fault columns: share of synthetic faults (extra load of 100-150%, 50-75% and 25-40% of the typical load, 6-48 hours long) found. "
                                      "The whole building has no fault test.", ParagraphStyle("c", fontName="Helvetica", fontSize=6.8, leading=8.4, textColor=colors.HexColor("#52606d")))])


def build():
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=8.6, leading=11.9, textColor=colors.HexColor(INK), alignment=TA_LEFT, spaceAfter=3)
    h = ParagraphStyle("h", parent=body, fontName="Helvetica-Bold", fontSize=10.2, leading=12.5, spaceBefore=5, spaceAfter=2, keepWithNext=1, textColor=colors.HexColor("#8a4b0f"))
    title = ParagraphStyle("t", parent=body, fontName="Helvetica-Bold", fontSize=17, leading=20, spaceAfter=1)
    sub = ParagraphStyle("s", parent=body, fontSize=9, leading=11.5, textColor=colors.HexColor("#52606d"), spaceAfter=4)
    small = ParagraphStyle("sm", parent=body, fontSize=7, leading=8.8, textColor=colors.HexColor("#52606d"))
    bullet = ParagraphStyle("b", parent=body, leftIndent=9, bulletIndent=0, spaceAfter=1.5)

    def P(t, st=body):
        return Paragraph(t, st)

    def B(t):
        return Paragraph(t, bullet, bulletText="•")

    CO2 = "CO<sub>2</sub>"
    tot = F["total"]["2019"]
    hv, pl = F["hvac"]["2019"], F["plug"]["2019"]
    s = W["summary"]
    wi = {x["cut_pct"]: x for x in AH["what_if"]}
    acc = O["accuracy"]
    sc = O["scenarios"][0]
    opts = next(b for b in sc["batteries"] if b["capacity_kwh"] == 250)["options"]
    allon = next(o for o in opts if not o["shed"])
    lp = next(o for o in opts if o["keep"] == ["lighting", "plug"])
    bm = W["benchmark"]
    big = lambda k: bm[k]["by_size"][2]["recall_pct"]

    story = [
        P("Campus Energy Forecaster", title),
        P("Cutting wasted electricity and planning for grid outages in schools, clinics and community buildings", sub),
        P("<b>Global Sustainability Challenge 2026-27</b> &middot; Theme: Sustainable Energy &middot; Focus: Usage and Efficiency; "
          "emergency power for communities when the grid goes down", small),
        P("<b>Team Terra Nexus:</b> Aslan Shaukat Vaida, Ramith Vaid, Soham Bisaria, Rohit Menon, Panav Java", small),
        Spacer(1, 3),
        P("1. The problem", h),
        P(f"Meter data is widely collected but rarely turned into decisions: it is hard to tell an unusual hour from a normal one, "
          f"or to see what the extra energy costs in money and carbon. In our demonstration building, a real office, <b>{n(AH['total']['after_hours_share_pct'])}% of "
          f"all electricity is used in the {n(AH['share_of_hours_after_hours_pct'])}% of hours when the building should be quiet</b> (nights, weekends, holidays), "
          f"and overnight plug load stays at {n(AH['overnight_vs_midday_plug_pct'])}% of its midday level. Separately, when the grid fails, "
          f"a school or clinic with a backup battery has no way to know how long it will last or which loads to switch off to stretch it."),
        P("2. The solution", h),
        P("Campus Energy Forecaster turns hourly meter data into decisions for a facilities manager, with no data-science skills needed:"),
        B("<b>Waste alerts.</b> A model learns what each load (HVAC, lighting, plug loads) normally does for the weather, hour and day of week. "
          f"Hours well above that become alerts with the extra energy, cost and {CO2}."),
        B("<b>Quiet-hours report.</b> A direct measurement of how much of each load runs after hours, with a what-if for cutting it."),
        B("<b>Next-day forecast with uncertainty.</b> A 24-hour forecast of each load with a calibrated 80% band, so planners see the range, not one number."),
        B("<b>Peak-load management.</b> It forecasts tomorrow's demand peak (size and hour) and estimates how much moving flexible HVAC load out of those hours would cut it."),
        B("<b>Emergency power planner.</b> Choose an outage start, a battery size and the loads that must stay on: it shows backup runtime for every combination of loads kept on, "
          "with a range, so the manager knows what to switch off first."),
        B("<b>Try it on your own data.</b> The live dashboard lets anyone upload an hourly CSV and get a quick in-browser look (typical-week baseline, flagged runs, peaks, battery runtime); "
          "the file never leaves the browser, and the full forecasting model runs in the open-source Python code."),
        Spacer(1, 3),
        Image(figure(), width=178 * mm, height=178 * mm * 2.15 / 7.4),
        P(f"<b>Figure.</b> A: share of each load drawn after hours in 2019. B: two weeks of whole-building load (amber) against the forecast (dashed) and its 80% band. "
          f"C: backup runtime for each choice of loads to keep on, for a 250 kWh battery and an outage starting on a {sc['label'].lower()}, forecast against what the building actually drew. Data: {R['dataset']['name']}.", small),
        P("3. Evidence: real data, honest tests", h),
        P(f"We built and tested everything on the public LBNL Building 59 dataset (three years of hourly electricity by end use, CC0 licence). Each month of 2019 is "
          f"predicted by a model fitted only on earlier months. Against the usual baseline of &quot;same hour last week&quot;, the whole-building forecast has "
          f"<b>{n(tot['mae_gain_vs_naive_pct'])}% lower mean error</b> ({n(tot['mae_kw'], 1)} kW against {n(tot['naive_mae_kw'], 1)} kW), and the 80% band held "
          f"{n(tot['band_coverage_pct'])}% of hours. Plug loads improve {n(pl['mae_gain_vs_naive_pct'])}% and HVAC {n(hv['mae_gain_vs_naive_pct'])}%. "
          f"Public data has no labelled faults, so we added synthetic extra load to held-out data: large faults (one to one-and-a-half times the typical load) were found "
          f"{n(big('hvac'))}% of the time on HVAC and {n(big('plug'))}% on plug loads, while small HVAC faults mostly hide in its noise "
          f"({n(bm['hvac']['by_size'][0]['recall_pct'])}%). On real, unmodified data the alerts fire {n(bm['hvac']['flagged_events_per_30d'], 1)} (HVAC) to "
          f"{n(bm['lighting']['flagged_events_per_30d'], 1)} (lighting) times per 30 days. For {n(acc['n_starts'])} simulated outages the forecast backup runtime was off by "
          f"{n(acc['mae_h'], 1)} h on average against a real runtime of {n(acc['mean_actual_runtime_h'], 1)} h."),
        evidence_table(),
        Spacer(1, 3),
        P(f"<b>Beyond one building.</b> We ran the same method, unchanged, on {M['all']['n_buildings']} schools, colleges and healthcare buildings from a second public dataset "
          f"(Building Data Genome 2; whole-building electricity only). Against the same baseline the median error was {n(M['groups']['Education']['median_mae_gain_vs_naive_pct'])}% lower for "
          f"{M['groups']['Education']['n_buildings']} schools and colleges ({n(M['groups']['Education']['share_buildings_beating_naive_pct'])}% of them beat the baseline) but only "
          f"{n(M['groups']['Healthcare']['median_mae_gain_vs_naive_pct'])}% lower for {M['groups']['Healthcare']['n_buildings']} healthcare buildings ({n(M['groups']['Healthcare']['share_buildings_beating_naive_pct'])}% beat it). "
          f"Large synthetic faults were found {n(M['groups']['Education']['median_recall_pct']['large'])}% (schools) and {n(M['groups']['Healthcare']['median_recall_pct']['large'])}% (healthcare) of the time. "
          f"Some individual buildings failed badly after their use changed between years."),
        Spacer(1, 3),
        P(f"<b>Where it fails, and we say so:</b> in 2020 plug and lighting loads fell sharply (plug averaged {n(OV['mean_kw_by_year']['2020']['plug'], 1)} kW against "
          f"{n(OV['mean_kw_by_year']['2019']['plug'], 1)} kW in 2019) and a model trained on the earlier year then does worse than the naive rule on those loads. "
          f"The tool therefore refits monthly and flags such changes for a refit. Our largest outage miss, in an autumn scenario, most likely reflects a change in how the building's HVAC was being run."),
        P("4. Impact", h),
        B(f"<b>Efficiency.</b> The model flagged {s['events']} waste events in 2019: {n(s['excess_kwh'])} kWh above expected, worth {'$' + n(s['cost_usd'])} and "
          f"{n(s['co2_kg'])} kg {CO2} if every one were fixed (estimates, not confirmed savings). The larger prize is the quiet-hours load: cutting after-hours HVAC and plug "
          f"load by 20% would save <b>{n(wi[20]['kwh'])} kWh, ${n(wi[20]['cost_usd'])} and {n(wi[20]['co2_kg'] / 1000, 1)} t {CO2} a year</b> in this building "
          f"(at the US average price instead, about ${n(wi[20]['kwh'] * US_PRICE)}). Whether that load can be cut is for the facilities team to confirm."),
        B(f"<b>Peak demand.</b> The peak forecast is off by {n(PK['accuracy']['mae_kw'], 1)} kW on average and {n(PK['accuracy']['top_days_caught_pct'])}% of the {PK['accuracy']['top_days']} highest-peak days are among the "
          f"{2 * PK['accuracy']['top_days']} days it flags. Moving {PK['shift'][1]['share_shifted_pct']}% of HVAC load out of the forecast peak hours on those flagged days would cut the typical peak by "
          f"{n(PK['shift'][1]['mean_peak_reduction_kw'], 1)} kW ({n(PK['shift'][1]['mean_peak_reduction_pct'])}%) and the year's highest peak from {n(PK['shift'][1]['annual_peak_before_kw'])} to "
          f"{n(PK['shift'][1]['annual_peak_after_kw'])} kW (a best case, planned from the forecast and scored on actual load)."),
        B(f"<b>Resilience.</b> In the sample outage ({sc['label'].lower()}, 250 kWh battery) everything on lasts {n(allon['runtime_h'], 1)} h, lighting and plug loads "
          f"{n(lp['runtime_h'], 1)} h, and lighting alone {n(opts[0]['runtime_h'], 1)} h. Choosing what to shed is the difference between losing the building in hours and keeping "
          f"a reduced set of loads running for days."),
        B("<b>Scalability.</b> The only inputs are hourly kW per meter and outdoor temperature, which smart meters and building-management systems typically record, so no new hardware is needed. "
          "That suits schools and clinics in regions with unreliable grids, where backup power is already part of operations. The multi-building check above supports this for schools and, less strongly, "
          "for healthcare buildings; it is not a pilot in a real community."),
        P("5. What is new", h),
        P("Waste detection, forecast uncertainty and outage planning are usually treated as separate problems. Here one forecast feeds all three, and every claim is "
          "reproducible: the repository builds each number in this document from public data, tests the detector against deliberately injected faults, and reports the "
          "failure case. The planner ranks loads by how long they extend backup power, which is what a manager actually decides in an outage."),
        P("6. Limits and next steps", h),
        P("The emergency planner and the end-use analysis are demonstrated on one office building, the only public dataset with end-use meters; the 30-building check covers whole-building "
          "electricity only. The peak-shifting figure is a best case in kW, not dollars, because demand charges depend on the tariff. Next: let users list their own critical circuits, "
          "add a weather-forecast feed, handle buildings whose use changes (automatic refit alerts), and pilot with a real school or clinic. Price and carbon figures are editable assumptions. "
          "The recorded weather stands in for a weather forecast in this demonstration.", body),
        Spacer(1, 2),
        P(f"<b>Sources.</b> Data: Luo, N., Wang, Z., Blum, D., et al. (2022), A three-year dataset supporting research on building energy, HVAC controls, and occupancy analytics, "
          f"Scientific Data, https://zenodo.org/records/5951008 (CC0). Price: California commercial average 2025, {n(A['tariff_usd_per_kwh'] * 100, 2)} cents/kWh, U.S. EIA Form EIA-861 "
          f"final annual data, Historical State Data (US average 13.37). Carbon: CAMX grid CO<sub>2</sub> total output rate 428.464 lb/MWh = {A['carbon_kg_per_kwh']} kg/kWh, U.S. EPA eGRID2023 "
          f"Revision 2 (US average 767.209 lb/MWh). Multi-building check: Miller, C., et al. (2020), The Building Data Genome Project 2, Scientific Data, https://zenodo.org/records/3887306 (CC BY 4.0). "
          f"Code and results: https://github.com/aslanvaida/campus-energy-forecaster" + (f" &middot; Live dashboard: {DEMO_URL}" if DEMO_URL else ""), small),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=13 * mm, bottomMargin=12 * mm,
                            title="Campus Energy Forecaster: project proposal", author="Terra Nexus: Aslan Shaukat Vaida, Ramith Vaid, Soham Bisaria, Rohit Menon, Panav Java",
                            subject="Global Sustainability Challenge 2026-27, Sustainable Energy")
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
