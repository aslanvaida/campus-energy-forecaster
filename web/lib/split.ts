export type Row = Record<string, string>;

export type Split = {
  train: Row[];
  test: Row[];
  /** Keys present in both partitions. Always empty; reported so the page can show the check. */
  shared: string[];
  /** How rows were identified: the `id` column, or the full row content when there is no usable id. */
  keyedBy: "id" | "row content";
  /** Rows that share a key with an earlier row; kept together on the same side. */
  duplicateRows: number;
};

/** Deterministic PRNG so the same seed always gives the same split. */
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Shuffle and split rows into non-overlapping train and test sets.
 *
 * Rows are grouped by key (the `id` column if present, otherwise the full row), and whole groups are assigned to
 * one side, so a duplicated row can never appear in both sets.
 */
export function splitRows(rows: Row[], fields: string[], trainFraction: number, seed: number): Split {
  const keyedBy = fields.includes("id") && rows.every((r) => r.id !== undefined && r.id !== "") ? "id" : "row content";
  const keyOf = (r: Row) => (keyedBy === "id" ? r.id : JSON.stringify(fields.map((f) => r[f])));

  const groups = new Map<string, Row[]>();
  for (const r of rows) {
    const k = keyOf(r);
    const g = groups.get(k);
    if (g) g.push(r);
    else groups.set(k, [r]);
  }

  const keys = [...groups.keys()];
  const rand = mulberry32(seed);
  for (let i = keys.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [keys[i], keys[j]] = [keys[j], keys[i]];
  }

  const target = Math.round(rows.length * trainFraction);
  const train: Row[] = [];
  const test: Row[] = [];
  const trainKeys = new Set<string>();
  for (const k of keys) {
    const g = groups.get(k)!;
    if (train.length + g.length <= target || train.length === 0) {
      train.push(...g);
      trainKeys.add(k);
    } else {
      test.push(...g);
    }
  }

  const shared = [...new Set(test.map(keyOf))].filter((k) => trainKeys.has(k));
  return { train, test, shared, keyedBy, duplicateRows: rows.length - groups.size };
}
