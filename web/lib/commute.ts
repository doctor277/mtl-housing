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

// Short labels for the campus picker; any other campus falls back to its full name.
const SHORT_NAMES: Record<string, string> = {
  udem: "UdeM",
  mcgill: "McGill",
  concordia_sgw: "Concordia SGW",
};

/** Campuses present in commute.json, in file order, with picker labels. */
export function campusOptions(commute: CommuteFile): { key: string; label: string }[] {
  return Object.entries(commute.meta.campuses).map(([key, c]) => ({
    key,
    label: SHORT_NAMES[key] ?? c.name,
  }));
}

/** Start and end of the departure window, "7:30" and "8:30", from commute.json meta. */
export function departureWindow(meta: CommuteFile["meta"]): { start: string; end: string } {
  const [h, m] = meta.departure_window.start.split(":").map(Number);
  const start = h * 60 + m;
  const hhmm = (t: number) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
  return { start: hhmm(start), end: hhmm(start + meta.departure_window.minutes) };
}

/** "leaving 7:30–8:30, Tue 2026-12-01", from commute.json meta. */
export function windowLabel(meta: CommuteFile["meta"]): string {
  const { start, end } = departureWindow(meta);
  // Noon UTC avoids a time-zone shift to the previous day.
  const day = new Date(`${meta.analysis_date}T12:00:00Z`).toLocaleDateString("en-CA", {
    weekday: "short",
    timeZone: "UTC",
  });
  return `leaving ${start}–${end}, ${day} ${meta.analysis_date}`;
}

/** What the time is measured to: "to Roddick Gates" for one destination, "fastest
 * UdeM building" when several buildings count (the faster one per home). */
export function commuteTarget(campusId: string, campus: CampusMeta): string {
  if (campus.destinations.length === 1) return `to ${campus.destinations[0].name}`;
  return `fastest ${SHORT_NAMES[campusId] ?? campus.name} building`;
}
