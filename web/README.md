# Dashboard

A static Next.js + TypeScript + Tailwind page for the energy tool. It has no backend and trains nothing: every figure it
shows is read from `public/data/results.json`, which `scripts/run_analysis.py` writes from the Python code in the repo root.

An animated hero sits at the top. Sections: headline numbers, waste alerts, the quiet-hours opportunity, next-day forecast with its uncertainty band, the
emergency power planner (outage start, battery size and the loads that must stay on are selectable), a check on schools and healthcare buildings, an in-browser CSV upload (`lib/quick-analysis.ts`: a typical-week baseline, runs in the browser, the file is not uploaded), and a page on how far to trust each result.

```bash
cd web
npm install
npm run dev      # http://localhost:3000
npm run build    # static build
npm run lint
```

To refresh the numbers, run the Python analysis from the repo root (see the main README), then reload.

```
app/page.tsx                 Page header with two buttons (analyze your own data / see the demo)
components/app-shell.tsx     Sticky tab bar: demo building, and "Analyze your own data" (the upload view, linkable as #upload)
components/dashboard.tsx     Sections (alerts, quiet hours, forecast, outage planner, trust)
components/band-chart.tsx    SVG chart: actual load against the forecast band
components/ui/               Card, table, badge and related primitives
lib/results.ts               Types for results.json and number formatting
lib/quick-analysis.ts        CSV parsing and the quick baseline analysis used by the upload section
components/upload-analysis.tsx  The upload section
components/hero-vortex.tsx   Animated particle background (three.js)
public/data/results.json     Generated, committed so the dashboard runs without the dataset
```
