"use client";

import * as React from "react";

import { BandChart } from "@/components/band-chart";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { multi } from "@/lib/multibuilding";
import { LOAD_LABEL, fmt, hoursText, results as R, usd, when } from "@/lib/results";

function Section({ id, title, lead, children }: { id: string; title: string; lead: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <div>
        <h2 id={id} className="text-2xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 max-w-3xl text-muted-foreground text-pretty">{lead}</p>
      </div>
      {children}
    </section>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">{sub}</CardContent>
    </Card>
  );
}

function Pills<T extends string | number>({ items, value, onChange, label }: { items: { id: T; text: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {items.map((it) => (
        <button
          key={String(it.id)}
          type="button"
          aria-pressed={it.id === value}
          onClick={() => onChange(it.id)}
          className={`min-h-10 rounded-full border px-3.5 py-1 text-sm transition-colors sm:min-h-0 sm:px-3 ${
            it.id === value ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted"
          }`}
        >
          {it.text}
        </button>
      ))}
    </div>
  );
}

const keepText = (keep: string[]) => keep.map((k) => LOAD_LABEL[k]).join(" + ");

export function Dashboard() {
  const ov = R.overview, w = R.waste, ah = R.after_hours, tot = R.forecast.total["2019"] as Exclude<(typeof R.forecast.total)["2019"], string>;
  const ahTotal = ah.total as { after_hours_share_pct: number };
  const whatIf = ah.what_if;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-14 px-4 py-10 sm:px-6">
      {/* KPIs */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Energy used in 2019" value={`${fmt(ov.annual_kwh.total / 1000)} MWh`} sub={`${usd(ov.annual_cost_usd)} and ${fmt(ov.annual_co2_t)} t CO₂ at the assumed price and grid factor`} />
        <Kpi label="Used after hours" value={`${fmt(ahTotal.after_hours_share_pct)}%`} sub={`of all energy, in ${fmt(ah.share_of_hours_after_hours_pct)}% of the hours (nights, weekends, holidays)`} />
        <Kpi label="Waste alerts, 2019" value={`${w.summary.events} events`} sub={`about ${fmt(w.summary.excess_kwh)} kWh above expected, ${usd(w.summary.cost_usd)}, ${fmt(w.summary.co2_kg)} kg CO₂ if all were fixed`} />
        <Kpi label="Forecast accuracy" value={`${fmt(tot.mae_gain_vs_naive_pct)}% better`} sub={`than "same hour last week" (mean absolute error). Each month of 2019 is predicted by a model fitted only on earlier months`} />
      </div>

      <Alerts />
      <AfterHours whatIf={whatIf} />
      <Forecast />
      <Peaks />
      <Outage />
      <Scale />
      <Honesty />
    </div>
  );
}

function Alerts() {
  const w = R.waste;
  return (
    <Section id="alerts" title="Waste alerts" lead={`Hours when a load ran well above what the weather, time of day and day of week explain. Largest of ${w.all_events} flagged events in ${w.window}. The saving is what the extra energy would have cost if the cause were fixed.`}>
      <Card>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Load</TableHead>
                <TableHead>Started</TableHead>
                <TableHead className="text-right">Duration</TableHead>
                <TableHead className="hidden text-right sm:table-cell">Extra load</TableHead>
                <TableHead className="text-right">Wasted energy</TableHead>
                <TableHead className="text-right">Cost</TableHead>
                <TableHead className="hidden text-right sm:table-cell">CO₂</TableHead>
                <TableHead>When</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {w.top_events.map((e) => (
                <TableRow key={e.meter + e.start}>
                  <TableCell className="font-medium">{e.label}</TableCell>
                  <TableCell>{when(e.start)}</TableCell>
                  <TableCell className="text-right tabular-nums">{hoursText(e.hours)}</TableCell>
                  <TableCell className="hidden text-right tabular-nums sm:table-cell">{fmt(e.mean_excess_kw, 1)} kW</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {fmt(e.excess_kwh)} kWh
                    <span className="block text-xs text-muted-foreground">at least {fmt(e.excess_kwh_floor)}</span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{usd(e.cost_usd)}</TableCell>
                  <TableCell className="hidden text-right tabular-nums sm:table-cell">{fmt(e.co2_kg)} kg</TableCell>
                  <TableCell>
                    <Badge variant={e.after_hours ? "default" : "secondary"}>{e.after_hours ? "After hours" : "Occupied hours"}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <div className="grid gap-3 sm:grid-cols-3">
        {Object.entries(w.per_meter).map(([k, m]) => (
          <Card size="sm" key={k}>
            <CardHeader>
              <CardDescription>{m.label}</CardDescription>
              <CardTitle className="tabular-nums">{fmt(m.excess_kwh)} kWh · {usd(m.cost_usd)}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{m.events} events in {fmt(w.days)} days</CardContent>
          </Card>
        ))}
      </div>
    </Section>
  );
}

function AfterHours({ whatIf }: { whatIf: { cut_pct: number; kwh: number; cost_usd: number; co2_kg: number }[] }) {
  const ah = R.after_hours;
  const rows = (["hvac", "plug", "lighting"] as const).map((k) => ah[k] as { label: string; after_hours_share_pct: number; after_hours_kwh: number });
  return (
    <Section id="afterhours" title="The quiet-hours opportunity" lead="Measured, not modelled: how much of each load is drawn at night, at weekends and on holidays, when an office should be nearly idle.">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Share of each load used after hours</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-3">
            {rows.map((r) => (
              <div key={r.label}>
                <div className="flex justify-between text-sm"><span>{r.label}</span><span className="tabular-nums">{fmt(r.after_hours_share_pct)}% · {fmt(r.after_hours_kwh)} kWh</span></div>
                <div className="mt-1 h-2 rounded-full bg-muted"><div className="h-2 rounded-full bg-primary" style={{ width: `${r.after_hours_share_pct}%` }} /></div>
              </div>
            ))}
            <p className="text-sm text-muted-foreground">Overnight plug load (midnight to 5 am, weekdays) is {fmt(ah.overnight_vs_midday_plug_pct)}% of the 10 am to 4 pm level.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>What if after-hours HVAC and plug load were cut?</CardTitle>
            <CardDescription>Arithmetic on the measured loads, not a forecast. Whether the load can be cut is for the facilities team to confirm.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Cut</TableHead><TableHead className="text-right">Energy per year</TableHead><TableHead className="text-right">Cost</TableHead><TableHead className="text-right">CO₂</TableHead></TableRow></TableHeader>
              <TableBody>
                {whatIf.map((r) => (
                  <TableRow key={r.cut_pct}>
                    <TableCell className="font-medium">{r.cut_pct}%</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(r.kwh)} kWh</TableCell>
                    <TableCell className="text-right tabular-nums">{usd(r.cost_usd)}</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(r.co2_kg / 1000, 1)} t</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </Section>
  );
}

function Forecast() {
  const [load, setLoad] = React.useState<"total" | "hvac" | "plug" | "lighting">("total");
  const s = R.series as unknown as Record<string, { actual: (number | null)[]; lo: (number | null)[]; mid: (number | null)[]; hi: (number | null)[] }> & { hours: string[]; window: string };
  const m = R.forecast[load]["2019"] as Exclude<(typeof R.forecast.total)["2019"], string>;
  return (
    <Section id="forecast" title="Tomorrow's load, with uncertainty" lead="Every night the tool forecasts the next 24 hours of each load. The shaded band is the range the load stays inside about 80% of the time; it is what the emergency planner uses for its ranges. Alerts use a stricter test on a separate baseline model, so brief excursions from this band are normal.">
      <Card>
        <CardHeader>
          <Pills label="Load" value={load} onChange={setLoad} items={(["total", "hvac", "plug", "lighting"] as const).map((k) => ({ id: k, text: LOAD_LABEL[k] }))} />
          <CardDescription>Two weeks in {s.window.replace(" to ", " – ")} · amber: actual · blue: forecast and band</CardDescription>
        </CardHeader>
        <CardContent>
          <BandChart hours={s.hours} series={s[load]} />
          <p className="mt-2 text-sm text-muted-foreground">
            Over all of 2019: mean error {fmt(m.mae_kw, 1)} kW against {fmt(m.naive_mae_kw, 1)} kW for &quot;same hour last week&quot;; the band held {fmt(m.band_coverage_pct)}% of actual hours (aim: {fmt(m.band_nominal_pct)}%).
          </p>
        </CardContent>
      </Card>
    </Section>
  );
}

function Outage() {
  const O = R.outage;
  const [sc, setSc] = React.useState(0);
  const [cap, setCap] = React.useState(O.batteries_kwh[1]);
  const [must, setMust] = React.useState<string[]>(O.default_must_keep);
  const scenario = O.scenarios[sc];
  const every = scenario.batteries.find((b) => b.capacity_kwh === cap)!.options;
  const options = every.filter((o) => must.every((m) => o.keep.includes(m)));
  const all = every.find((o) => o.shed.length === 0)!;
  const toggle = (k: string) => setMust((m) => (m.includes(k) ? m.filter((x) => x !== k) : [...m, k]));
  const best = options[0];
  const maxH = Math.max(...options.map((o) => o.runtime_h));
  const prof = scenario.load_profile;
  const maxKw = Math.max(...prof.map((p) => p.hvac + p.lighting + p.plug));
  const gain = all.runtime_h > 0 ? best.runtime_h / all.runtime_h : 0;
  return (
    <Section id="outage" title="Emergency power planner" lead="When the grid goes down, how long does a backup battery keep a building running, and which loads should stay on to make it last longest? Runtimes use the forecast load for that moment (day-ahead forecast for the first 24 hours, a baseline model after that), and each is checked against what the building actually drew. Windows are chosen where the meter readings are complete.">
      <Card>
        <CardHeader className="gap-3">
          <Pills label="Outage starts" value={sc} onChange={setSc} items={O.scenarios.map((s, i) => ({ id: i, text: s.label }))} />
          <Pills label="Battery size" value={cap} onChange={setCap} items={O.batteries_kwh.map((c) => ({ id: c, text: `${fmt(c)} kWh` }))} />
          <div role="group" aria-label="Loads that must stay on" className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted-foreground">Must stay on:</span>
            {(["hvac", "lighting", "plug"] as const).map((k) => (
              <label key={k} className="flex min-h-10 cursor-pointer items-center gap-1.5 rounded-full border px-3.5 py-1 hover:bg-muted sm:min-h-0 sm:px-3">
                <input type="checkbox" checked={must.includes(k)} onChange={() => toggle(k)} className="accent-[var(--primary)]" />
                {LOAD_LABEL[k]}
              </label>
            ))}
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Kpi label="Everything on" value={hoursText(all.runtime_h)} sub={`${fmt(all.mean_kw)} kW average, ${all.actual_runtime_h != null ? `${hoursText(all.actual_runtime_h)} with the real load` : ""}`} />
            <Kpi label="Longest-lasting plan" value={hoursText(best.runtime_h)} sub={`keep ${keepText(best.keep)}; ${fmt(gain, 1)}× longer`} />
            <Kpi label="Range for best plan" value={`${best.runtime_low_h != null ? hoursText(best.runtime_low_h) : "?"} to ${best.runtime_high_h != null ? hoursText(best.runtime_high_h) : "?"}`} sub="if the load lands at the top or bottom of the forecast band" />
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Keep running</TableHead>
                <TableHead className="text-right">Average load</TableHead>
                <TableHead className="text-right">Forecast runtime</TableHead>
                <TableHead className="text-right">With the real load</TableHead>
                <TableHead className="w-1/4"> </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {options.map((o) => (
                <TableRow key={o.keep.join()}>
                  <TableCell className="font-medium">{keepText(o.keep)}</TableCell>
                  <TableCell className="text-right tabular-nums">{fmt(o.mean_kw, 1)} kW</TableCell>
                  <TableCell className="text-right tabular-nums">{hoursText(o.runtime_h)}</TableCell>
                  <TableCell className="text-right tabular-nums">{o.actual_runtime_h != null ? hoursText(o.actual_runtime_h) : "n/a"}</TableCell>
                  <TableCell><div className="h-2 rounded-full bg-muted"><div className="h-2 rounded-full bg-primary" style={{ width: `${(100 * o.runtime_h) / maxH}%` }} /></div></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div>
            <p className="mb-2 text-sm font-medium">Forecast load over the first 24 hours of this outage (kW)</p>
            <div className="flex h-24 items-end gap-0.5" role="img" aria-label="Forecast load by hour">
              {prof.map((p) => (
                <div key={p.hour} className="flex flex-1 flex-col-reverse" title={`+${p.hour} h: HVAC ${p.hvac}, plug ${p.plug}, lighting ${p.lighting} kW`}>
                  <div className="bg-[var(--test)]" style={{ height: `${(96 * p.hvac) / maxKw}px` }} />
                  <div className="bg-primary" style={{ height: `${(96 * p.plug) / maxKw}px` }} />
                  <div className="bg-[var(--ok)]" style={{ height: `${(96 * p.lighting) / maxKw}px` }} />
                </div>
              ))}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Blue: HVAC · amber: plug loads · green: lighting. Battery assumptions: {fmt(100 * O.backup_assumptions.usable_fraction)}% usable, {fmt(100 * O.backup_assumptions.efficiency)}% efficient; pick the loads that must stay on, and the plan keeps those and ranks the rest.</p>
          </div>
        </CardContent>
      </Card>
    </Section>
  );
}

function Peaks() {
  const P = R.peak;
  const a = P.accuracy;
  return (
    <Section id="peaks" title="Peak-load management" lead="Tomorrow's highest demand, forecast a day ahead, and what moving flexible load out of those hours would do to it. High peaks drive demand charges where a tariff has them and are what a weak grid or a backup system struggles with.">
      <div className="grid gap-3 sm:grid-cols-3">
        <Kpi label="Peak size forecast" value={`${fmt(a.mae_kw, 1)} kW off`} sub={`on average, over ${a.n_days} days (${fmt(a.mape_pct)}% of the peak)`} />
        <Kpi label="Highest-peak days caught" value={`${fmt(a.top_days_caught_pct)}%`} sub={`of the ${a.top_days} days with the highest real peak were among the ${2 * a.top_days} days flagged`} />
        <Kpi label="Peak hour right" value={`${fmt(a.peak_hour_within_2h_pct)}%`} sub="of days: forecast peak hour within 2 hours of the real one" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Load-shifting estimate</CardTitle>
            <CardDescription>On the {P.shift[0].days_acted_on} days with the highest forecast peak, move a share of HVAC load out of the forecast peak hours into the day&apos;s quietest hours (for example pre-cooling). Planned from the forecast, scored on what really happened. A best case: it assumes the load can be moved freely.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>HVAC load moved</TableHead><TableHead className="text-right">Typical peak cut</TableHead><TableHead className="text-right">Year&apos;s highest peak</TableHead></TableRow></TableHeader>
              <TableBody>
                {P.shift.map((s) => (
                  <TableRow key={s.share_shifted_pct}>
                    <TableCell className="font-medium">{s.share_shifted_pct}%</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(s.mean_peak_reduction_kw, 1)} kW ({fmt(s.mean_peak_reduction_pct, 1)}%)</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(s.annual_peak_before_kw)} to {fmt(s.annual_peak_after_kw)} kW</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Highest forecast peaks</CardTitle>
            <CardDescription>The ten days with the highest forecast peak, and what happened.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Day</TableHead><TableHead className="text-right">Forecast</TableHead><TableHead className="text-right">Actual</TableHead></TableRow></TableHeader>
              <TableBody>
                {P.next_days.map((d) => (
                  <TableRow key={d.date}>
                    <TableCell className="font-medium">{when(d.date + "T00:00").split(",")[0]}</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(d.forecast_kw)} kW at {d.forecast_hour}:00</TableCell>
                    <TableCell className="text-right tabular-nums">{d.actual_kw != null ? `${fmt(d.actual_kw)} kW at ${d.actual_hour}:00` : "n/a"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </Section>
  );
}

function Scale() {
  const groups = Object.values(multi.groups);
  return (
    <Section id="scale" title="Does it work beyond one office?" lead="The same method, unchanged, was run on a random sample of schools and healthcare buildings from a second public dataset. This is a check of the method on whole-building electricity, not a pilot.">
      <Card>
        <CardContent className="flex flex-col gap-3">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Building type</TableHead>
                <TableHead className="text-right">Buildings</TableHead>
                <TableHead className="text-right">Error vs last week (median)</TableHead>
                <TableHead className="text-right">Buildings that beat it</TableHead>
                <TableHead className="text-right">80% band held</TableHead>
                <TableHead className="text-right">Large faults found</TableHead>
                <TableHead className="text-right">Alerts / 30 days</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.map((g) => (
                <TableRow key={g.label}>
                  <TableCell className="font-medium">{g.label}</TableCell>
                  <TableCell className="text-right tabular-nums">{g.n_buildings} at {g.n_sites} sites</TableCell>
                  <TableCell className="text-right tabular-nums">{fmt(g.median_mae_gain_vs_naive_pct)}% lower</TableCell>
                  <TableCell className="text-right tabular-nums">{fmt(g.share_buildings_beating_naive_pct)}%</TableCell>
                  <TableCell className="text-right tabular-nums">{fmt(g.median_band_coverage_pct)}%</TableCell>
                  <TableCell className="text-right tabular-nums">{fmt(g.median_recall_pct.large)}%</TableCell>
                  <TableCell className="text-right tabular-nums">{fmt(g.median_flagged_events_per_30d, 1)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="text-sm text-muted-foreground">{multi.method} Data: {multi.dataset.name}, licence {multi.dataset.license}. Medians across buildings. The emergency planner needs end-use meters, which this dataset does not have, so it is not part of this check.</p>
        </CardContent>
      </Card>
    </Section>
  );
}

function Honesty() {
  const F = R.forecast;
  const rows = (["total", "hvac", "plug", "lighting"] as const).map((k) => ({
    k,
    a: F[k]["2019"] as Exclude<(typeof F.total)["2019"], string>,
    b: F[k]["2020"] as Exclude<(typeof F.total)["2019"], string>,
  }));
  const B = R.waste.benchmark;
  return (
    <Section id="honesty" title="How far to trust it" lead="Public data, no cherry-picking: every figure on this page comes from code in the repository, and the weak spots are shown here.">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Forecast accuracy on unseen years</CardTitle>
            <CardDescription>Mean error gain over &quot;same hour last week&quot;. The model is refitted monthly on the months before the one it predicts.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Load</TableHead><TableHead className="text-right">2019 gain</TableHead><TableHead className="text-right">2019 CV(RMSE)</TableHead><TableHead className="text-right">2020 gain</TableHead></TableRow></TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.k}>
                    <TableCell className="font-medium">{LOAD_LABEL[r.k]}</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(r.a.mae_gain_vs_naive_pct)}%</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(r.a.cv_rmse_pct)}%</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(r.b.mae_gain_vs_naive_pct)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="mt-3 text-sm text-muted-foreground">In 2020 plug loads averaged {fmt(R.overview.mean_kw_by_year["2020"].plug, 1)} kW against {fmt(R.overview.mean_kw_by_year["2019"].plug, 1)} kW in 2019, and lighting {fmt(R.overview.mean_kw_by_year["2020"].lighting, 1)} kW against {fmt(R.overview.mean_kw_by_year["2019"].lighting, 1)} kW. A model fitted on the year before cannot know about a drop that large, so on those two loads it does worse than the naive rule. It needs recent data, and a change like this should trigger a refit.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Can the alerts find real faults?</CardTitle>
            <CardDescription>There are no labelled faults in public data, so extra load was added to the held-out data on purpose: {B.hvac.by_size[0].injected_faults} windows of 6 to 48 hours per size. Share found:</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Load</TableHead>{B.hvac.by_size.map((s) => <TableHead key={s.size} className="text-right capitalize">{s.size} (+{s.extra_load_pct_of_median[0]}–{s.extra_load_pct_of_median[1]}%)</TableHead>)}<TableHead className="text-right">Alerts / 30 days</TableHead></TableRow></TableHeader>
              <TableBody>
                {Object.entries(B).map(([k, b]) => (
                  <TableRow key={k}>
                    <TableCell className="font-medium">{b.label}</TableCell>
                    {b.by_size.map((s) => <TableCell key={s.size} className="text-right tabular-nums">{fmt(s.recall_pct)}%</TableCell>)}
                    <TableCell className="text-right tabular-nums">{fmt(b.flagged_events_per_30d, 1)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="mt-3 text-sm text-muted-foreground">Extra load is given as a share of the load&apos;s typical value. HVAC is noisy, so small faults hide in it; large ones are found more often. Alerts per 30 days are counted on real, unmodified data and are not labelled, so some may be real faults and some may be shifts in how the building runs.</p>
          </CardContent>
        </Card>
      </div>
      <Card size="sm">
        <CardContent className="flex flex-col gap-2 text-sm text-muted-foreground">
          <p><strong className="text-foreground">Outage runtimes:</strong> for {fmt(R.outage.accuracy.n_starts)} outages starting at 9 am on weekdays and 10 pm on Saturdays in 2019 (250 kWh battery, everything on), the forecast runtime was off by {fmt(R.outage.accuracy.mae_h, 1)} h on average, against a real runtime of {fmt(R.outage.accuracy.mean_actual_runtime_h, 1)} h ({fmt(R.outage.accuracy.mape_pct)}% error). A further {R.outage.accuracy.n_skipped_missing_data} outage start times were left out because meter readings were missing. Runtimes cap at 14 days.</p>
          <p><strong className="text-foreground">Assumptions you should replace:</strong> electricity {fmt(R.assumptions.tariff_usd_per_kwh * 100, 2)} ¢/kWh ({R.assumptions.tariff_source}); grid {fmt(R.assumptions.carbon_kg_per_kwh, 3)} kg CO₂/kWh ({R.assumptions.carbon_source}). Weather in the forecast is the weather that was recorded, standing in for a weather forecast. Totals skip the {fmt(R.overview.missing_hours_pct, 1)}% of hours with a missing reading, so they are slight under-counts.</p>
          <p><strong className="text-foreground">Data:</strong> {R.dataset.name}, {R.dataset.period}, licence {R.dataset.license}. {R.dataset.citation}</p>
        </CardContent>
      </Card>
    </Section>
  );
}
