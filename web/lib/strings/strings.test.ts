import { describe, expect, it } from "vitest";
import { formatDollars } from "../rent";
import { BUDGET_EXAMPLE, BUDGET_STEP, MAX_COMMUTE_MIN, parseSearch, SEARCH_SIZES } from "../search";
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

  it("takes the budget step and the commute buttons from the code, not typed text", () => {
    expect(strings.form.budget.hint(formatDollars(BUDGET_EXAMPLE))).toBe(
      "e.g. 1,400. Leave it empty to sort by commute only.",
    );
    expect(parseSearch({ campus: "a", size: "1br", budget: String(BUDGET_EXAMPLE), max: "45" }, ["a"]).ok).toBe(
      true,
    );
    expect(strings.results.invalid.budget(BUDGET_STEP)).toContain("steps of $25");
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
    expect(strings.detail.manyUnreachable("15%", 120)).toContain("more than 120 min");
    expect(strings.results.groupHint.over(10)).toBe("Up to 10% over your budget.");
    expect(strings.results.noneFits(2, 30, 10)).toContain("more than 10% over");
    expect(strings.detail.signedMin(1.9)).toBe("+1.9 min");
    expect(strings.detail.signedMin(-2.4)).toBe("−2.4 min");
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
