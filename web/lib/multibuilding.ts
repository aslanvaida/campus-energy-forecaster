import raw from "@/public/data/multibuilding.json";

/** Written by scripts/validate_buildings.py: the same method run on schools and healthcare buildings from a second public dataset. */
export const multi = raw as unknown as {
  dataset: { name: string; license: string; source: string; citation: string };
  method: string;
  groups: Record<
    string,
    {
      label: string;
      n_buildings: number;
      n_sites: number;
      median_mae_gain_vs_naive_pct: number;
      share_buildings_beating_naive_pct: number;
      median_cv_rmse_pct: number;
      median_band_coverage_pct: number;
      median_flagged_events_per_30d: number;
      median_recall_pct: { small: number; medium: number; large: number };
    }
  >;
  all: { n_buildings: number; median_mae_gain_vs_naive_pct: number; share_buildings_beating_naive_pct: number; median_band_coverage_pct: number };
};
