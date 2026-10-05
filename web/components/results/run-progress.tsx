"use client";

import * as React from "react";
import { Check, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

const STEPS = [
  { key: "Preparing", label: "Send split to the model server" },
  { key: "bag 1", label: "Train bag 1 of 3" },
  { key: "bag 2", label: "Train bag 2 of 3" },
  { key: "bag 3", label: "Train bag 3 of 3" },
  { key: "Predicting", label: "Predict the test set" },
  { key: "Scoring", label: "Score against the true values" },
];

/** Loading state while the model trains: spinner, current stage, step list and elapsed time. */
export function RunProgress({ stage, progress, startedAt, nTrain, nTest }: {
  stage: string; progress: number; startedAt: number; nTrain: number; nTest: number;
}) {
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);

  const current = Math.max(0, STEPS.findIndex((s) => stage.includes(s.key)));
  const elapsed = Math.max(0, Math.round((now - startedAt) / 1000));

  return (
    <div className="flex flex-col items-center gap-6 py-6 text-center" role="status" aria-live="polite">
      <Loader2 className="size-10 animate-spin text-primary motion-reduce:animate-none" aria-hidden />
      <div>
        <p className="text-lg font-medium">{stage}…</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Training on {nTrain.toLocaleString("en-US")} rows, testing on {nTest.toLocaleString("en-US")} rows · {elapsed}s elapsed (usually under a minute)
        </p>
      </div>
      <div className="h-1.5 w-full max-w-md overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${Math.round(progress * 100)}%` }} />
      </div>
      <ol className="grid w-full max-w-md gap-2 text-left text-sm">
        {STEPS.map((s, i) => (
          <li key={s.key} className={cn("flex items-center gap-2", i > current && "text-muted-foreground")}>
            {i < current ? (
              <Check className="size-4 text-[var(--ok)]" aria-label="done" />
            ) : i === current ? (
              <Loader2 className="size-4 animate-spin text-primary motion-reduce:animate-none" aria-label="in progress" />
            ) : (
              <span className="size-4 rounded-full border" aria-hidden />
            )}
            {s.label}
          </li>
        ))}
      </ol>
    </div>
  );
}
