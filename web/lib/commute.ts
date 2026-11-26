import { inLang, type Localized } from "./localized";
import { strings } from "./strings";

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
  name: Localized;
  destinations: {
    id: string;
    name: Localized;
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
    walk_speed_kmh: number;
    /** The schedule feeds routed on, with their service periods (ISO dates). */
    gtfs_feeds: { name: string; version: string | null; start: string; end: string }[];
    /** OpenStreetMap data date (ISO timestamp). */
    osm_date: string;
    /** Areas left out of the commute statistics, with the pipeline's reason. */
    out_of_scope: { area: string; reason: Localized }[];
    /** Attribution texts written by the pipeline (DATA_SOURCES.md wording), both languages. */
    sources: Localized[];
    campuses: Record<string, CampusMeta>;
    [key: string]: unknown;
  };
  results: Record<string, Record<string, CampusResult | undefined>>;
}

/** Flat properties for the map layer: numbers only where they exist. */
export function featureProps(result: CampusResult | undefined): Record<string, unknown> {
  if (!result) return { status: "no_data" };
  if (result.median !== null) return { status: "ok", median: result.median };
  return { status: result.over_max.includes("median") ? "over_max" : "no_data" };
}

/** Per-campus properties for one quartier: status_<campus> and median_<campus>. */
export function campusFeatureProps(
  results: Record<string, CampusResult | undefined> | undefined,
  campusIds: string[],
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const c of campusIds) {
    for (const [k, v] of Object.entries(featureProps(results?.[c]))) out[`${k}_${c}`] = v;
  }
  return out;
}

/** Campuses present in commute.json, in file order, with short labels ("UdeM"). */
export function campusOptions(commute: CommuteFile): { key: string; label: string }[] {
  return Object.entries(commute.meta.campuses).map(([key, c]) => ({
    key,
    label: strings.commute.campusShort(key, inLang(c.name, strings.lang)),
  }));
}

/** Start and end of the departure window, "7:30" and "8:30", from commute.json meta. */
export function departureWindow(meta: CommuteFile["meta"]): { start: string; end: string } {
  const [h, m] = meta.departure_window.start.split(":").map(Number);
  const start = h * 60 + m;
  const hhmm = (t: number) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
  return { start: hhmm(start), end: hhmm(start + meta.departure_window.minutes) };
}
