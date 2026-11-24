import { describe, expect, it } from "vitest";
import { BUDGET_STEP, MAX_COMMUTE_MIN, SEARCH_SIZES } from "../search";
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
    expect(strings.form.budget.hint(BUDGET_STEP)).toBe("Steps of $25. Leave it empty to sort by commute only.");
    expect(strings.form.budget.hint(50)).toContain("Steps of $50.");
    expect(strings.results.invalid.budget(BUDGET_STEP)).toContain("steps of $25");
    expect(strings.results.invalid.maxCommute(MAX_COMMUTE_MIN)).toBe("Pick a max commute: 20, 30, 45 or 60 min.");
    expect(strings.results.invalid.maxCommute([15, 90])).toBe("Pick a max commute: 15 or 90 min.");
  });

  it("keeps the owner's first-screen wording", () => {
    expect(strings.home.title).toBe("Find where to live in Montréal without a car");
    expect(strings.home.submit).toBe("Show me neighbourhoods");
  });
});
