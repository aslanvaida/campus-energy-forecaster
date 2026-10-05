# Campus Energy Forecaster: web app

A Next.js + TypeScript + Tailwind + shadcn/ui site for the project. The page has three parts:

1. **The model:** a short description of how the forecaster works.
2. **Upload and split:** upload a labelled CSV (datathon columns), choose the training or test share in 10% steps from
   10% to 90%, and check that the two sets don't overlap.
3. **Train and test:** the two partitions are sent to the Python model API, which fits the final model
   (`BaggedBlendModel`, 3 bags) on the training rows only and scores it on the held-out test rows. The page shows a
   loading state with the current step while it trains (usually under a minute), then the results: RMSE / MAE / R²
   against the naive "usage = previous usage" rule, predicted vs actual, error by building, the largest errors, and a
   CSV of every test prediction.

## Run

The site needs the model API (`campus_energy_forecaster/api.py`) running. It calls `/api/model/*`, which Next.js
proxies to `MODEL_API_URL` (default `http://127.0.0.1:8000`).

```bash
# terminal 1, from the repo root
pip install -r requirements.txt
uvicorn campus_energy_forecaster.api:app --port 8000

# terminal 2
cd web
npm install
npm run dev     # http://localhost:3000
```

On macOS, XGBoost needs the OpenMP runtime: `brew install libomp`.

## How the split stays non-overlapping

`lib/split.ts`:
- Rows are keyed by the `id` column, or by the full row content when there is no `id`.
- Rows that share a key are kept together, so a duplicated row can never land in both sets.
- Keys are shuffled with a seeded PRNG (same seed gives the same split), then whole groups go to train until the target
  share is reached, and the rest go to test.

The page re-checks the result (shared keys = 0, train + test = total rows), and the API rejects a job whose train and
test files share any `id`.

## Structure

```
app/page.tsx                       Page: hero, model overview, workbench
components/model-overview.tsx      Short model description
components/workbench.tsx           Upload, split slider, overlap check, run + polling
components/results/                Loading state, results view, SVG charts
components/hero-vortex.tsx         Client-only wrapper for the 3D background
components/ui/                     shadcn components + vortex.tsx
components/ui/vortex-utils/        SceneContainer (r3f canvas) and useShadcnTheme (CSS vars -> THREE.Color)
lib/split.ts                       Seeded, group-aware train/test split
lib/model-api.ts                   Calls to the model API
```

shadcn's CLI installs components into `components/ui` (the `ui` alias in `components.json`), and `vortex.tsx` imports
its helpers from `@/components/ui/vortex-utils/`, so both must stay under that folder.
