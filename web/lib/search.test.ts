import { describe, expect, it } from "vitest";
import { BUDGET_STEP, MAX_COMMUTE_MIN, parseSearch, SEARCH_SIZES, searchQuery } from "./search";

// Fake campus ids: the parser only checks membership in the list it is given.
const CAMPUSES = ["a", "b"];
const ok = { campus: "a", size: "1br", budget: "1500", max: "45" };

describe("parseSearch", () => {
  it("accepts a full search", () => {
    expect(parseSearch(ok, CAMPUSES)).toEqual({
      ok: true,
      search: { campus: "a", size: "1br", budget: 1500, maxCommute: 45 },
    });
  });

  it("treats a missing or empty budget as no budget", () => {
    for (const budget of [undefined, "", "  "]) {
      const r = parseSearch({ ...ok, budget }, CAMPUSES);
      expect(r).toEqual({ ok: true, search: { campus: "a", size: "1br", budget: null, maxCommute: 45 } });
    }
  });

  it("accepts every size the form offers, room included", () => {
    expect(SEARCH_SIZES).toEqual(["room", "studio", "1br", "2br"]);
    for (const size of SEARCH_SIZES) expect(parseSearch({ ...ok, size }, CAMPUSES).ok).toBe(true);
  });

  it("accepts every max-commute button and nothing else", () => {
    expect(MAX_COMMUTE_MIN).toEqual([20, 30, 45, 60]);
    for (const max of MAX_COMMUTE_MIN) expect(parseSearch({ ...ok, max: String(max) }, CAMPUSES).ok).toBe(true);
    for (const max of ["25", "90", "0", "45.0", "x", ""]) {
      expect(parseSearch({ ...ok, max }, CAMPUSES)).toEqual({ ok: false, errors: ["maxCommute"] });
    }
  });

  it("accepts budgets in $25 steps only", () => {
    expect(BUDGET_STEP).toBe(25);
    expect(parseSearch({ ...ok, budget: "25" }, CAMPUSES).ok).toBe(true);
    expect(parseSearch({ ...ok, budget: "1475" }, CAMPUSES).ok).toBe(true);
    const tooBig = ["1000000000000000000000", "10000000000000000001"]; // 1e21; 1e19 + 1 rounds to 1e19
    for (const budget of ["1480", "0", "-25", "1500.5", "1,500", "$1500", "abc", "1e3", ...tooBig]) {
      expect(parseSearch({ ...ok, budget }, CAMPUSES)).toEqual({ ok: false, errors: ["budget"] });
    }
  });

  it("rejects an unknown or missing campus or size", () => {
    expect(parseSearch({ ...ok, campus: "z" }, CAMPUSES)).toEqual({ ok: false, errors: ["campus"] });
    expect(parseSearch({ ...ok, campus: undefined }, CAMPUSES)).toEqual({ ok: false, errors: ["campus"] });
    expect(parseSearch({ ...ok, size: "3br_plus" }, CAMPUSES)).toEqual({ ok: false, errors: ["size"] });
  });

  it("rejects a repeated parameter instead of picking one", () => {
    expect(parseSearch({ ...ok, campus: ["a", "b"] }, CAMPUSES)).toEqual({ ok: false, errors: ["campus"] });
    expect(parseSearch({ ...ok, budget: ["1500", "1600"] }, CAMPUSES)).toEqual({ ok: false, errors: ["budget"] });
  });

  it("lists every problem at once, in form order", () => {
    expect(parseSearch({}, CAMPUSES)).toEqual({ ok: false, errors: ["campus", "size", "maxCommute"] });
    expect(parseSearch({ budget: "7" }, CAMPUSES)).toEqual({
      ok: false,
      errors: ["campus", "size", "budget", "maxCommute"],
    });
  });
});

describe("searchQuery", () => {
  it("writes the form's own parameter names, and round-trips", () => {
    const search = { campus: "a", size: "2br" as const, budget: 1500, maxCommute: 30 as const };
    expect(searchQuery(search)).toBe("campus=a&size=2br&budget=1500&max=30");
    const params = Object.fromEntries(new URLSearchParams(searchQuery(search)));
    expect(parseSearch(params, CAMPUSES)).toEqual({ ok: true, search });
  });

  it("leaves the budget out when there is none", () => {
    expect(searchQuery({ campus: "b", size: "room", budget: null, maxCommute: 60 })).toBe(
      "campus=b&size=room&max=60",
    );
  });
});

describe("budget step", () => {
  it("matches the rounding step of the rents in rent.json (budgets compare with rounded rents)", async () => {
    const { readFile } = await import("node:fs/promises");
    const rent = JSON.parse(await readFile(new URL("../public/data/rent.json", import.meta.url), "utf-8"));
    expect(rent.meta.rounding.step).toBe(BUDGET_STEP);
  });
});
