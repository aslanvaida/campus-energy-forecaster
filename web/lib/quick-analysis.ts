import Papa from "papaparse";

/**
 * Quick analysis of an uploaded hourly meter file, done entirely in the browser (nothing is uploaded anywhere).
 * It uses a typical-week baseline (median and 90th percentile of each hour of the day, weekdays and weekends separately),
 * not the gradient-boosted forecasting model in the Python code. The same alert rule is used: a run of at least 3 hours above
 * the upper band plus one more band-width.
 */

export type Parsed = { columns: string[]; tsCol: string; valueCols: string[]; rows: Record<string, string>[] };
export type Point = { ms: number; hour: number; dow: number; day: string; kw: number };
export type Event = { start: string; hours: number; afterHours: boolean; meanExcessKw: number; excessKwh: number };

const TS = /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[T\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/;

/** Read a timestamp as written (no time-zone shift), as a UTC-based number so getUTC* returns the written clock time. */
export function parseStamp(s: string): number | null {
  const m = TS.exec((s ?? "").trim());
  if (m) return Date.UTC(+m[1], +m[2] - 1, +m[3], m[4] ? +m[4] : 0, m[5] ? +m[5] : 0, m[6] ? +m[6] : 0);
  return null;
}

export function parseCsv(text: string): Parsed {
  const res = Papa.parse<Record<string, string>>(text, { header: true, skipEmptyLines: true });
  const columns = res.meta.fields ?? [];
  const rows = res.data;
  if (columns.length < 2 || rows.length < 24) throw new Error("The file needs a header row, a timestamp column, a power column and at least 24 rows.");
  const sample = rows.slice(0, 50);
  const tsCol = columns.find((c) => sample.filter((r) => parseStamp(r[c]) !== null).length >= Math.min(20, sample.length) * 0.9);
  if (!tsCol) throw new Error("No timestamp column found. Timestamps should look like 2024-03-05 14:00 or 2024-03-05T14:00:00.");
  const valueCols = columns.filter((c) => c !== tsCol && sample.filter((r) => r[c] !== "" && !Number.isNaN(Number(r[c]))).length >= sample.length * 0.8);
  if (!valueCols.length) throw new Error("No numeric power column found.");
  return { columns, tsCol, valueCols, rows };
}

/** Average to hourly values, scaled to kW. `scale` is 1 for kW (or kWh per hour) and 0.001 for W. */
export function toHourly(p: Parsed, valueCol: string, scale: number): Point[] {
  const buckets = new Map<number, { sum: number; n: number }>();
  for (const r of p.rows) {
    const t = parseStamp(r[p.tsCol]);
    const v = Number(r[valueCol]);
    if (t === null || r[valueCol] === "" || Number.isNaN(v)) continue;
    const key = Math.floor(t / 3.6e6) * 3.6e6;
    const b = buckets.get(key) ?? { sum: 0, n: 0 };
    b.sum += v * scale;
    b.n += 1;
    buckets.set(key, b);
  }
  return [...buckets.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([ms, b]) => {
      const d = new Date(ms);
      return { ms, hour: d.getUTCHours(), dow: (d.getUTCDay() + 6) % 7, day: d.toISOString().slice(0, 10), kw: b.sum / b.n };
    });
}

const quantile = (sorted: number[], q: number) => {
  if (!sorted.length) return NaN;
  const i = (sorted.length - 1) * q;
  const lo = Math.floor(i), hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
};

export type Analysis = ReturnType<typeof analyze>;

export function analyze(pts: Point[], opts: { price: number; carbon: number }) {
  const weekend = (dow: number) => (dow >= 5 ? 1 : 0);
  const groups: number[][] = Array.from({ length: 48 }, () => []);
  for (const p of pts) groups[weekend(p.dow) * 24 + p.hour].push(p.kw);
  const p50 = groups.map((g) => quantile([...g].sort((a, b) => a - b), 0.5));
  const p90 = groups.map((g) => quantile([...g].sort((a, b) => a - b), 0.9));
  const thr = p90.map((hi, i) => hi + (hi - p50[i]));

  const isAfter = (p: Point) => p.hour < 7 || p.hour >= 19 || p.dow >= 5;
  const total = pts.reduce((s, p) => s + p.kw, 0);
  const after = pts.filter(isAfter).reduce((s, p) => s + p.kw, 0);

  // events: runs of >= 3 hours above the threshold, bridging single-hour gaps and missing hours of the same run
  const above = pts.map((p) => p.kw > thr[weekend(p.dow) * 24 + p.hour]);
  const flag = [...above];
  for (let i = 1; i < pts.length - 1; i++) if (!above[i] && above[i - 1] && above[i + 1] && pts[i + 1].ms - pts[i - 1].ms === 7.2e6) flag[i] = true;
  const events: Event[] = [];
  for (let i = 0; i < pts.length; ) {
    if (!flag[i]) { i++; continue; }
    let j = i;
    while (j + 1 < pts.length && flag[j + 1] && pts[j + 1].ms - pts[j].ms === 3.6e6) j++;
    const seg = pts.slice(i, j + 1);
    if (seg.length >= 3) {
      const kwh = seg.reduce((s, p) => s + Math.max(0, p.kw - p50[weekend(p.dow) * 24 + p.hour]), 0);
      events.push({ start: new Date(seg[0].ms).toISOString().slice(0, 16).replace("T", " "), hours: seg.length,
        afterHours: seg.filter(isAfter).length / seg.length > 0.5, meanExcessKw: kwh / seg.length, excessKwh: kwh });
    }
    i = j + 1;
  }
  events.sort((a, b) => b.excessKwh - a.excessKwh);
  const excessKwh = events.reduce((s, e) => s + e.excessKwh, 0);

  // daily peaks
  const byDay = new Map<string, Point>();
  for (const p of pts) { const b = byDay.get(p.day); if (!b || p.kw > b.kw) byDay.set(p.day, p); }
  const days = [...byDay.values()].sort((a, b) => b.kw - a.kw);

  // weekly profile (median by weekday and hour) for the outage calculator
  const weekly = Array.from({ length: 7 }, (_, d) => Array.from({ length: 24 }, (_, h) => {
    const g = pts.filter((p) => p.dow === d && p.hour === h).map((p) => p.kw).sort((a, b) => a - b);
    return quantile(g, 0.5);
  }));

  const nDays = new Set(pts.map((p) => p.day)).size;
  return {
    hours: pts.length, days: nDays, meanKw: total / pts.length, peakKw: days[0]?.kw ?? 0, peakAt: days[0] ? `${days[0].day} ${days[0].hour}:00` : "",
    afterHoursSharePct: (100 * after) / total, events, excessKwh, excessCost: excessKwh * opts.price, excessCo2Kg: excessKwh * opts.carbon,
    topDays: days.slice(0, 5).map((p) => ({ day: p.day, kw: p.kw, hour: p.hour })), weekly,
    annualKwh: (total / pts.length) * 8760,
  };
}

/** Hours a battery lasts when serving the typical week from (dow, hour), with `shedPct` of the load switched off. Capped at 14 days. */
export function outageRuntime(weekly: number[][], dow: number, hour: number, capacityKwh: number, shedPct: number, usable = 0.9, eff = 0.92) {
  let left = capacityKwh * usable * eff;
  for (let i = 0; i < 24 * 14; i++) {
    const t = hour + i;
    const kw = weekly[(dow + Math.floor(t / 24)) % 7][t % 24] * (1 - shedPct / 100);
    if (Number.isNaN(kw)) return NaN;
    if (kw >= left) return i + left / kw;
    left -= kw;
  }
  return 24 * 14;
}
