"use client";

import * as React from "react";

import { niceTicks, useWidth } from "@/components/results/use-width";
import type { BuildingScore } from "@/lib/model-api";

const BAR = 18, GAP = 10;
const M = { top: 4, right: 48, bottom: 28, left: 72 };

/** Test RMSE per building, lowest first. */
export function BuildingBars({ data, overall }: { data: BuildingScore[]; overall: number }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = React.useState<number | null>(null);

  const ticks = niceTicks(0, Math.max(...data.map((d) => d.rmse), overall), 4);
  const max = ticks[ticks.length - 1];
  const innerW = Math.max(0, width - M.left - M.right);
  const height = M.top + data.length * (BAR + GAP) + M.bottom;
  const x = (v: number) => M.left + (v / max) * innerW;
  const rowY = (i: number) => M.top + i * (BAR + GAP);

  return (
    <div ref={ref} className="relative w-full">
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Test RMSE by building">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={x(t)} x2={x(t)} y1={M.top} y2={height - M.bottom} className="stroke-border" strokeWidth={1} />
              <text x={x(t)} y={height - 8} textAnchor="middle" className="fill-muted-foreground text-[11px] tabular-nums">{t}</text>
            </g>
          ))}
          {data.map((d, i) => {
            const w = Math.max(0, x(d.rmse) - M.left);
            const r = Math.min(4, w / 2);
            const y0 = rowY(i);
            return (
              <g
                key={d.building_id}
                tabIndex={0}
                aria-label={`${d.building_id}: RMSE ${d.rmse.toFixed(2)}`}
                onPointerEnter={() => setHover(i)}
                onPointerLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                className="outline-none"
              >
                <rect x={0} y={y0 - GAP / 2} width={width} height={BAR + GAP} fill="transparent" />
                <text x={M.left - 8} y={y0 + BAR / 2} dy="0.32em" textAnchor="end" className="fill-foreground text-xs">{d.building_id}</text>
                {/* square at the baseline, 4px rounded data-end */}
                <path
                  d={`M${M.left},${y0} h${w - r} a${r},${r} 0 0 1 ${r},${r} v${BAR - 2 * r} a${r},${r} 0 0 1 ${-r},${r} h${-(w - r)} z`}
                  fill="var(--series-1)"
                  fillOpacity={hover === null || hover === i ? 1 : 0.45}
                />
                <text x={x(d.rmse) + 6} y={y0 + BAR / 2} dy="0.32em" className="fill-muted-foreground text-[11px] tabular-nums">{d.rmse.toFixed(2)}</text>
              </g>
            );
          })}
          {/* overall test RMSE for reference */}
          <line x1={x(overall)} x2={x(overall)} y1={M.top - 2} y2={height - M.bottom} className="stroke-foreground" strokeWidth={1} />
        </svg>
      )}
      {hover !== null && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border bg-popover px-3 py-2 text-xs shadow-md"
          style={{ left: Math.min(x(data[hover].rmse) + 44, width - 170), top: rowY(hover) - 8 }}
        >
          <p className="mb-1 text-muted-foreground">{data[hover].building_id} · {data[hover].building_type}</p>
          <p><span className="font-semibold tabular-nums">{data[hover].rmse.toFixed(2)}</span> <span className="text-muted-foreground">RMSE</span></p>
          <p><span className="font-semibold tabular-nums">{data[hover].mae.toFixed(2)}</span> <span className="text-muted-foreground">MAE</span></p>
          <p><span className="font-semibold tabular-nums">{data[hover].n}</span> <span className="text-muted-foreground">test rows</span></p>
        </div>
      )}
    </div>
  );
}
