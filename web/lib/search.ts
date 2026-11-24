// The search the first screen submits (a plain GET form, so it works without JavaScript):
// /results?campus=<id>&size=<size>&budget=<dollars>&max=<minutes>. Budget is optional.
// Wording lives in lib/strings; this file only checks values.

import type { BedroomType } from "./rent";

/** Sizes the form offers. "room" has one citywide rent figure (rent.json meta.room). */
export type SearchSize = "room" | Extract<BedroomType, "studio" | "1br" | "2br">;
export const SEARCH_SIZES: readonly SearchSize[] = ["room", "studio", "1br", "2br"];

/** The max-commute buttons, in minutes (owner's decision: buttons, no slider). */
export const MAX_COMMUTE_MIN = [20, 30, 45, 60] as const;
export type MaxCommute = (typeof MAX_COMMUTE_MIN)[number];

/** Budgets are whole dollars in steps of $25, the rounding step of the rents shown. */
export const BUDGET_STEP = 25;

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
    if (!(budget > 0 && budget % BUDGET_STEP === 0)) errors.push("budget");
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

/** The query string for a search, with the form's own parameter names. */
export function searchQuery(s: Search): string {
  const p = new URLSearchParams({ campus: s.campus, size: s.size });
  if (s.budget !== null) p.set("budget", String(s.budget));
  p.set("max", String(s.maxCommute));
  return p.toString();
}
