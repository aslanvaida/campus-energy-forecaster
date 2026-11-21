"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { analyze, outageRuntime, parseCsv, toHourly, type Parsed } from "@/lib/quick-analysis";
import { fmt, hoursText, results as R, usd } from "@/lib/results";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const field = "rounded-md border bg-background px-2 py-1 text-sm";

export function UploadAnalysis() {
  const [text, setText] = React.useState<string | null>(null);
  const [name, setName] = React.useState("");
  const [error, setError] = React.useState("");
  const [col, setCol] = React.useState("");
  const [unit, setUnit] = React.useState("1");
  const [price, setPrice] = React.useState(String(R.assumptions.tariff_usd_per_kwh));
  const [carbon, setCarbon] = React.useState(String(R.assumptions.carbon_kg_per_kwh));
  const [cap, setCap] = React.useState("250");
  const [shed, setShed] = React.useState(0);
  const [dow, setDow] = React.useState(2);
  const [hour, setHour] = React.useState(9);

  const parsed = React.useMemo<Parsed | null>(() => {
    if (text === null) return null;
    try {
      return parseCsv(text);
    } catch {
      return null;
    }
  }, [text]);

  const activeCol = parsed ? (parsed.valueCols.includes(col) ? col : (parsed.valueCols.find((c) => /kw|power|load|energy|total|usage/i.test(c)) ?? parsed.valueCols[0])) : "";

  const analysis = React.useMemo(() => {
    if (!parsed || !activeCol) return null;
    const pts = toHourly(parsed, activeCol, Number(unit));
    if (pts.length < 48) return null;
    return analyze(pts, { price: Number(price) || 0, carbon: Number(carbon) || 0 });
  }, [parsed, activeCol, unit, price, carbon]);

  const load = (t: string, n: string) => {
    try {
      parseCsv(t);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the file.");
    }
    setText(t);
    setName(n);
  };

  const onFile = async (f: File | undefined) => {
    if (f) load(await f.text(), f.name);
  };

  const useSample = async () => {
    const r = await fetch(`${BASE}/data/sample_hourly_kw.csv`);
    load(await r.text(), "sample_hourly_kw.csv (the demo building, 2019)");
  };

  const runtime = analysis ? outageRuntime(analysis.weekly, dow, hour, Number(cap) || 0, shed) : NaN;
  const runtimeAll = analysis ? outageRuntime(analysis.weekly, dow, hour, Number(cap) || 0, 0) : NaN;

  return (
    <section id="upload-panel" aria-labelledby="upload-heading" className="flex flex-col gap-4">
      <div>
        <h2 id="upload-heading" className="text-2xl font-semibold tracking-tight">Try it on your own meter data</h2>
        <p className="mt-1 max-w-3xl text-muted-foreground text-pretty">
          Upload a CSV with a timestamp column and a power column (kW). This is a quick look that runs in your browser and never uploads the file: it learns a typical week
          from your data and flags runs of unusual hours. The full forecasting model, with weather and uncertainty bands, is the Python code in the repository.
        </p>
      </div>
      <Card>
        <CardHeader className="gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <label className="cursor-pointer rounded-md border bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground">
              Choose a CSV file
              <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => onFile(e.target.files?.[0])} />
            </label>
            <button type="button" onClick={useSample} className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted">Use the sample file</button>
            <a href={`${BASE}/data/sample_hourly_kw.csv`} download className="text-sm underline underline-offset-4">Download the sample</a>
            {name && <Badge variant="secondary">{name}</Badge>}
          </div>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          {parsed && (
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <label className="flex items-center gap-1.5">Power column
                <select value={activeCol} onChange={(e) => setCol(e.target.value)} className={field}>{parsed.valueCols.map((c) => <option key={c}>{c}</option>)}</select>
              </label>
              <label className="flex items-center gap-1.5">Unit
                <select value={unit} onChange={(e) => setUnit(e.target.value)} className={field}><option value="1">kW (or kWh per hour)</option><option value="0.001">W</option></select>
              </label>
              <label className="flex items-center gap-1.5">Price $/kWh<input value={price} onChange={(e) => setPrice(e.target.value)} className={`${field} w-20`} inputMode="decimal" /></label>
              <label className="flex items-center gap-1.5">kg CO₂/kWh<input value={carbon} onChange={(e) => setCarbon(e.target.value)} className={`${field} w-20`} inputMode="decimal" /></label>
            </div>
          )}
          <CardDescription>Needs hourly or finer readings, ideally four weeks or more. Prices default to the values used for the demo building.</CardDescription>
        </CardHeader>
        {analysis && (
          <CardContent className="flex flex-col gap-5">
            {analysis.days < 28 && <p className="text-sm text-destructive">Only {analysis.days} days of data: the typical week is a rough guess, so treat the alerts with care.</p>}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Average load", `${fmt(analysis.meanKw, 1)} kW`, `about ${fmt(analysis.annualKwh / 1000)} MWh a year, ${usd((analysis.annualKwh * Number(price)) || 0)}`],
                ["Highest hour", `${fmt(analysis.peakKw, 1)} kW`, analysis.peakAt],
                ["Used after hours", `${fmt(analysis.afterHoursSharePct)}%`, "nights, weekends (before 7 am, from 7 pm)"],
                ["Unusual runs", `${analysis.events.length}`, `${fmt(analysis.excessKwh)} kWh above typical, ${usd(analysis.excessCost)}, ${fmt(analysis.excessCo2Kg)} kg CO₂`],
              ].map(([l, v, s]) => (
                <Card size="sm" key={l}>
                  <CardHeader><CardDescription>{l}</CardDescription><CardTitle className="text-2xl tabular-nums">{v}</CardTitle></CardHeader>
                  <CardContent className="text-sm text-muted-foreground">{s}</CardContent>
                </Card>
              ))}
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-medium">Largest unusual runs</p>
                {analysis.events.length === 0 ? <p className="text-sm text-muted-foreground">None found with this rule.</p> : (
                  <Table>
                    <TableHeader><TableRow><TableHead>Started</TableHead><TableHead className="text-right">Hours</TableHead><TableHead className="text-right">Extra</TableHead><TableHead className="text-right">Cost</TableHead><TableHead>When</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {analysis.events.slice(0, 8).map((e) => (
                        <TableRow key={e.start}>
                          <TableCell>{e.start}</TableCell>
                          <TableCell className="text-right tabular-nums">{e.hours}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmt(e.excessKwh)} kWh</TableCell>
                          <TableCell className="text-right tabular-nums">{usd(e.excessKwh * Number(price))}</TableCell>
                          <TableCell><Badge variant={e.afterHours ? "default" : "secondary"}>{e.afterHours ? "After hours" : "Occupied"}</Badge></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
              <div>
                <p className="mb-2 text-sm font-medium">Highest-peak days</p>
                <Table>
                  <TableHeader><TableRow><TableHead>Day</TableHead><TableHead className="text-right">Peak</TableHead><TableHead className="text-right">At</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {analysis.topDays.map((d) => (
                      <TableRow key={d.day}><TableCell>{d.day}</TableCell><TableCell className="text-right tabular-nums">{fmt(d.kw, 1)} kW</TableCell><TableCell className="text-right tabular-nums">{d.hour}:00</TableCell></TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium">If the grid fails: how long does your backup last?</p>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <label className="flex items-center gap-1.5">Battery kWh<input value={cap} onChange={(e) => setCap(e.target.value)} className={`${field} w-24`} inputMode="decimal" /></label>
                <label className="flex items-center gap-1.5">Starts on
                  <select value={dow} onChange={(e) => setDow(Number(e.target.value))} className={field}>{DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select>
                  at
                  <select value={hour} onChange={(e) => setHour(Number(e.target.value))} className={field}>{Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{h}:00</option>)}</select>
                </label>
                <label className="flex items-center gap-1.5">Switch off
                  <select value={shed} onChange={(e) => setShed(Number(e.target.value))} className={field}>{[0, 25, 50, 75].map((s) => <option key={s} value={s}>{s}% of the load</option>)}</select>
                </label>
              </div>
              <p className="mt-2 text-lg font-semibold tabular-nums">
                {Number.isNaN(runtime) ? "Not enough data for that hour" : hoursText(runtime)}
                {shed > 0 && !Number.isNaN(runtimeAll) && <span className="ml-2 text-sm font-normal text-muted-foreground">against {hoursText(runtimeAll)} with everything on</span>}
              </p>
              <p className="text-xs text-muted-foreground">Uses your typical week for that day and hour, 90% usable battery and 92% efficiency. Runtimes cap at 14 days.</p>
            </div>
          </CardContent>
        )}
      </Card>
    </section>
  );
}
