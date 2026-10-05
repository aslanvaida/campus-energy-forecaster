# Campus Energy Forecaster: web app

A Next.js + TypeScript + Tailwind + shadcn/ui site for the project.

**Train / test splitter** (`/`): upload a CSV, choose the training (or test) share in 10% steps from 10% to 90%,
and download two non-overlapping CSVs. Everything runs in the browser and the file is never sent to a server.

How the split stays non-overlapping (`lib/split.ts`):
- Rows are keyed by the `id` column, or by the full row content when there is no `id`.
- Rows that share a key are kept together, so a duplicated row can never land in both sets.
- Keys are shuffled with a seeded PRNG (same seed gives the same split), then whole groups go to train until the
  target share is reached, and the rest go to test.
- The page re-checks the result: shared keys = 0 and train + test = total rows.

## Run

```bash
npm install
npm run dev     # http://localhost:3000
```

## Structure

```
app/page.tsx                    Page (hero + splitter)
components/dataset-splitter.tsx Upload, slider, overlap check, preview, download
components/hero-vortex.tsx      Client-only wrapper for the 3D background
components/ui/                  shadcn components + vortex.tsx
components/ui/vortex-utils/     SceneContainer (r3f canvas) and useShadcnTheme (CSS vars -> THREE.Color)
lib/split.ts                    Seeded, group-aware train/test split
```

shadcn's CLI installs components into `components/ui` (the `ui` alias in `components.json`), and `vortex.tsx`
imports its helpers from `@/components/ui/vortex-utils/`, so both must stay under that folder.
