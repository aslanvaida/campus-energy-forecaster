"use client";

import * as React from "react";
import Papa from "papaparse";
import { CheckCircle2, Download, FileSpreadsheet, Shuffle, Upload, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { splitRows, type Row } from "@/lib/split";

type Dataset = { name: string; size: number; fields: string[]; rows: Row[] };
type Mode = "train" | "test";

const STEPS = [10, 20, 30, 40, 50, 60, 70, 80, 90];
const PREVIEW_ROWS = 5;

const fmt = new Intl.NumberFormat("en-US");

function formatBytes(n: number) {
  return n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function downloadCsv(rows: Row[], fields: string[], filename: string) {
  const blob = new Blob([Papa.unparse(rows, { columns: fields })], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}

export function DatasetSplitter() {
  const [data, setData] = React.useState<Dataset | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [mode, setMode] = React.useState<Mode>("train");
  const [pct, setPct] = React.useState(80);
  const [seed, setSeed] = React.useState(42);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const trainPct = mode === "train" ? pct : 100 - pct;
  const split = React.useMemo(
    () => (data ? splitRows(data.rows, data.fields, trainPct / 100, seed) : null),
    [data, trainPct, seed],
  );

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
        if (!fields.length || !res.data.length) {
          setError("That file has no header row or no data rows.");
          return;
        }
        if (res.data.length < 2) {
          setError("Need at least 2 rows to make a train/test split.");
          return;
        }
        setData({ name: file.name, size: file.size, fields, rows: res.data });
      },
      error: (err) => setError(`Could not read the file: ${err.message}`),
    });
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) load(file);
  }

  const base = data?.name.replace(/\.csv$/i, "") ?? "dataset";

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Upload */}
      <Card>
        <CardHeader>
          <CardTitle>1. Upload your dataset</CardTitle>
          <CardDescription>A CSV with a header row. It is read in your browser and never uploaded to a server.</CardDescription>
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
              <Button variant="outline" onClick={() => inputRef.current?.click()}>
                <Upload data-icon="inline-start" /> Replace
              </Button>
              <Button variant="ghost" size="icon" aria-label="Remove dataset" onClick={() => setData(null)}>
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
          {error && (
            <p role="alert" className="mt-3 text-sm text-destructive">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      {/* 2. Split */}
      <Card className={cn(!data && "pointer-events-none opacity-50")} aria-disabled={!data}>
        <CardHeader>
          <CardTitle>2. Choose the split</CardTitle>
          <CardDescription>Rows are shuffled with a fixed seed, then divided so no row lands in both sets.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Tabs value={mode} onValueChange={(v) => {
              const next = v as Mode;
              if (next !== mode) {
                setMode(next);
                setPct(100 - pct); // keep the same split, just express it from the other side
              }
            }}>
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
              <span className="font-mono text-2xl font-semibold tabular-nums">{pct}%</span>
            </div>
            <Slider
              aria-labelledby="split-label"
              min={10}
              max={90}
              step={10}
              value={[pct]}
              onValueChange={(v) => setPct(Array.isArray(v) ? v[0] : v)}
            />
            <div className="mt-2 flex justify-between text-xs text-muted-foreground tabular-nums" aria-hidden>
              {STEPS.map((s) => (
                <span key={s} className={cn("w-8 text-center", s === pct && "font-semibold text-foreground")}>
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* proportion bar */}
          <div>
            <div className="flex h-9 overflow-hidden rounded-md text-xs font-medium">
              <div
                className="flex items-center justify-center bg-[var(--train)] text-[var(--train-foreground)] transition-[width] duration-300"
                style={{ width: `${trainPct}%` }}
              >
                Train {trainPct}%
              </div>
              <div
                className="flex items-center justify-center bg-[var(--test)] text-[var(--test-foreground)] transition-[width] duration-300"
                style={{ width: `${100 - trainPct}%` }}
              >
                Test {100 - trainPct}%
              </div>
            </div>
          </div>

          {split && data && (
            <div className="grid gap-3 sm:grid-cols-3">
              <Stat label="Training rows" value={fmt.format(split.train.length)} swatch="var(--train)" />
              <Stat label="Test rows" value={fmt.format(split.test.length)} swatch="var(--test)" />
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">Overlap check</p>
                <div className="mt-1 flex items-center gap-2">
                  {split.shared.length === 0 && split.train.length + split.test.length === data.rows.length ? (
                    <>
                      <CheckCircle2 className="size-5 text-[var(--ok)]" aria-hidden />
                      <span className="text-lg font-semibold">No overlap</span>
                    </>
                  ) : (
                    <span className="text-lg font-semibold text-destructive">{split.shared.length} shared</span>
                  )}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {split.shared.length} shared {split.keyedBy === "id" ? "ids" : "rows"} · every row used once
                  {split.duplicateRows > 0 && ` · ${split.duplicateRows} duplicate rows kept together`}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 3. Preview + download */}
      {split && data && (
        <Card>
          <CardHeader>
            <CardTitle>3. Preview and download</CardTitle>
            <CardDescription>
              First {PREVIEW_ROWS} rows of each set. Downloads keep the original columns and order.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6 lg:grid-cols-2">
            {(
              [
                ["Training set", split.train, "train", "var(--train)"],
                ["Test set", split.test, "test", "var(--test)"],
              ] as const
            ).map(([title, rows, suffix, swatch]) => (
              <div key={suffix} className="flex min-w-0 flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full" style={{ background: swatch }} aria-hidden />
                    <h3 className="font-medium">{title}</h3>
                    <Badge variant="secondary" className="tabular-nums">{fmt.format(rows.length)} rows</Badge>
                  </div>
                  <Button size="sm" onClick={() => downloadCsv(rows, data.fields, `${base}_${suffix}.csv`)}>
                    <Download data-icon="inline-start" /> {suffix}.csv
                  </Button>
                </div>
                <div className="overflow-x-auto rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {data.fields.map((f) => (
                          <TableHead key={f} className="whitespace-nowrap">{f}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rows.slice(0, PREVIEW_ROWS).map((r, i) => (
                        <TableRow key={i}>
                          {data.fields.map((f) => (
                            <TableCell key={f} className="whitespace-nowrap font-mono text-xs tabular-nums">
                              {r[f] === "" ? <span className="text-muted-foreground">—</span> : r[f]}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value, swatch }: { label: string; value: string; swatch: string }) {
  return (
    <div className="rounded-lg border p-4">
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="size-2.5 rounded-full" style={{ background: swatch }} aria-hidden />
        {label}
      </p>
      <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
