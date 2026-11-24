// Every UI string of the site, in one place (owner's M4 decision 6), map and rent lines
// included. M5 adds a French file with the same shape (`Strings`). Numbers never go in here
// as text: they come from the data files or the code and are passed in. Number formats
// ("1,475", "≈ $1,475") are language-specific, so they live here too.

import type { TimeBlock, TimeStat } from "../commute";
import type { BedroomType, LabelKey, RentEntry, RentMeta } from "../rent";
import { isLowReliability } from "../rent";
import type { MaxCommute, SearchField, SearchSize } from "../search";

/** "1,475" (en-CA grouping, no locale dependency). */
function dollars(x: number): string {
  return String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** "≈ $1,475": an estimate (rent.json rents are rounded to $25). */
function rentAbout(x: number): string {
  return `≈ $${dollars(x)}`;
}

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

/** "a, b and c". */
function andList(items: string[]): string {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

const wholePct = (share: number) => `${Math.round(share * 100)}%`;
const oneDecimalPct = (share: number) => `${(share * 100).toFixed(1)}%`;

/** Short campus names for pickers and sentences; any other campus uses its full name. */
const CAMPUS_SHORT: Record<string, string> = {
  udem: "UdeM",
  mcgill: "McGill",
  concordia_sgw: "Concordia SGW",
};

const SIZE_LABELS = { room: "Room", studio: "Studio", "1br": "3½", "2br": "4½" } satisfies Record<SearchSize, string>;

// --- rent lines (approved wording: docs/methodology.md, Rent, "What the site shows") ----------

const BADGES: Record<LabelKey, string> = {
  neighbourhood: "Estimate",
  zone: "Wider-area estimate",
  neighbourhood_low: "Low reliability",
  zone_low: "Low reliability",
  none: "Not enough data",
};

/** Main CMHC line. One CMHC area or zone: the approved text. Several (a neighbourhood split
 * between CMHC areas): the rating moves to the split line, per area, because the label's
 * worst grade isn't every area's rating. "Adjusted to current asking rents" is said once, in
 * the source line (owner, M4.3). */
function detailLine(e: RentEntry, meta: RentMeta): string {
  const words = meta.grade_words;
  const period = meta.cmhc.period;
  const areas = e.cmhc_areas;
  if (e.label === "none") return "CMHC doesn’t publish a reliable rent for this size here or nearby.";
  const zone = areas[0]?.type === "zone";
  if (areas.length === 1) {
    const name = areas[0].name;
    const word = words[areas[0].grade];
    switch (e.label) {
      case "neighbourhood":
        return `Based on CMHC’s average rent in CMHC area ${name} (${period}, rated ${word} by CMHC).`;
      case "zone":
        return `CMHC has no reliable figure for this area, so this uses the wider CMHC zone ${name} (rated ${word} by CMHC).`;
      case "neighbourhood_low":
        return `Based on CMHC’s average rent in CMHC area ${name}, which CMHC rates “use with caution”.`;
      case "zone_low":
        return `Based on the wider CMHC zone ${name}, which CMHC rates “use with caution”.`;
    }
  }
  const kind = zone ? "CMHC zones" : "CMHC areas";
  const names = andList(areas.map((a) => a.name));
  if (isLowReliability(e.label)) {
    return `Based on CMHC’s average rents in ${kind} ${names}; CMHC rates at least one of them “use with caution”.`;
  }
  return `Based on CMHC’s average rents in ${kind} ${names} (${period}).`;
}

/** Extra lines: the split (raw shares, per-area rating) and the coverage. */
function extraLines(e: RentEntry, meta: RentMeta): string[] {
  const words = meta.grade_words;
  const areas = e.cmhc_areas;
  const lines: string[] = [];
  const partial = e.coverage_pct !== null;
  const kind = areas[0]?.type === "zone" ? "CMHC zones" : "CMHC areas";
  if (areas.length > 1) {
    const rated = (g: string) => (g === "d" ? `rated “${words[g]}”` : `rated ${words[g]}`);
    const parts = areas.map(
      (a) => `${a.name} (${partial ? oneDecimalPct(a.share) : wholePct(a.share)}, ${rated(a.grade)})`,
    );
    lines.push(`Weighted average of ${kind} ${andList(parts)}, by rental units.`);
  }
  if (partial) {
    const shares = areas.length === 1 ? ` (${areas[0].name}: ${oneDecimalPct(areas[0].share)})` : "";
    lines.push(
      `Covers ${e.coverage_pct}% of this neighbourhood’s rental units${shares}; CMHC has no reliable figure for the rest.`,
    );
  }
  return lines;
}

/** Legend text per rent class, in dollars. Rents are multiples of `step`, so the upper bound
 * of a class is the next edge minus one step. */
function rentClassRanges(edges: number[], step: number): string[] {
  const out = [`under $${dollars(edges[0])}`];
  for (let i = 0; i < edges.length - 1; i++) out.push(`$${dollars(edges[i])}–$${dollars(edges[i + 1] - step)}`);
  out.push(`$${dollars(edges[edges.length - 1])} or more`);
  return out;
}

/** "< 85%", "85–95%", …, "> 130%" from the class edges as fractions (lib/rent.ts BIN_PCT). */
function rentClassPct(binPct: number[]): string[] {
  const p = binPct.map((x) => Math.round(x * 100));
  return [`< ${p[0]}%`, ...p.slice(1).map((x, i) => `${p[i]}–${x}%`), `> ${p[p.length - 1]}%`];
}

// --- commute lines ------------------------------------------------------------------------

/** "44 min", "> 120 min" or "no data". */
function commuteTime(block: TimeBlock, stat: TimeStat, maxTripMin: number): string {
  const v = block[stat];
  if (v !== null) return `${Math.round(v)} min`;
  return block.over_max.includes(stat) ? `> ${maxTripMin} min` : "no data";
}

/** Commute classes from their upper bounds in minutes: "≤ 20 min", "21–30", …, "91–120". */
function commuteClassLabels(uppers: number[], maxTripMin: number): string[] {
  const all = [...uppers, maxTripMin];
  return [`≤ ${all[0]} min`, ...all.slice(1).map((u, i) => `${all[i] + 1}–${u}`)];
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
  format: {
    dollars,
    rent: rentAbout,
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
      labels: SIZE_LABELS,
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
    budget: (amount: string) => `up to $${amount} a month`,
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
      budget: "The budget must be a whole number of dollars, or left empty.",
      maxCommute: (options: readonly number[]) =>
        `Pick a max commute: ${orList(options.map(String))} min.`,
    } satisfies Record<SearchField, unknown>,
  },
  /** A shortlist card and its detail panel. */
  card: {
    minutes: (min: number) => `${min} min`,
    perMonth: (rent: string) => `${rent} a month`,
  },
  detail: {
    commuteHeading: "Commute",
    /** Owner's wording. The schedule date and the access adjustments are explained in How it
     * works, not here. */
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
  /** Rent lines shared by the map and the detail panel. */
  rent: {
    badges: BADGES,
    detailLine,
    extraLines,
    /** The line under every estimate (owner's wording, M3). */
    sourceLine:
      "Estimate based on average rents, adjusted to current Montréal asking rents. Not a listing, and possibly low in areas with many long-time tenants.",
    /** The two data dates. */
    dataLine: (meta: RentMeta) =>
      `Data: CMHC (${meta.cmhc.period}) and Statistics Canada’s experimental asking rents (${meta.statcan.quarter}).`,
    roomLine: (meta: RentMeta) =>
      `Room: ${rentAbout(meta.room.estimate)} a month: Montréal-wide average asking rent for a room, not specific to this neighbourhood (Statistics Canada, ${meta.statcan.quarter}).`,
    classRanges: rentClassRanges,
    classPct: rentClassPct,
    sizeLabel: (size: Exclude<BedroomType, "3br_plus">) => SIZE_LABELS[size],
  },
  /** Commute wording shared by the map, the cards and the form. */
  commute: {
    campusShort: (id: string, fullName: string) => CAMPUS_SHORT[id] ?? fullName,
    time: commuteTime,
    /** "leaving 7:30–8:30, Tue 2026-12-01". */
    window: (start: string, end: string, isoDate: string) => {
      // Noon UTC avoids a time-zone shift to the previous day.
      const day = new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("en-CA", { weekday: "short", timeZone: "UTC" });
      return `leaving ${start}–${end}, ${day} ${isoDate}`;
    },
    /** What the time is measured to: "to Roddick Gates" for one destination, "fastest UdeM
     * building" when several buildings count (the faster one per home). */
    target: (campusShort: string, destinations: { name: string }[]) =>
      destinations.length === 1 ? `to ${destinations[0].name}` : `fastest ${campusShort} building`,
    classLabels: commuteClassLabels,
  },
  /** The map: /map (all neighbourhoods) and the results' map view. */
  map: {
    group: "Map",
    modes: { commute: "Commute", rent: "Rent" },
    campus: "Campus",
    size: "Size",
    hideLegend: "Hide legend",
    showLegend: "Show legend",
    loadingCommutes: "Loading commutes…",
    loadingRents: "Loading rents…",
    loadingMap: "Loading the map…",
    commuteTitle: (campusName: string) => `Median transit commute to ${campusName}`,
    overMaxClass: (max: number) => `> ${max} min`,
    noData: "no data",
    noResidents: "no residents (park)",
    rentTitle: (size: string) => `Estimated rent, ${size}`,
    /** A published StatCan figure, shown as is (no "≈"). */
    rentBasis: (level: number) => `compared with the Montréal asking rent ($${dollars(level)}, Statistics Canada)`,
    rentClass: (pct: string, range: string) => `${pct}: ${range}`,
    lowReliability: "low reliability (CMHC: “use with caution”)",
    notEnoughData: "not enough data",
    clickHint: "Click a neighbourhood for details.",
    attribution: (withRent: boolean) =>
      `Quartiers: Ville de Montréal (CC BY 4.0). Schedules: STM, REM, exo (CC BY 4.0). ${withRent ? "Rents: CMHC, Statistics Canada. " : ""}Map data © OpenStreetMap contributors.`,
    error: (message: string) => `The map couldn’t load: ${message}`,
    marker: (campusName: string, destination: string) => `${campusName}: ${destination}`,
    popup: {
      /** Followed by the time in bold. */
      medianPrefix: (campusName: string, target: string) => `${campusName}, ${target}, median: `,
      range: (p10: string, p90: string) => `p10–p90: ${p10} – ${p90}`,
      access: (signed: string) => `includes a ${signed} access adjustment (platform to entrance)`,
      building: (name: string, time: string, signed: string | null, share: string) =>
        `${name}: ${time}${signed ? ` (incl. ${signed} access adjustment)` : ""}, fastest for ${share} of homes`,
      signedMin: (adj: number) => `${adj > 0 ? "+" : "−"}${Math.abs(adj)} min`,
      sample: (n: number, unreachable: number) => `${n} sample points, ${unreachable} unreachable`,
      flags: (flags: string[]) => `flags: ${flags.length ? flags.join(", ") : "none"}`,
      noRent: (size: string) => `${size}: not enough data`,
      rent: (size: string, perMonth: string | null, badge: string) =>
        `${size}: ${perMonth ? `${perMonth} a month · ` : ""}${badge}`,
      noResidents: (mode: "commute" | "rent") =>
        `No residents, so no ${mode === "rent" ? "rent estimate" : "commute time"} is shown.`,
      partOf: (parent: string) => `In the city’s data this area is part of the ${parent} quartier.`,
      noCommuteData: "no data",
    },
  },
};

export type Strings = typeof en;
