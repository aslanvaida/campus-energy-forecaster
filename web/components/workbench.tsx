"use client";

import * as React from "react";
import Papa from "papaparse";
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Play, RotateCcw, Shuffle, Upload, X } from "lucide-react";

import { ResultsView } from "@/components/results/results-view";
import { RunProgress } from "@/components/results/run-progress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getJob, REQUIRED_COLUMNS, startJob, type RunResult } from "@/lib/model-api";
import { splitRows, type Row } from "@/lib/split";
import { cn } from "@/lib/utils";

type Dataset = { name: string; size: number; fields: string[]; rows: Row[] };
type Mode = "train" | "test";
type RunConfig = { file: string; trainPct: number; seed: number };
type Run =
  | { state: "idle" }
  | { state: "running"; config: RunConfig; stage: string; progress: number; startedAt: number; nTrain: number; nTest: number }
  | { state: "done"; config: RunConfig; result: RunResult }
  | { state: "error"; config: RunConfig; message: string };

const STEPS = [10, 20, 30, 40, 50, 60, 70, 80, 90];
const POLL_MS = 1000;
const fmt = new Intl.NumberFormat("en-US");

function formatBytes(n: number) {
  return n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function Workbench() {
  const [data, setData] = React.useState<Dataset | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [mode, setMode] = React.useState<Mode>("train");
  const [pct, setPct] = React.useState(80);
  const [seed, setSeed] = React.useState(42);
  const [run, setRun] = React.useState<Run>({ state: "idle" });
  const inputRef = React.useRef<HTMLInputElement>(null);
  const resultsRef = React.useRef<HTMLDivElement>(null);
  const pollRef = React.useRef<AbortController | null>(null);

  const trainPct = mode === "train" ? pct : 100 - pct;
  const split = React.useMemo(
    () => (data ? splitRows(data.rows, data.fields, trainPct / 100, seed) : null),
    [data, trainPct, seed],
  );
  const missing = data ? REQUIRED_COLUMNS.filter((c) => !data.fields.includes(c)) : [];
  const running = run.state === "running";
  const config: RunConfig | null = data ? { file: data.name, trainPct, seed } : null;
  const stale = run.state !== "idle" && config !== null &&
    (run.config.file !== config.file || run.config.trainPct !== config.trainPct || run.config.seed !== config.seed);

  React.useEffect(() => () => pollRef.current?.abort(), []);

  function load(file: File) {
    setError(null);
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please upload a .csv file.");
      return;
    }
    Papa.parse<Row>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => {
        const fields = res.meta.fields ?? [];
        if (!fields.length || res.data.length < 2) {
          setError("That file needs a header row and at least 2 data rows.");
          return;
        }
        setData({ name: file.name, size: file.size, fields, rows: res.data });
      },
      error: (err) => setError(`Could not read the file: ${err.message}`),
    });
  }

  async function trainAndTest() {
    if (!data || !split || !config) return;
    pollRef.current?.abort();
    const ctrl = new AbortController();
    pollRef.current = ctrl;
    const base = { config, startedAt: Date.now(), nTrain: split.train.length, nTest: split.test.length };
    setRun({ state: "running", stage: "Preparing data", progress: 0.02, ...base });
    requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    try {
      const id = await startJob(split.train, split.test, data.fields);
      while (!ctrl.signal.aborted) {
        const job = await getJob(id, ctrl.signal);
        if (job.status === "done" && job.result) {
          setRun({ state: "done", config, result: job.result });
          return;
        }
        if (job.status === "error") throw new Error(job.error ?? "Training failed.");
        setRun({ state: "running", stage: job.stage, progress: job.progress, ...base });
        await new Promise((r) => setTimeout(r, POLL_MS));
      }
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setRun({ state: "error", config, message: e instanceof Error ? e.message : String(e) });
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && !running) load(file);
  }

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Upload */}
      <Card>
        <CardHeader>
          <CardTitle>1. Upload your dataset</CardTitle>
          <CardDescription>
            A labelled CSV with the datathon columns: {REQUIRED_COLUMNS.join(", ")}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data ? (
            <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 p-4">
              <FileSpreadsheet className="size-8 shrink-0 text-primary" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{data.name}</p>
                <p className="text-sm text-muted-foreground">
                  {fmt.format(data.rows.length)} rows · {data.fields.length} columns · {formatBytes(data.size)}
                </p>
              </div>
              <Button variant="outline" disabled={running} onClick={() => inputRef.current?.click()}>
                <Upload data-icon="inline-start" /> Replace
              </Button>
              <Button variant="ghost" size="icon" aria-label="Remove dataset" disabled={running} onClick={() => setData(null)}>
                <X />
              </Button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={cn(
                "flex w-full flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 text-center transition-colors",
                "hover:border-primary/60 hover:bg-muted/30 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                dragging && "border-primary bg-primary/5",
              )}
            >
              <Upload className="size-8 text-muted-foreground" aria-hidden />
              <span className="font-medium">Drop a CSV here or click to browse</span>
              <span className="text-sm text-muted-foreground">e.g. Track 1 Training Dataset.csv</span>
            </button>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) load(file);
              e.target.value = "";
            }}
          />
          {error && <p role="alert" className="mt-3 text-sm text-destructive">{error}</p>}
          {missing.length > 0 && (
            <p role="alert" className="mt-3 flex items-start gap-2 text-sm text-destructive">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
              This file is missing columns the model needs: {missing.join(", ")}.
            </p>
          )}
        </CardContent>
      </Card>

      {/* 2. Split + run */}
      <Card className={cn(!data && "pointer-events-none opacity-50")} aria-disabled={!data}>
        <CardHeader>
          <CardTitle>2. Choose the split and run</CardTitle>
          <CardDescription>
            Rows are shuffled with a fixed seed and divided so no row is in both sets. The model trains on the
            training set only and is then scored on the held-out test set.
          </CardDescription>
        </CardHeader>
        <CardContent className={cn("flex flex-col gap-6", running && "pointer-events-none opacity-60")}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Tabs
              value={mode}
              onValueChange={(v) => {
                const next = v as Mode;
                if (next !== mode) {
                  setMode(next);
                  setPct(100 - pct); // same split, expressed from the other side
                }
              }}
            >
              <TabsList>
                <TabsTrigger value="train">Set training %</TabsTrigger>
                <TabsTrigger value="test">Set test %</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Seed <span className="font-mono text-foreground tabular-nums">{seed}</span></span>
              <Button variant="outline" size="sm" onClick={() => setSeed(Math.floor(Math.random() * 1_000_000))}>
                <Shuffle data-icon="inline-start" /> Reshuffle
              </Button>
            </div>
          </div>

          <div>
            <div className="mb-3 flex items-baseline justify-between">
              <label id="split-label" className="text-sm font-medium">
                {mode === "train" ? "Training" : "Test"} portion
              </label>
              <span className="text-2xl font-semibold">{pct}%</span>
            </div>
            <Slider
              aria-labelledby="split-label"
              min={10}
              max={90}
              step={10}
              value={[pct]}
              disabled={running}
              onValueChange={(v) => setPct(Array.isArray(v) ? v[0] : v)}
            />
            <div className="mt-2 flex justify-between text-xs text-muted-foreground tabular-nums" aria-hidden>
              {STEPS.map((s) => (
                <span key={s} className={cn("w-8 text-center", s === pct && "font-semibold text-foreground")}>{s}</span>
              ))}
            </div>
          </div>

          <div className="flex h-9 gap-0.5 overflow-hidden rounded-md text-xs font-medium">
            <div
              className="flex items-center justify-center rounded-l-md bg-[var(--train)] text-[var(--train-foreground)] transition-[width] duration-300"
              style={{ width: `${trainPct}%` }}
            >
              Train {trainPct}%{split && ` · ${fmt.format(split.train.length)} rows`}
            </div>
            <div
              className="flex items-center justify-center rounded-r-md bg-[var(--test)] text-[var(--test-foreground)] transition-[width] duration-300"
              style={{ width: `${100 - trainPct}%` }}
            >
              Test {100 - trainPct}%{split && ` · ${fmt.format(split.test.length)} rows`}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            {split && data ? (
              split.shared.length === 0 && split.train.length + split.test.length === data.rows.length ? (
                <p className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="size-4 text-[var(--ok)]" aria-hidden />
                  <span>
                    No overlap: 0 shared {split.keyedBy === "id" ? "ids" : "rows"}, every row used once
                    {split.duplicateRows > 0 && ` (${split.duplicateRows} duplicate rows kept together)`}
                  </span>
                </p>
              ) : (
                <p className="text-sm text-destructive">{split.shared.length} rows are in both sets.</p>
              )
            ) : <span />}
            <Button size="lg" disabled={!data || missing.length > 0 || running} onClick={trainAndTest}>
              <Play data-icon="inline-start" /> {run.state === "idle" ? "Train and test" : "Run again"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 3. Results */}
      <div ref={resultsRef} className="scroll-mt-6">
        {run.state !== "idle" && (
          <Card>
            <CardHeader>
              <CardTitle>3. Results on the test set</CardTitle>
              <CardDescription>
                {run.state === "done"
                  ? `Trained on ${fmt.format(run.result.n_train)} rows (${run.config.trainPct}%) and tested on ${fmt.format(run.result.n_test)} held-out rows (${100 - run.config.trainPct}%) in ${run.result.seconds}s · seed ${run.config.seed}.`
                  : `Final model: ${run.state === "running" ? "training" : "stopped"} on a ${run.config.trainPct}/${100 - run.config.trainPct} split.`}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {stale && run.state !== "running" && (
                <p className="flex items-center gap-2 rounded-md border border-dashed p-3 text-sm text-muted-foreground">
                  <RotateCcw className="size-4 shrink-0" aria-hidden />
                  These results are for the previous settings ({run.config.trainPct}/{100 - run.config.trainPct}, seed {run.config.seed}). Press &ldquo;Run again&rdquo; to update them.
                </p>
              )}
              {run.state === "running" && (
                <RunProgress stage={run.stage} progress={run.progress} startedAt={run.startedAt} nTrain={run.nTrain} nTest={run.nTest} />
              )}
              {run.state === "error" && (
                <div role="alert" className="flex items-start gap-3 rounded-md border border-destructive/40 bg-destructive/10 p-4 text-sm">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />
                  <div>
                    <p className="font-medium">The run failed</p>
                    <p className="mt-1 text-muted-foreground">{run.message}</p>
                  </div>
                </div>
              )}
              {run.state === "done" && (
                <div className={cn(stale && "opacity-60")}>
                  <ResultsView result={run.result} fileName={run.config.file} />
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
