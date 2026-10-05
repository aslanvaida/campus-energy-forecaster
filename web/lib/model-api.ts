import Papa from "papaparse";

import type { Row } from "@/lib/split";

/** Columns the model needs (same as the datathon CSV). */
export const REQUIRED_COLUMNS = [
  "id", "building_id", "building_type", "hour", "day_of_week", "month",
  "temperature", "humidity", "occupancy", "previous_usage", "energy_usage",
];

export type Metrics = { rmse: number; mae: number; r2: number };

export type BuildingScore = { building_id: string; building_type: string; n: number; rmse: number; mae: number };

export type RunResult = {
  n_train: number;
  n_test: number;
  seconds: number;
  n_bags: number;
  metrics: Metrics;
  naive: Metrics;
  gaps: { rows_with_gap: number; rmse_with_gap: number | null; rmse_complete: number | null };
  by_building: BuildingScore[];
  points: { actual: number[]; predicted: number[]; building_id: string[] };
  predictions: { id: string[]; actual: number[]; predicted: number[] };
};

export type JobStatus = {
  status: "queued" | "running" | "done" | "error";
  stage: string;
  progress: number;
  result?: RunResult;
  error?: string;
  dropped_unlabelled?: { train: number; test: number };
};

async function errorMessage(res: Response) {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {}
  return res.status >= 500
    ? "The model server is not reachable. Start it with: uvicorn campus_energy_forecaster.api:app --port 8000"
    : `Request failed (${res.status})`;
}

/** Send the two partitions to the API and start a training job. */
export async function startJob(train: Row[], test: Row[], fields: string[]): Promise<string> {
  const form = new FormData();
  form.append("train", new Blob([Papa.unparse(train, { columns: fields })], { type: "text/csv" }), "train.csv");
  form.append("test", new Blob([Papa.unparse(test, { columns: fields })], { type: "text/csv" }), "test.csv");
  const res = await fetch("/api/model/jobs", { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorMessage(res));
  return (await res.json()).job_id;
}

export async function getJob(id: string, signal?: AbortSignal): Promise<JobStatus> {
  const res = await fetch(`/api/model/jobs/${id}`, { signal, cache: "no-store" });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}
