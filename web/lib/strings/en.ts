// Every UI string for the site's own pages, in one place (owner's M4 decision 6). M5 adds a
// French file with the same shape (`Strings`). Numbers never go in here as text: they come
// from the data files and are passed in.
//
// Not here yet: the map's legend and popup texts (lib/rent.ts, lib/commute.ts, app/MapView.tsx,
// app/QuartierMap.tsx). They move here in M4.3, when the map becomes the results' second view.

import type { MaxCommute, SearchField, SearchSize } from "../search";

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
    submit: "Show me neighbourhoods",
  },
  form: {
    campus: { legend: "Campus" },
    size: {
      legend: "Size",
      hint: "Room: one room in a shared apartment. 3½: one bedroom. 4½: two bedrooms.",
      labels: { room: "Room", studio: "Studio", "1br": "3½", "2br": "4½" } satisfies Record<
        SearchSize,
        string
      >,
    },
    budget: {
      label: "Budget per month",
      optional: "optional",
      hint: (step: number) => `Steps of $${step}. Leave it empty to sort by commute only.`,
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
    title: "Your search",
    loading: "Loading…",
    budget: (dollars: string) => `up to $${dollars} a month`,
    noBudget: "no budget",
    maxCommute: (min: MaxCommute) => `${min} min max`,
    notBuilt: "The shortlist of neighbourhoods isn’t built yet. It comes in the next version of the site.",
    mapNote: "Until then, the map shows commute times and rents for every neighbourhood.",
    openMap: "Open the map",
    changeSearch: "Change search",
    invalidTitle: "This search can’t be used",
    invalid: {
      campus: "Pick one of the campuses.",
      size: "Pick a size: room, studio, 3½ or 4½.",
      budget: (step: number) => `The budget must be whole dollars in steps of $${step}, or left empty.`,
      maxCommute: (options: readonly number[]) =>
        `Pick a max commute: ${orList(options.map(String))} min.`,
    } satisfies Record<SearchField, unknown>,
  },
};

export type Strings = typeof en;
