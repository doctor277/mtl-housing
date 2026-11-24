import { describe, expect, it } from "vitest";
import { BUDGET_EXAMPLE, EXAMPLE_SEARCH, MAX_COMMUTE_MIN, parseSearch, SEARCH_SIZES, searchQuery } from "../search";
import { strings } from ".";

describe("strings", () => {
  it("labels every size and every max-commute button", () => {
    expect(SEARCH_SIZES.map((s) => strings.form.size.labels[s])).toEqual(["Room", "Studio", "3½", "4½"]);
    expect(MAX_COMMUTE_MIN.map((m) => strings.form.maxCommute.option(m))).toEqual([
      "20 min",
      "30 min",
      "45 min",
      "60 min",
    ]);
  });

  it("puts the departure window from the data into the commute hint", () => {
    expect(strings.form.maxCommute.hint("7:30", "8:30")).toContain("leaving 7:30–8:30");
  });

  it("takes the budget example and the commute buttons from the code, not typed text", () => {
    expect(strings.form.budget.hint(strings.format.dollars(BUDGET_EXAMPLE))).toBe(
      "e.g. 1,500. Leave it empty to sort by commute only.",
    );
    expect(parseSearch({ campus: "a", size: "1br", budget: String(BUDGET_EXAMPLE), max: "45" }, ["a"]).ok).toBe(
      true,
    );
    expect(strings.results.invalid.maxCommute(MAX_COMMUTE_MIN)).toBe("Pick a max commute: 20, 30, 45 or 60 min.");
    expect(strings.results.invalid.maxCommute([15, 90])).toBe("Pick a max commute: 15 or 90 min.");
  });

  it("says how many neighbourhoods are hidden for missing commute data (decision 4)", () => {
    expect(strings.results.hiddenNoCommute(1, "Z")).toBe(
      "1 neighbourhood is not shown: there is no commute data to Z for it.",
    );
    expect(strings.results.hiddenNoCommute(2, "Z")).toBe(
      "2 neighbourhoods are not shown: there is no commute data to Z for them.",
    );
  });

  it("takes limits and percentages as numbers, never typed", () => {
    expect(strings.detail.manyUnreachable("15%", 120)).toBe("15% of homes here are more than 2 hours away by transit.");
    expect(strings.detail.overMax(90)).toBe("more than 90 min");
    expect(strings.detail.overMax(60)).toBe("more than 1 hour");
    expect(strings.results.groupHint.over(10)).toBe("Up to 10% over your budget.");
    expect(strings.results.noneFits(3, 30, 10)).toBe("The 3 neighbourhoods within 30 min are all more than 10% over your budget.");
    expect(strings.results.hiddenOverBudget(4, 10)).toBe("4 more neighbourhoods are more than 10% over your budget.");
    expect(strings.results.hiddenOverBudget(1, 10)).toBe("1 more neighbourhood is more than 10% over your budget.");
  });

  it("keeps the owner's M4.2 wording for the commute detail", () => {
    expect(strings.detail.median(27, strings.detail.toClosestBuilding("UdeM"), "7:30", "8:30")).toBe(
      "About 27 min door to door, to the closest UdeM building, on a typical weekday morning (leaving 7:30–8:30).",
    );
    expect(strings.detail.range(20, 37, 120)).toBe("Depending on where you live here: 20–37 min for most homes.");
    expect(strings.detail.range(27, 27, 120)).toBe("Depending on where you live here: 27 min for most homes.");
    expect(strings.detail.range(40, null, 120)).toBe(
      "Depending on where you live here: 40 min to more than 2 hours for most homes.",
    );
    expect(
      strings.detail.buildings([
        { name: "Roger-Gaudry", time: "27 min" },
        { name: "Jean-Brillant", time: "28 min" },
      ]),
    ).toBe("Roger-Gaudry: 27 min · Jean-Brillant: 28 min");
    expect(strings.detail.lowSample(2)).toBe("Few homes sampled here (2), so this is less certain.");
    expect(strings.results.cheapest("Quartier A", "≈ $1,650")).toBe("Cheapest: Quartier A, ≈ $1,650.");
    expect(strings.results.sort.label).toBe("Sort by");
  });

  it("builds the map's commute class labels from the class edges and the routing limit", () => {
    expect(strings.commute.classLabels([20, 30, 45, 60, 90], 120)).toEqual([
      "≤ 20 min",
      "21–30",
      "31–45",
      "46–60",
      "61–90",
      "91–120",
    ]);
  });

  it("writes the footer data line and How it works dates from the data", () => {
    expect(strings.format.longDate("2026-12-01")).toBe("Tuesday, December 1, 2026");
    expect(strings.footer.dataLine("Tuesday, December 1, 2026", "October 2025", "2026 Q2")).toBe(
      "Data: STM, REM and exo transit schedules for Tuesday, December 1, 2026; rents from CMHC (October 2025) and Statistics Canada’s experimental asking rents (2026 Q2). Estimates, not listings.",
    );
    expect(strings.format.andList(["A", "B", "C"])).toBe("A, B and C");
    expect(strings.example.label("UdeM", "3½", 1500, 45)).toBe("UdeM, 3½, $1,500, 45 min");
  });

  it("keeps the owner's example search valid", () => {
    expect(EXAMPLE_SEARCH).toEqual({ campus: "udem", size: "1br", budget: 1500, maxCommute: 45 });
    const params = Object.fromEntries(new URLSearchParams(searchQuery(EXAMPLE_SEARCH)));
    expect(parseSearch(params, ["udem"])).toEqual({ ok: true, search: EXAMPLE_SEARCH });
  });

  it("keeps the owner's first-screen wording", () => {
    expect(strings.home.title).toBe("Find where to live in Montréal without a car");
    expect(strings.home.intro(91)).toBe(
      "Compare transit commute times and typical rents across 91 Montréal neighbourhoods.",
    );
    expect(strings.form.size.hint).toContain("Studio: 1½–2½.");
    expect(strings.home.submit).toBe("Show me neighbourhoods");
  });
});
