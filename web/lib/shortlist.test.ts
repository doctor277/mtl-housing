import { describe, expect, it } from "vitest";
import type { CampusResult, CommuteFile } from "./commute";
import type { BedroomType, LabelKey, RentEntry, RentFile } from "./rent";
import type { Search } from "./search";
import { type Hood, buildShortlist, rentGroup } from "./shortlist";

// Clearly fake fixtures (CLAUDE.md): quartiers "A", "B", …; campus "z".
const CAMPUS = "z";

function commuteResult(median: number | null, overMax = false): CampusResult {
  return {
    median,
    p10: median,
    p90: median,
    over_max: overMax ? ["median", "p10", "p90"] : [],
    n_points: 10,
    n_unreachable: 0,
    unreachable_share: 0,
    flags: [],
    rule: "fastest_destination",
    by_destination: {},
  };
}

function rentEntry(estimate: number | null, label: LabelKey = estimate === null ? "none" : "neighbourhood"): RentEntry {
  return { estimate, label, grade: null, coverage_pct: null, cmhc_areas: [] };
}

/** One quartier: [id, median commute to Z (or null / "over"), 3½ rent (or null)]. */
type Row = [id: string, commute: number | null | "over" | "absent", rent: number | null];

function fixture(rows: Row[], roomEstimate = 999) {
  const hoods: Hood[] = rows.map(([id]) => ({ id, name: `Quartier ${id}`, borough: "Borough Y" }));
  const commute = {
    meta: { max_trip_min: 120 },
    results: Object.fromEntries(
      rows
        .filter(([, c]) => c !== "absent")
        .map(([id, c]) => [id, { [CAMPUS]: c === "over" ? commuteResult(null, true) : commuteResult(c as number | null) }]),
    ),
  } as unknown as CommuteFile;
  const rent = {
    meta: { room: { estimate: roomEstimate } },
    results: Object.fromEntries(
      rows.map(([id, , r]) => [id, { "1br": rentEntry(r) } as Record<BedroomType, RentEntry>]),
    ),
  } as unknown as RentFile;
  return { hoods, commute, rent };
}

const search = (over: Partial<Search> = {}): Search => ({
  campus: CAMPUS,
  size: "1br",
  budget: 1400,
  maxCommute: 45,
  ...over,
});

const ids = (s: ReturnType<typeof buildShortlist>) =>
  Object.fromEntries(s.groups.map((g) => [g.key, g.items.map((i) => i.id)]));

describe("rentGroup (owner's M4 decision 2: compare the rounded rent the user sees)", () => {
  it("fits exactly at the budget", () => {
    expect(rentGroup(1400, 1400)).toBe("fits");
    expect(rentGroup(1375, 1400)).toBe("fits");
  });

  it("uses the rent as shown, rounded to $25: one step over the budget is over", () => {
    // rent.json holds rents already rounded to $25; ≈ $1,425 against $1,400 is over budget.
    expect(rentGroup(1425, 1400)).toBe("over");
    // Budgets can be any whole dollar (owner, M4.3); the rent compared is still the rounded one.
    expect(rentGroup(1400, 1410)).toBe("fits");
    expect(rentGroup(1425, 1410)).toBe("over");
    expect(rentGroup(1400, 1399)).toBe("over");
  });

  it("puts just under and exactly 10% over as slightly over, just over 10% as hidden", () => {
    // $1,500 budget: 10% over is $1,650.
    expect(rentGroup(1625, 1500)).toBe("over");
    expect(rentGroup(1650, 1500)).toBe("over");
    expect(rentGroup(1675, 1500)).toBe("hidden");
    // $1,325 budget: 10% over is $1,457.50, so $1,450 is in and $1,475 is out.
    expect(rentGroup(1450, 1325)).toBe("over");
    expect(rentGroup(1475, 1325)).toBe("hidden");
  });

  it("can't check a missing rent", () => {
    expect(rentGroup(null, 1400)).toBe("noData");
  });
});

describe("buildShortlist", () => {
  it("groups by budget: fits, then slightly over, then not enough data", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 20, 1400], // exactly at budget
      ["B", 25, 1500], // slightly over (≤ 1540)
      ["C", 30, 1550], // more than 10% over: hidden
      ["D", 35, null], // not enough data
      ["E", 40, 1200],
    ]);
    const s = buildShortlist(hoods, commute, rent, search(), "commute");
    expect(s.mode).toBe("budget");
    expect(ids(s)).toEqual({ fits: ["A", "E"], over: ["B"], noData: ["D"] });
    expect(s.hiddenOverBudget).toBe(1);
    expect(s.cheapestHidden).toEqual({ name: "Quartier C", rent: 1550 });
  });

  it("with no budget: one list by commute, no groups; 'Not enough data' stays in commute order", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 15, null],
      ["B", 20, 2500],
      ["C", 25, 900],
    ]);
    const s = buildShortlist(hoods, commute, rent, search({ budget: null }), "commute");
    expect(s.mode).toBe("noBudget");
    expect(ids(s)).toEqual({ all: ["A", "B", "C"] });
    expect(s.groups[0].items[0]).toMatchObject({ id: "A", rent: null, label: "none" });
    expect(s.hiddenOverBudget).toBe(0);
    // No budget means commute order (decision 8), even if sort=rent is in the URL.
    expect(ids(buildShortlist(hoods, commute, rent, search({ budget: null }), "rent"))).toEqual({ all: ["A", "B", "C"] });
  });

  it("is a hard max-commute filter for everyone, on the minutes shown (rounded)", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 45.4, 1000], // shows "45 min": in
      ["B", 45.6, 1000], // shows "46 min": out
      ["C", 50, null], // no rent data doesn't exempt it
      ["D", "over", 1000], // more than 2 h: too far, not missing
    ]);
    const s = buildShortlist(hoods, commute, rent, search(), "commute");
    expect(ids(s)).toEqual({ fits: ["A"] });
    expect(s.tooFar).toBe(3);
    expect(s.hiddenNoCommute).toBe(0);
  });

  it("hides neighbourhoods with missing commute data and counts them", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 20, 1000],
      ["B", null, 1000], // routed, no result
      ["C", "absent", 1000], // not in commute.json for this campus
    ]);
    const s = buildShortlist(hoods, commute, rent, search(), "commute");
    expect(ids(s)).toEqual({ fits: ["A"] });
    expect(s.hiddenNoCommute).toBe(2);
  });

  it("sorts by commute within each group, then by name", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 30, 1000],
      ["B", 10, 1300],
      ["C", 30, 1100], // ties with A on commute: name order
      ["D", 40, 1500],
      ["E", 20, 1450],
      ["F", 44, null],
      ["G", 5, null],
    ]);
    const s = buildShortlist(hoods, commute, rent, search(), "commute");
    expect(ids(s)).toEqual({ fits: ["B", "A", "C"], over: ["E", "D"], noData: ["G", "F"] });
  });

  it("sorts by rent within each group when asked, ties by commute; no-data stays by commute", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 30, 1000],
      ["B", 10, 1300],
      ["C", 5, 1000], // ties with A on rent: faster first
      ["D", 40, 1500],
      ["E", 20, 1450],
      ["F", 44, null],
      ["G", 5, null],
    ]);
    const s = buildShortlist(hoods, commute, rent, search(), "rent");
    expect(ids(s)).toEqual({ fits: ["C", "A", "B"], over: ["E", "D"], noData: ["G", "F"] });
  });

  it("rooms: no budget filter, sorted by commute only, warning when the budget is under the room figure", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 30, 2000],
      ["B", 10, null],
      ["C", 20, 900],
    ]);
    const low = buildShortlist(hoods, commute, rent, search({ size: "room", budget: 975 }), "rent");
    expect(low.mode).toBe("room");
    expect(ids(low)).toEqual({ all: ["B", "C", "A"] }); // every one, by commute, "rent" sort ignored
    expect(low.roomWarning).toBe(true);
    expect(low.roomEstimate).toBe(999);
    expect(low.hiddenOverBudget).toBe(0);

    expect(buildShortlist(hoods, commute, rent, search({ size: "room", budget: 999 }), "commute").roomWarning).toBe(false);
    expect(buildShortlist(hoods, commute, rent, search({ size: "room", budget: null }), "commute").roomWarning).toBe(false);
  });

  it("drops empty groups and reports how many passed the commute filter", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 20, 3000],
      ["B", 60, 1000],
    ]);
    const s = buildShortlist(hoods, commute, rent, search(), "commute");
    expect(s.groups).toEqual([]);
    expect(s.withinCommute).toBe(1);
    expect(s.hiddenOverBudget).toBe(1);
    expect(s.cheapestHidden).toEqual({ name: "Quartier A", rent: 3000 });
  });

  it("names the cheapest neighbourhood hidden for budget, then the faster one", () => {
    const { hoods, commute, rent } = fixture([
      ["A", 30, 2000],
      ["B", 20, 1800],
      ["C", 10, 1800], // same rent as B, faster
      ["D", 40, 1000], // fits
    ]);
    const s = buildShortlist(hoods, commute, rent, search(), "commute");
    expect(s.hiddenOverBudget).toBe(3);
    expect(s.cheapestHidden).toEqual({ name: "Quartier C", rent: 1800 });
    expect(buildShortlist(hoods, commute, rent, search({ budget: null }), "commute").cheapestHidden).toBeNull();
  });

  it("carries what a card shows: rounded minutes, rent and its label", () => {
    const { hoods, commute, rent } = fixture([["A", 31.6, 1375]]);
    const [item] = buildShortlist(hoods, commute, rent, search(), "commute").groups[0].items;
    expect(item).toMatchObject({ id: "A", name: "Quartier A", minutes: 32, rent: 1375, label: "neighbourhood" });
  });
});
