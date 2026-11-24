// The search the first screen submits (a plain GET form, so it works without JavaScript):
// /results?campus=<id>&size=<size>&budget=<dollars>&max=<minutes>. Budget is optional.
// Wording lives in lib/strings; this file only checks values.

import type { BedroomType } from "./rent";
import type { SortKey } from "./shortlist";

/** Sizes the form offers. "room" has one citywide rent figure (rent.json meta.room). */
export type SearchSize = "room" | Extract<BedroomType, "studio" | "1br" | "2br">;
export const SEARCH_SIZES: readonly SearchSize[] = ["room", "studio", "1br", "2br"];

/** The max-commute buttons, in minutes (owner's decision: buttons, no slider). */
export const MAX_COMMUTE_MIN = [20, 30, 45, 60] as const;
export type MaxCommute = (typeof MAX_COMMUTE_MIN)[number];

// Budgets are any whole number of dollars (owner, M4.3). They are compared with the rent as
// shown, which rent.json has already rounded to $25 (lib/shortlist.ts, rentGroup).

/** The example in the budget hint ("e.g. 1,400"); a valid budget (tested). */
export const BUDGET_EXAMPLE = 1400;

export interface Search {
  campus: string;
  size: SearchSize;
  budget: number | null;
  maxCommute: MaxCommute;
}

export type SearchField = "campus" | "size" | "budget" | "maxCommute";

export type ParsedSearch = { ok: true; search: Search } | { ok: false; errors: SearchField[] };

type Params = Record<string, string | string[] | undefined>;

/** One value, or undefined when absent or repeated (a repeated key is never guessed at). */
function single(params: Params, key: string): string | undefined {
  const v = params[key];
  return typeof v === "string" ? v : undefined;
}

/** Checks the URL's search parameters. Every problem is reported, in form order. */
export function parseSearch(params: Params, campusIds: readonly string[]): ParsedSearch {
  const errors: SearchField[] = [];

  const campus = single(params, "campus");
  if (campus === undefined || !campusIds.includes(campus)) errors.push("campus");

  const size = single(params, "size");
  if (size === undefined || !(SEARCH_SIZES as readonly string[]).includes(size)) errors.push("size");

  let budget: number | null = null;
  const rawBudget = (single(params, "budget") ?? "").trim();
  if (rawBudget !== "" || (params.budget !== undefined && typeof params.budget !== "string")) {
    budget = /^\d+$/.test(rawBudget) ? Number(rawBudget) : NaN;
    // Safe integers only: past 2^53 a typed number is silently rounded (1e19 + 1 -> 1e19).
    if (!(Number.isSafeInteger(budget) && budget > 0)) errors.push("budget");
  }

  const max = single(params, "max");
  const maxCommute = MAX_COMMUTE_MIN.find((m) => String(m) === max);
  if (maxCommute === undefined) errors.push("maxCommute");

  if (errors.length > 0) return { ok: false, errors };
  return {
    ok: true,
    search: { campus: campus!, size: size as SearchSize, budget, maxCommute: maxCommute! },
  };
}

/** Results as cards (default) or on the map (M4 decision 9: the map is never the default). */
export type ResultsView = "list" | "map";

/** The query string for a search, with the form's own parameter names; `sort` and `view` only
 * when they aren't the defaults. */
export function searchQuery(s: Search, sort: SortKey = "commute", view: ResultsView = "list"): string {
  const p = new URLSearchParams({ campus: s.campus, size: s.size });
  if (s.budget !== null) p.set("budget", String(s.budget));
  p.set("max", String(s.maxCommute));
  if (sort !== "commute") p.set("sort", sort);
  if (view !== "list") p.set("view", view);
  return p.toString();
}

/** The shortlist order: `sort=rent` ("cheapest"), else fastest commute first (decision 1).
 * Not a form field, so anything else falls back to the default instead of an error. */
export function parseSort(params: Params): SortKey {
  return single(params, "sort") === "rent" ? "rent" : "commute";
}

/** `view=map`, else the cards. Not a form field: anything else falls back to the default. */
export function parseView(params: Params): ResultsView {
  return single(params, "view") === "map" ? "map" : "list";
}

/** `open=<id>`: the card to show open (from a map popup's "Show details"). */
export function parseOpen(params: Params): string | null {
  return single(params, "open") ?? null;
}
