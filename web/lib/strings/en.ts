// Every UI string for the site's own pages, in one place (owner's M4 decision 6). M5 adds a
// French file with the same shape (`Strings`). Numbers never go in here as text: they come
// from the data files and are passed in.
//
// Not here yet: the map's legend and popup texts (lib/rent.ts, lib/commute.ts, app/MapView.tsx,
// app/QuartierMap.tsx). They move here in M4.3, when the map becomes the results' second view.

import type { MaxCommute, SearchField, SearchSize } from "../search";

/** "more than 2 hours" for the routing limit in minutes (commute.json max_trip_min). */
function overMax(maxMin: number): string {
  if (maxMin % 60 !== 0) return `more than ${maxMin} min`;
  const h = maxMin / 60;
  return `more than ${h} ${h === 1 ? "hour" : "hours"}`;
}

/** "a, b or c": an English list joined with "or" (no serial comma). */
function orList(items: string[]): string {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} or ${items.at(-1)}`;
}

export const en = {
  lang: "en",
  /** Placeholder until the name is chosen (M6). */
  siteName: "[NAME]",
  meta: {
    title: "[NAME]: where to live in Montréal without a car",
    description:
      "Pick your campus, apartment size, budget and longest commute, and see which Montréal neighbourhoods fit.",
    mapTitle: "[NAME]: map of commutes and rents",
  },
  home: {
    title: "Find where to live in Montréal without a car",
    /** `count`: the neighbourhoods in commute.json. */
    intro: (count: number) =>
      `Compare transit commute times and typical rents across ${count} Montréal neighbourhoods.`,
    submit: "Show me neighbourhoods",
  },
  form: {
    campus: { legend: "Campus" },
    size: {
      legend: "Size",
      hint: "Room: one room in a shared apartment. Studio: 1½–2½. 3½: one bedroom. 4½: two bedrooms.",
      labels: { room: "Room", studio: "Studio", "1br": "3½", "2br": "4½" } satisfies Record<
        SearchSize,
        string
      >,
    },
    budget: {
      label: "Budget per month",
      optional: "optional",
      /** `example`: BUDGET_EXAMPLE, already formatted ("1,400"). */
      hint: (example: string) => `e.g. ${example}. Leave it empty to sort by commute only.`,
      prefix: "$",
    },
    maxCommute: {
      legend: "Max commute",
      hint: (start: string, end: string) =>
        `Typical transit trip to campus, walking included, leaving ${start}–${end} on a weekday morning.`,
      option: (min: MaxCommute) => `${min} min`,
    },
  },
  results: {
    title: "Neighbourhoods",
    loading: "Loading…",
    budget: (dollars: string) => `up to $${dollars} a month`,
    noBudget: "no budget",
    maxCommute: (min: MaxCommute) => `${min} min max`,
    changeSearch: "Change search",
    update: "Update",
    sort: { label: "Sort by", commute: "Fastest commute", rent: "Cheapest rent" },
    /** Above the list: the cards only badge real caveats (owner, M4.2). */
    allEstimates: "All rents are estimates.",
    /** Group headings ("all": no budget, or rooms; read by screen readers only). Owner's words for "over" and "noData". */
    groups: {
      /** Screen-reader heading for the one list (no budget, or rooms). */
      all: "Shortlist",
      fits: "Within your budget",
      over: "Slightly over budget",
      noData: "Not enough data",
    },
    groupHint: {
      over: (pct: number) => `Up to ${pct}% over your budget.`,
      noData: "We can’t check these against your budget: there isn’t enough rent data for this size.",
    },
    showMore: (n: number) => `Show ${n} more`,
    showFewer: "Show fewer",
    /** Owner's wording (M4 decision 5); the figure comes from rent.json. */
    roomNote: (rent: string) => `Room rent: ${rent} citywide, same estimate everywhere`,
    roomWarning: (rent: string) =>
      `Typical room rent (${rent}) is above your budget, and we can’t tell where cheaper rooms are.`,
    hiddenNoCommute: (n: number, campus: string) =>
      `${n} ${n === 1 ? "neighbourhood is" : "neighbourhoods are"} not shown: there is no commute data to ${campus} for ${n === 1 ? "it" : "them"}.`,
    noneWithin: (max: number, campus: string) => `No neighbourhood is within ${max} min of ${campus}.`,
    tryLonger: "Try a longer max commute.",
    noCommuteData: (campus: string) => `There is no commute data to ${campus} for these neighbourhoods.`,
    noneFits: (n: number, max: number, pct: number) =>
      n === 1
        ? `The one neighbourhood within ${max} min is more than ${pct}% over your budget.`
        : `The ${n} neighbourhoods within ${max} min are all more than ${pct}% over your budget.`,
    cheapest: (name: string, rent: string) => `Cheapest: ${name}, ${rent}.`,
    hiddenOverBudget: (n: number, pct: number) =>
      n === 1
        ? `1 more neighbourhood is more than ${pct}% over your budget.`
        : `${n} more neighbourhoods are more than ${pct}% over your budget.`,
    tryBudget: (n: number) =>
      n === 1 ? "Try a higher budget, or leave it empty to see it." : "Try a higher budget, or leave it empty to see them all.",
    openMap: "See every neighbourhood on the map",
    invalidTitle: "This search can’t be used",
    invalid: {
      campus: "Pick one of the campuses.",
      size: "Pick a size: room, studio, 3½ or 4½.",
      budget: (step: number) => `The budget must be whole dollars in steps of $${step}, or left empty.`,
      maxCommute: (options: readonly number[]) =>
        `Pick a max commute: ${orList(options.map(String))} min.`,
    } satisfies Record<SearchField, unknown>,
  },
  /** A shortlist card and its detail panel. Rent texts (badges, CMHC lines, source line) are
   * the approved ones in lib/rent.ts. */
  card: {
    minutes: (min: number) => `${min} min`,
    perMonth: (rent: string) => `${rent} a month`,
  },
  detail: {
    commuteHeading: "Commute",
    /** Owner's wording. The schedule date and the access adjustments are explained in How it
     * works (M4.3), not here. */
    median: (min: number, target: string, start: string, end: string) =>
      `About ${min} min door to door, ${target}, on a typical weekday morning (leaving ${start}–${end}).`,
    toClosestBuilding: (campus: string) => `to the closest ${campus} building`,
    toPlace: (name: string) => `to ${name}`,
    /** 10th to 90th percentile in whole minutes; null = over the routing limit. */
    range: (lo: number, hi: number | null, maxMin: number) =>
      `Depending on where you live here: ${hi === null ? `${lo} min to ${overMax(maxMin)}` : lo === hi ? `${lo} min` : `${lo}–${hi} min`} for most homes.`,
    /** "Roger-Gaudry: 27 min · Jean-Brillant: 28 min" (names as in commute.json). */
    buildings: (parts: { name: string; time: string }[]) => parts.map((p) => `${p.name}: ${p.time}`).join(" · "),
    overMax: (maxMin: number) => overMax(maxMin),
    lowSample: (n: number) => `Few homes sampled here (${n}), so this is less certain.`,
    manyUnreachable: (pct: string, maxMin: number) =>
      `${pct} of homes here are ${overMax(maxMin)} away by transit.`,
    commuteSource:
      "Travel times are derived from STM, REM and exo schedules (CC BY 4.0). Schedules don’t include delays or outages.",
    rentHeading: (size: string) => `Rent, ${size}`,
  },
};

export type Strings = typeof en;
