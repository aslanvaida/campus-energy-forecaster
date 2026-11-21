"use client";

import * as React from "react";

type Series = { actual: (number | null)[]; lo: (number | null)[]; mid: (number | null)[]; hi: (number | null)[] };

/** Hourly actual load against the day-ahead forecast and its uncertainty band (plain SVG). */
export function BandChart({ hours, series, unit = "kW" }: { hours: string[]; series: Series; unit?: string }) {
  const W = 860, H = 280, L = 44, R = 12, T = 12, B = 28;
  const n = hours.length;
  const vals = [...series.actual, ...series.hi].filter((v): v is number => v != null);
  const max = Math.max(1, ...vals) * 1.05;
  const x = (i: number) => L + (i / (n - 1)) * (W - L - R);
  const y = (v: number) => T + (1 - v / max) * (H - T - B);

  const line = (arr: (number | null)[]) => {
    let d = "";
    arr.forEach((v, i) => {
      if (v == null) return;
      d += `${d && arr[i - 1] != null ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    });
    return d;
  };
  const bandPts = series.hi.map((v, i) => (v != null && series.lo[i] != null ? i : -1)).filter((i) => i >= 0);
  const band =
    bandPts.length > 1
      ? `M${bandPts.map((i) => `${x(i).toFixed(1)},${y(series.hi[i]!).toFixed(1)}`).join("L")}L${[...bandPts]
          .reverse()
          .map((i) => `${x(i).toFixed(1)},${y(series.lo[i]!).toFixed(1)}`)
          .join("L")}Z`
      : "";
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * max);
  const dayIdx = hours.map((h, i) => (h.slice(11, 13) === "00" ? i : -1)).filter((i) => i >= 0);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Actual load versus forecast band">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="currentColor" strokeOpacity={0.1} />
          <text x={L - 6} y={y(t) + 4} textAnchor="end" fontSize={11} fill="currentColor" fillOpacity={0.6}>
            {Math.round(t)}
          </text>
        </g>
      ))}
      {dayIdx.map((i, k) =>
        k % 2 === 0 ? (
          <text key={i} x={x(i)} y={H - 8} fontSize={11} fill="currentColor" fillOpacity={0.6}>
            {new Date(hours[i].replace(" ", "T")).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          </text>
        ) : null,
      )}
      <path d={band} fill="var(--test)" fillOpacity={0.22} />
      <path d={line(series.mid)} fill="none" stroke="var(--test)" strokeWidth={1.4} strokeDasharray="4 3" />
      <path d={line(series.actual)} fill="none" stroke="var(--primary)" strokeWidth={1.8} />
      <text x={L} y={10} fontSize={11} fill="currentColor" fillOpacity={0.6}>
        {unit}
      </text>
    </svg>
  );
}
