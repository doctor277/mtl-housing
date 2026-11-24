// Types for web/public/data/rent.json (written by pipeline/src/mtlhousing/rent_export.py) and
// the rent colour classes. No text here: the wording (badges, CMHC lines, source and data
// lines) is in lib/strings. Every rent in rent.json is already rounded to $25; null = not
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

/** Sizes the site shows rents for (3br_plus is in rent.json but not shown). */
export type ShownSize = Exclude<BedroomType, "3br_plus">;
export const SIZES: ShownSize[] = ["studio", "1br", "2br"];
export const DEFAULT_SIZE: ShownSize = "1br";

// --- colour classes ---------------------------------------------------------------------
// Relative to the Montréal asking rent for the chosen size. Diverging, colour-blind-safe,
// centred on a neutral 95–105%: blue = cheaper, orange = pricier (validated with the
// dataviz skill's palette checker; see docs/methodology.md).
export const BIN_PCT = [0.85, 0.95, 1.05, 1.15, 1.3];
export const RENT_COLOURS = ["#2166ac", "#6aaed6", "#f3f2ee", "#eb9236", "#b85208", "#6a2d05"];
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

/** Index into RENT_COLOURS: the number of edges at or below the (rounded) estimate. */
export function binIndex(estimate: number, edges: number[]): number {
  return edges.filter((e) => estimate >= e).length;
}

export const isLowReliability = (label: LabelKey) =>
  label === "neighbourhood_low" || label === "zone_low";

/** Flat properties for the map layer, one set per shown size: rent_bin_<size> (-1 = not
 * enough data) and rent_low_<size> (grade d). */
export function rentFeatureProps(
  entries: Record<BedroomType, RentEntry> | undefined,
  meta: RentMeta,
): Record<string, number | boolean> {
  const props: Record<string, number | boolean> = {};
  for (const key of SIZES) {
    const e = entries?.[key];
    const edges = binEdges(meta.montreal[key].statcan_asking, meta.rounding.step);
    props[`rent_bin_${key}`] = e?.estimate != null ? binIndex(e.estimate, edges) : -1;
    props[`rent_low_${key}`] = e ? isLowReliability(e.label) : false;
  }
  return props;
}
