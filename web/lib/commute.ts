// Types for web/public/data/commute.json (written by pipeline/src/mtlhousing/export.py)
// and the join used by the map. A null time listed in `over_max` means "more than
// meta.max_trip_min"; any other null means "no data".

export type TimeStat = "median" | "p10" | "p90";

export interface TimeBlock {
  median: number | null;
  p10: number | null;
  p90: number | null;
  over_max: TimeStat[];
}

export interface DestinationResult extends TimeBlock {
  n_unreachable: number;
  fastest_share: number | null;
}

export interface CampusResult extends TimeBlock {
  n_points: number;
  n_unreachable: number;
  unreachable_share: number | null;
  flags: string[];
  rule: "fastest_destination";
  by_destination: Record<string, DestinationResult>;
}

export interface CampusMeta {
  name: string;
  destinations: {
    id: string;
    name: string;
    lat: number;
    lon: number;
    access_adjustment_min: number;
  }[];
}

export interface CommuteFile {
  meta: {
    analysis_date: string;
    departure_window: { start: string; minutes: number };
    max_trip_min: number;
    campuses: Record<string, CampusMeta>;
    [key: string]: unknown;
  };
  results: Record<string, Record<string, CampusResult | undefined>>;
}

/** "44 min", "> 120 min" or "no data". */
export function formatTime(block: TimeBlock, stat: TimeStat, maxTripMin: number): string {
  const v = block[stat];
  if (v !== null) return `${Math.round(v)} min`;
  return block.over_max.includes(stat) ? `> ${maxTripMin} min` : "no data";
}

/** Flat properties for the map layer: numbers only where they exist. */
export function featureProps(result: CampusResult | undefined): Record<string, unknown> {
  if (!result) return { status: "no_data" };
  if (result.median !== null) return { status: "ok", median: result.median };
  return { status: result.over_max.includes("median") ? "over_max" : "no_data" };
}
