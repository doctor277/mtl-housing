// The shortlist (M4.2): which neighbourhoods a search shows, in which group, in which order.
// Rules: docs/ROADMAP.md, "M4 decisions" 1–5 and 7–8. Pure functions, no text: wording lives
// in lib/strings.

import type { CommuteFile } from "./commute";
import type { BedroomType, LabelKey, RentFile } from "./rent";
import type { Search } from "./search";

/** A neighbourhood with residents (neighbourhoods.geojson, no_residents false). */
export interface Hood {
  id: string;
  name: string;
  borough: string;
}

export type SortKey = "commute" | "rent";

/** "fits" / "over" / "noData" with a budget; "all" without one, and for rooms. */
export type GroupKey = "fits" | "over" | "all" | "noData";

export interface ShortlistItem extends Hood {
  /** Median commute, unrounded (sorting). */
  median: number;
  /** Median commute as shown: whole minutes. */
  minutes: number;
  /** Rent as shown (rent.json is already rounded to $25), or null = not enough data. Rooms: null. */
  rent: number | null;
  label: LabelKey | null;
}

export interface Shortlist {
  mode: "budget" | "noBudget" | "room";
  /** Non-empty groups, in display order. */
  groups: { key: GroupKey; items: ShortlistItem[] }[];
  /** Neighbourhoods within the max commute (shown or hidden by budget). */
  withinCommute: number;
  /** Over the max commute, including "more than 2 h". */
  tooFar: number;
  /** No commute data for this campus: hidden, and said so under the results (decision 4). */
  hiddenNoCommute: number;
  /** More than 10% over the budget: hidden (decision 2). */
  hiddenOverBudget: number;
  /** Rooms: the one citywide figure, and whether it is above the budget (decision 5). */
  roomEstimate: number | null;
  roomWarning: boolean;
}

/** Where a rent goes against a budget. `rent` is the rounded rent the user sees. "over" is
 * budget < rent ≤ budget × 1.10, computed in integers (decision 7: rent·10 ≤ budget·11). */
export function rentGroup(rent: number | null, budget: number): "fits" | "over" | "hidden" | "noData" {
  if (rent === null) return "noData";
  if (rent <= budget) return "fits";
  if (rent * 10 <= budget * 11) return "over";
  return "hidden";
}

const byName = (a: ShortlistItem, b: ShortlistItem) => a.name.localeCompare(b.name, "fr");
const byCommute = (a: ShortlistItem, b: ShortlistItem) => a.median - b.median || byName(a, b);
const byRent = (a: ShortlistItem, b: ShortlistItem) =>
  (a.rent ?? Infinity) - (b.rent ?? Infinity) || byCommute(a, b);

export function buildShortlist(
  hoods: Hood[],
  commute: CommuteFile,
  rent: RentFile,
  search: Search,
  sort: SortKey,
): Shortlist {
  const room = search.size === "room";
  const mode = room ? "room" : search.budget === null ? "noBudget" : "budget";
  const out: Shortlist = {
    mode,
    groups: [],
    withinCommute: 0,
    tooFar: 0,
    hiddenNoCommute: 0,
    hiddenOverBudget: 0,
    roomEstimate: room ? rent.meta.room.estimate : null,
    roomWarning: room && search.budget !== null && search.budget < rent.meta.room.estimate,
  };

  const groups: Record<GroupKey, ShortlistItem[]> = { fits: [], over: [], all: [], noData: [] };
  for (const hood of hoods) {
    const c = commute.results[hood.id]?.[search.campus];
    if (!c || (c.median === null && !c.over_max.includes("median"))) {
      out.hiddenNoCommute++;
      continue;
    }
    // Compared as shown, in whole minutes; "more than 2 h" is over every button.
    if (c.median === null || Math.round(c.median) > search.maxCommute) {
      out.tooFar++;
      continue;
    }
    out.withinCommute++;
    const item: ShortlistItem = { ...hood, median: c.median, minutes: Math.round(c.median), rent: null, label: null };
    if (room) {
      groups.all.push(item);
      continue;
    }
    const entry = rent.results[hood.id]?.[search.size as BedroomType];
    item.rent = entry?.estimate ?? null;
    item.label = entry?.label ?? "none";
    // No budget: one list, no groups (decision 8). Missing rent keeps its "Not enough data"
    // badge but isn't moved to the bottom: there is no budget it fails to be checked against.
    if (search.budget === null) {
      groups.all.push(item);
      continue;
    }
    if (item.rent === null) {
      groups.noData.push(item);
      continue;
    }
    const g = rentGroup(item.rent, search.budget);
    if (g === "hidden") out.hiddenOverBudget++;
    else groups[g as "fits" | "over"].push(item);
  }

  const order: GroupKey[] = mode === "budget" ? ["fits", "over", "noData"] : ["all"];
  for (const key of order) {
    // Rooms and "not enough data" have no rent to sort by: commute only (decisions 3, 5). In
    // one no-budget list sorted by rent, unknown rents come last (byRent).
    const cmp = sort === "rent" && !room && key !== "noData" ? byRent : byCommute;
    if (groups[key].length) out.groups.push({ key, items: groups[key].sort(cmp) });
  }
  return out;
}
