"use client";

import * as React from "react";
import Papa from "papaparse";
import { Download } from "lucide-react";

import { BuildingBars } from "@/components/results/building-bars";
import { ScatterChart } from "@/components/results/scatter-chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RunResult } from "@/lib/model-api";

const fmt = new Intl.NumberFormat("en-US");
const WORST = 10;

function Tile({ label, value, note, hero }: { label: string; value: string; note?: React.ReactNode; hero?: boolean }) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={hero ? "mt-1 text-5xl font-semibold tracking-tight" : "mt-1 text-3xl font-semibold tracking-tight"}>{value}</p>
      {note && <p className="mt-1 text-xs text-muted-foreground">{note}</p>}
    </div>
  );
}

export function ResultsView({ result, fileName }: { result: RunResult; fileName: string }) {
  const { metrics: m, naive, gaps, predictions: p } = result;
  const gain = (1 - m.rmse / naive.rmse) * 100;

  const worst = React.useMemo(
    () =>
      p.id
        .map((id, i) => ({ id, actual: p.actual[i], predicted: p.predicted[i], error: p.predicted[i] - p.actual[i] }))
        .sort((a, b) => Math.abs(b.error) - Math.abs(a.error))
        .slice(0, WORST),
    [p],
  );

  function download() {
    const rows = p.id.map((id, i) => ({ id, actual: p.actual[i], prediction: p.predicted[i], error: +(p.predicted[i] - p.actual[i]).toFixed(4) }));
    const blob = new Blob([Papa.unparse(rows)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    Object.assign(document.createElement("a"), { href: url, download: `${fileName.replace(/\.csv$/i, "")}_test_predictions.csv` }).click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile hero label="Test RMSE" value={m.rmse.toFixed(2)} note={`energy-usage units, ${fmt.format(result.n_test)} test rows`} />
        <Tile label="Better than naive" value={`${gain.toFixed(0)}%`} note={`naive "usage = previous usage" RMSE ${naive.rmse.toFixed(2)}`} />
        <Tile label="MAE" value={m.mae.toFixed(2)} note={`naive ${naive.mae.toFixed(2)}`} />
        <Tile label="R²" value={m.r2.toFixed(3)} note={`naive ${naive.r2.toFixed(3)}`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Predicted vs actual</CardTitle>
            <CardDescription>
              Each dot is a test row{result.points.actual.length < result.n_test && ` (random ${fmt.format(result.points.actual.length)} shown)`}. Closer to the diagonal is better.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScatterChart actual={result.points.actual} predicted={result.points.predicted} buildingId={result.points.building_id} />
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Error by building</CardTitle>
            <CardDescription>Test RMSE per building. The vertical line is the overall RMSE ({m.rmse.toFixed(2)}).</CardDescription>
          </CardHeader>
          <CardContent>
            <BuildingBars data={result.by_building} overall={m.rmse} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Largest errors</CardTitle>
            <CardDescription>
              The {WORST} test rows the model missed by the most.
              {gaps.rows_with_gap > 0 && gaps.rmse_with_gap !== null && gaps.rmse_complete !== null &&
                ` Rows with a missing input (${fmt.format(gaps.rows_with_gap)}) score RMSE ${gaps.rmse_with_gap.toFixed(2)} vs ${gaps.rmse_complete.toFixed(2)} for complete rows.`}
            </CardDescription>
          </div>
          <Button variant="outline" onClick={download}>
            <Download data-icon="inline-start" /> All {fmt.format(result.n_test)} predictions (.csv)
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>id</TableHead>
                  <TableHead className="text-right">Actual</TableHead>
                  <TableHead className="text-right">Predicted</TableHead>
                  <TableHead className="text-right">Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {worst.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono text-xs">{r.id}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.actual.toFixed(2)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.predicted.toFixed(2)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.error > 0 ? "+" : ""}{r.error.toFixed(2)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
