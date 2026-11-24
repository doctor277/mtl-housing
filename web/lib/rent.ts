// Types for web/public/data/rent.json (written by pipeline/src/mtlhousing/rent_export.py),
// the rent colour classes and the texts the map shows. Wording: docs/methodology.md, Rent,
// "What the site shows". Every rent in rent.json is already rounded to $25; null = not
// enough data.

export type BedroomType = "studio" | "1br" | "2br" | "3br_plus";
export type LabelKey = "neighbourhood" | "zone" | "neighbourhood_low" | "zone_low" | "none";

export interface CmhcAreaUsed {
  type: "area" | "zone";
  name: string;
  share: number; // of the neighbourhood's rental units; sums to the coverage, not to 1
  grade: string;
}

export interface RentEntry {
  estimate: number | null;
  label: LabelKey;
  grade: string | null;
  coverage_pct: number | null;
  cmhc_areas: CmhcAreaUsed[];
}

export interface RentMeta {
  rounding: { step: number; mode: string };
  shown_bedroom_types: BedroomType[];
  cmhc: { period: string };
  statcan: { quarter: string };
  montreal: Record<BedroomType, { cmhc_average: number; statcan_asking: number }>;
  room: { estimate: number };
  grade_words: Record<string, string>;
  [key: string]: unknown;
}

export interface RentFile {
  meta: RentMeta;
  results: Record<string, Record<BedroomType, RentEntry>>;
}

// Sizes the site offers, in Québec naming. 3br_plus is in rent.json but not shown.
export const SIZES: { key: BedroomType; label: string }[] = [
  { key: "studio", label: "Studio" },
  { key: "1br", label: "3½" },
  { key: "2br", label: "4½" },
];
export const DEFAULT_SIZE: BedroomType = "1br";

// --- colour classes ---------------------------------------------------------------------
// Relative to the Montréal asking rent for the chosen size. Diverging, colour-blind-safe,
// centred on a neutral 95–105%: blue = cheaper, orange = pricier (validated with the
// dataviz skill's palette checker; see docs/methodology.md).
export const BIN_PCT = [0.85, 0.95, 1.05, 1.15, 1.3];
export const RENT_BINS: [pct: string, colour: string][] = [
  ["< 85%", "#2166ac"],
  ["85–95%", "#6aaed6"],
  ["95–105%", "#f3f2ee"],
  ["105–115%", "#eb9236"],
  ["115–130%", "#b85208"],
  ["> 130%", "#6a2d05"],
];
export const RENT_NO_DATA_COLOUR = "#6e6e6e"; // "not enough data", darker than "no residents"
export const RENT_FILL_OPACITY = 0.8; // map fill; the legend swatches use the same

/** Class edges in dollars for one size: the smallest multiple of `step` at or above
 * pct × level. Rents are multiples of `step`, so "rent ≥ edge" means exactly "rent ≥ pct"
 * and no rent is coloured in a class whose % it doesn't meet. (Rounding the edge to the
 * nearest step instead could put it below the %: 85% of $1,480 = $1,258 → $1,250 = 84.5%.)
 * The epsilon absorbs float noise such as 1.3 × 1250 = 1625.0000000000002. */
export function binEdges(montrealAsking: number, step: number): number[] {
  return BIN_PCT.map((p) => Math.ceil((p * montrealAsking) / step - 1e-9) * step);
}

/** Index into RENT_BINS: the number of edges at or below the (rounded) estimate. */
export function binIndex(estimate: number, edges: number[]): number {
  return edges.filter((e) => estimate >= e).length;
}

/** "1,475" (en-CA grouping, no locale dependency). */
export function formatDollars(x: number): string {
  return String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** "≈ $1,475". */
export function formatRent(x: number): string {
  return `≈ $${formatDollars(x)}`;
}

/** Legend text per class, in dollars. Rents are multiples of `step`, so the upper bound
 * of a class is the next edge minus one step. */
export function binLegend(edges: number[], step: number): string[] {
  const out = [`under $${formatDollars(edges[0])}`];
  for (let i = 0; i < edges.length - 1; i++) {
    out.push(`$${formatDollars(edges[i])}–$${formatDollars(edges[i + 1] - step)}`);
  }
  out.push(`$${formatDollars(edges[edges.length - 1])} or more`);
  return out;
}

// --- texts ------------------------------------------------------------------------------

export const BADGES: Record<LabelKey, string> = {
  neighbourhood: "Estimate",
  zone: "Wider-area estimate",
  neighbourhood_low: "Low reliability",
  zone_low: "Low reliability",
  none: "Not enough data",
};

export const isLowReliability = (label: LabelKey) =>
  label === "neighbourhood_low" || label === "zone_low";

function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

function wholePct(share: number): string {
  return `${Math.round(share * 100)}%`;
}

function oneDecimalPct(share: number): string {
  return `${(share * 100).toFixed(1)}%`;
}

/** Main detail line. One CMHC area or zone: the approved text. Several (a neighbourhood
 * split between CMHC areas): the rating moves to the split line, per area, because the
 * label's worst grade isn't every area's rating. */
export function detailLine(e: RentEntry, meta: RentMeta): string {
  const words = meta.grade_words;
  const period = meta.cmhc.period;
  const areas = e.cmhc_areas;
  if (e.label === "none") return "CMHC doesn't publish a reliable rent for this size here or nearby.";
  const zone = areas[0]?.type === "zone";
  if (areas.length === 1) {
    const name = areas[0].name;
    const word = words[areas[0].grade];
    switch (e.label) {
      case "neighbourhood":
        return `Based on CMHC's average rent in CMHC area ${name} (${period}, rated ${word} by CMHC).`;
      case "zone":
        return `CMHC has no reliable figure for this area, so this uses the wider CMHC zone ${name} (rated ${word} by CMHC).`;
      case "neighbourhood_low":
        return `Based on CMHC's average rent in CMHC area ${name}, which CMHC rates "use with caution".`;
      case "zone_low":
        return `Based on the wider CMHC zone ${name}, which CMHC rates "use with caution".`;
    }
  }
  const kind = zone ? "CMHC zones" : "CMHC areas";
  const names = joinNames(areas.map((a) => a.name));
  if (isLowReliability(e.label)) {
    return `Based on CMHC's average rents in ${kind} ${names}; CMHC rates at least one of them "use with caution".`;
  }
  return `Based on CMHC's average rents in ${kind} ${names} (${period}).`;
}

/** Extra lines: the split (raw shares, per-area rating) and the coverage. */
export function extraLines(e: RentEntry, meta: RentMeta): string[] {
  const words = meta.grade_words;
  const areas = e.cmhc_areas;
  const lines: string[] = [];
  const partial = e.coverage_pct !== null;
  const kind = areas[0]?.type === "zone" ? "CMHC zones" : "CMHC areas";
  if (areas.length > 1) {
    const rated = (g: string) => (g === "d" ? `rated "${words[g]}"` : `rated ${words[g]}`);
    const parts = areas.map(
      (a) => `${a.name} (${partial ? oneDecimalPct(a.share) : wholePct(a.share)}, ${rated(a.grade)})`,
    );
    lines.push(`Weighted average of ${kind} ${joinNames(parts)}, by rental units.`);
  }
  if (partial) {
    const shares =
      areas.length === 1 ? ` (${areas[0].name}: ${oneDecimalPct(areas[0].share)})` : "";
    lines.push(
      `Covers ${e.coverage_pct}% of this neighbourhood's rental units${shares}; CMHC has no reliable figure for the rest.`,
    );
  }
  return lines;
}

/** The line under every estimate (owner's wording, M3). */
export function sourceLine(): string {
  return "Estimate based on average rents, adjusted to current Montréal asking rents. Not a listing, and possibly low in areas with many long-time tenants.";
}

/** The two data dates, shown once in the rent legend. */
export function dataLine(meta: RentMeta): string {
  return `Data: CMHC (${meta.cmhc.period}) and Statistics Canada's experimental asking rents (${meta.statcan.quarter}).`;
}

/** The room line (legend panel). */
export function roomLine(meta: RentMeta): string {
  return `Room: ${formatRent(meta.room.estimate)} a month: Montréal-wide average asking rent for a room, not specific to this neighbourhood (Statistics Canada, ${meta.statcan.quarter}).`;
}

/** Flat properties for the map layer, one set per shown size: rent_bin_<size> (-1 = not
 * enough data) and rent_low_<size> (grade d). */
export function rentFeatureProps(
  entries: Record<BedroomType, RentEntry> | undefined,
  meta: RentMeta,
): Record<string, number | boolean> {
  const props: Record<string, number | boolean> = {};
  for (const { key } of SIZES) {
    const e = entries?.[key];
    const edges = binEdges(meta.montreal[key].statcan_asking, meta.rounding.step);
    props[`rent_bin_${key}`] = e?.estimate != null ? binIndex(e.estimate, edges) : -1;
    props[`rent_low_${key}`] = e ? isLowReliability(e.label) : false;
  }
  return props;
}
