import raw from "@/public/data/results.json";

/** Everything the dashboard shows comes from this file, written by scripts/run_analysis.py. */
export type WasteEvent = {
  meter: string;
  label: string;
  start: string;
  end: string;
  hours: number;
  after_hours: boolean;
  mean_excess_kw: number;
  excess_kwh: number;
  excess_kwh_floor: number;
  cost_usd: number;
  co2_kg: number;
};

export type OutageOption = {
  keep: string[];
  shed: string[];
  mean_kw: number;
  runtime_h: number;
  actual_runtime_h: number | null;
  runtime_low_h: number | null;
  runtime_high_h: number | null;
};

export const results = raw as unknown as {
  dataset: { name: string; license: string; source: string; period: string; citation: string };
  assumptions: { tariff_usd_per_kwh: number; carbon_kg_per_kwh: number; tariff_source: string; carbon_source: string };
  overview: { annual_kwh: Record<string, number>; annual_cost_usd: number; annual_co2_t: number; missing_hours_pct: number; peak_kw: number; mean_kw_by_year: Record<string, Record<string, number>> };
  forecast: Record<
    string,
    Record<
      string,
      | string
      | {
          n_hours: number;
          mae_kw: number;
          cv_rmse_pct: number;
          nmbe_pct: number;
          naive_mae_kw: number;
          naive_cv_rmse_pct: number;
          mae_gain_vs_naive_pct: number;
          band_coverage_pct: number;
          band_nominal_pct: number;
        }
    >
  >;
  waste: {
    window: string;
    days: number;
    all_events: number;
    summary: { events: number; excess_kwh: number; excess_kwh_floor: number; cost_usd: number; co2_kg: number; after_hours_events: number };
    per_meter: Record<string, { label: string; events: number; excess_kwh: number; cost_usd: number; co2_kg: number }>;
    top_events: WasteEvent[];
    benchmark: Record<
      string,
      {
        label: string;
        flagged_events_per_30d: number;
        by_size: { size: string; extra_load_pct_of_median: number[]; injected_faults: number; recall_pct: number; flagged_kwh_over_injected_kwh_pct: number }[];
      }
    >;
  };
  after_hours: Record<string, { label: string; after_hours_share_pct: number; after_hours_kwh: number; total_kwh: number } | number | { cut_pct: number; kwh: number; cost_usd: number; co2_kg: number }[]> & {
    share_of_hours_after_hours_pct: number;
    overnight_vs_midday_plug_pct: number;
    what_if: { cut_pct: number; kwh: number; cost_usd: number; co2_kg: number }[];
  };
  outage: {
    batteries_kwh: number[];
    default_must_keep: string[];
    backup_assumptions: { usable_fraction: number; efficiency: number };
    accuracy: { battery_kwh: number; n_starts: number; n_skipped_missing_data: number; mean_actual_runtime_h: number; mae_h: number; mape_pct: number; bias_h: number };
    scenarios: {
      key: string;
      label: string;
      start: string;
      load_profile: { hour: number; hvac: number; lighting: number; plug: number }[];
      batteries: { capacity_kwh: number; options: OutageOption[] }[];
    }[];
  };
  peak: {
    accuracy: { n_days: number; mae_kw: number; mape_pct: number; peak_hour_within_2h_pct: number; top_days: number; top_days_caught_pct: number };
    shift: { share_shifted_pct: number; days_acted_on: number; mean_peak_reduction_kw: number; mean_peak_reduction_pct: number; annual_peak_before_kw: number; annual_peak_after_kw: number }[];
    next_days: { date: string; forecast_kw: number; forecast_hour: number; actual_kw: number | null; actual_hour: number | null }[];
  };
  series: { window: string; hours: string[] } & Record<string, unknown>;
};

export const LOAD_LABEL: Record<string, string> = { hvac: "HVAC", lighting: "Lighting", plug: "Plug loads", total: "Whole building" };

export const fmt = (n: number, digits = 0) => n.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
export const usd = (n: number) => `$${fmt(n)}`;
export const when = (iso: string) =>
  new Date(iso.replace(" ", "T")).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", hour12: true });
export const hoursText = (h: number) => (h >= 336 ? "14+ days" : h >= 48 ? `${fmt(h / 24, 1)} days` : `${fmt(h, 1)} h`);
