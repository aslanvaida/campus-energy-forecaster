import { Blend, Building2, Layers, PuzzleIcon } from "lucide-react";

const PARTS = [
  {
    icon: PuzzleIcon,
    title: "Fills missing values",
    body: "Gaps in temperature, humidity, occupancy or the previous reading are predicted by small tree models from the building, hour, weekday and the other inputs. Rows are never dropped.",
  },
  {
    icon: Building2,
    title: "Linear core, per building (85%)",
    body: "A ridge regression with building-specific slopes where buildings really differ (occupancy, temperature, daily cycle, weekend) and shared ones where they don't.",
  },
  {
    icon: Blend,
    title: "Tree hedge (15%)",
    body: "Three XGBoost models pick up non-linear effects. Their average is blended in with a small weight.",
  },
  {
    icon: Layers,
    title: "Robust to gaps",
    body: "Each part trains on extra copies of the data with random gaps, and three such models (bags) are averaged.",
  },
];

export function ModelOverview() {
  return (
    <section aria-labelledby="model-heading" className="flex flex-col gap-5">
      <div className="max-w-3xl">
        <h2 id="model-heading" className="text-2xl font-semibold tracking-tight">The model</h2>
        <p className="mt-2 text-muted-foreground text-pretty">
          It predicts a campus building&apos;s hourly <span className="text-foreground">energy usage</span> from its previous
          reading, occupancy, weather, time and building. On the NTU Datathon 2026 data it scores RMSE about 3.07 and R² 0.97
          in 5-fold cross-validation, roughly half the error of the naive rule &ldquo;usage = previous usage&rdquo;.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {PARTS.map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-xl border bg-card p-4">
            <Icon className="size-5 text-primary" aria-hidden />
            <h3 className="mt-3 font-medium">{title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
