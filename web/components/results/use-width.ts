"use client";

import * as React from "react";

/** Track an element's content width so SVG charts can draw at real pixel size (crisp text, no scaling). */
export function useWidth<T extends HTMLElement>() {
  const ref = React.useRef<T>(null);
  const [width, setWidth] = React.useState(0);
  React.useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}

/** Clean axis ticks (1, 2, 2.5, 5 x 10^k steps) covering [min, max]. */
export function niceTicks(min: number, max: number, count = 5) {
  const span = max - min || 1;
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= end + step / 2; v += step) ticks.push(+v.toFixed(10));
  return ticks;
}
