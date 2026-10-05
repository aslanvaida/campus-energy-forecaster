"use client";

import * as React from "react";

import { niceTicks, useWidth } from "@/components/results/use-width";

type Props = { actual: number[]; predicted: number[]; buildingId: string[] };

const HEIGHT = 340;
const M = { top: 12, right: 16, bottom: 40, left: 48 };
const fmt = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 1 });

/** Predicted vs actual on the test set; points on the diagonal are perfect predictions. */
export function ScatterChart({ actual, predicted, buildingId }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = React.useState<number | null>(null);

  const ticks = React.useMemo(() => {
    const all = [...actual, ...predicted];
    return niceTicks(Math.min(...all), Math.max(...all));
  }, [actual, predicted]);
  const lo = ticks[0], hi = ticks[ticks.length - 1];

  const innerW = Math.max(0, width - M.left - M.right);
  const innerH = HEIGHT - M.top - M.bottom;
  const x = (v: number) => M.left + ((v - lo) / (hi - lo)) * innerW;
  const y = (v: number) => M.top + innerH - ((v - lo) / (hi - lo)) * innerH;

  // Nearest point to the pointer (within 24px), so tiny dots are easy to hover.
  function onMove(e: React.PointerEvent<SVGRectElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - box.left + M.left, py = e.clientY - box.top + M.top;
    let best = -1, bestD = 24 * 24;
    for (let i = 0; i < actual.length; i++) {
      const dx = x(actual[i]) - px, dy = y(predicted[i]) - py, d = dx * dx + dy * dy;
      if (d < bestD) { bestD = d; best = i; }
    }
    setHover(best >= 0 ? best : null);
  }

  return (
    <div ref={ref} className="relative w-full">
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label={`Predicted versus actual energy usage for ${actual.length} test rows`}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={M.left} x2={M.left + innerW} y1={y(t)} y2={y(t)} className="stroke-border" strokeWidth={1} />
              <line x1={x(t)} x2={x(t)} y1={M.top} y2={M.top + innerH} className="stroke-border" strokeWidth={1} />
              <text x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted-foreground text-[11px] tabular-nums">{fmt(t)}</text>
              <text x={x(t)} y={M.top + innerH + 18} textAnchor="middle" className="fill-muted-foreground text-[11px] tabular-nums">{fmt(t)}</text>
            </g>
          ))}
          {/* perfect-prediction diagonal */}
          <line x1={x(lo)} y1={y(lo)} x2={x(hi)} y2={y(hi)} className="stroke-muted-foreground" strokeWidth={1} />
          <text x={x(hi) - 4} y={y(hi) + 14} textAnchor="end" className="fill-muted-foreground text-[11px]">predicted = actual</text>

          <g fill="var(--series-1)" fillOpacity={0.55}>
            {actual.map((a, i) => (
              <circle key={i} cx={x(a)} cy={y(predicted[i])} r={2.5} />
            ))}
          </g>
          {hover !== null && (
            <circle cx={x(actual[hover])} cy={y(predicted[hover])} r={5} fill="var(--series-1)" stroke="var(--card-solid)" strokeWidth={2} />
          )}

          <text x={M.left + innerW / 2} y={HEIGHT - 4} textAnchor="middle" className="fill-muted-foreground text-xs">Actual usage</text>
          <text transform={`translate(12 ${M.top + innerH / 2}) rotate(-90)`} textAnchor="middle" className="fill-muted-foreground text-xs">Predicted usage</text>

          <rect
            x={M.left} y={M.top} width={innerW} height={innerH} fill="transparent"
            onPointerMove={onMove} onPointerLeave={() => setHover(null)}
          />
        </svg>
      )}
      {hover !== null && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border bg-popover px-3 py-2 text-xs shadow-md"
          style={{
            left: Math.min(x(actual[hover]) + 12, width - 150),
            top: Math.max(0, y(predicted[hover]) - 64),
          }}
        >
          <p className="mb-1 text-muted-foreground">{buildingId[hover]}</p>
          <p><span className="font-semibold tabular-nums">{fmt(predicted[hover])}</span> <span className="text-muted-foreground">predicted</span></p>
          <p><span className="font-semibold tabular-nums">{fmt(actual[hover])}</span> <span className="text-muted-foreground">actual</span></p>
        </div>
      )}
    </div>
  );
}
