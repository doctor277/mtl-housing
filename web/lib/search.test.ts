import { describe, expect, it } from "vitest";
import { MAX_COMMUTE_MIN, parseOpen, parseSearch, parseSort, parseView, SEARCH_SIZES, searchQuery } from "./search";

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

  it("accepts any whole number of dollars as a budget", () => {
    for (const budget of ["1", "25", "1475", "1480", "1399"]) {
      expect(parseSearch({ ...ok, budget }, CAMPUSES)).toEqual({
        ok: true,
        search: { campus: "a", size: "1br", budget: Number(budget), maxCommute: 45 },
      });
    }
    const tooBig = ["1000000000000000000000", "10000000000000000001"]; // 1e21; 1e19 + 1 rounds to 1e19
    for (const budget of ["0", "-25", "1500.5", "1,500", "$1500", "abc", "1e3", ...tooBig]) {
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
    expect(parseSearch({ budget: "seven" }, CAMPUSES)).toEqual({
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

  it("adds sort=rent only when it isn't the default", () => {
    const search = { campus: "a", size: "1br" as const, budget: null, maxCommute: 45 as const };
    expect(searchQuery(search, "commute")).toBe("campus=a&size=1br&max=45");
    expect(searchQuery(search, "rent")).toBe("campus=a&size=1br&max=45&sort=rent");
    expect(searchQuery(search, "commute", "map")).toBe("campus=a&size=1br&max=45&view=map");
    expect(searchQuery(search, "rent", "map")).toBe("campus=a&size=1br&max=45&sort=rent&view=map");
  });

  it("leaves the budget out when there is none", () => {
    expect(searchQuery({ campus: "b", size: "room", budget: null, maxCommute: 60 })).toBe(
      "campus=b&size=room&max=60",
    );
  });
});

describe("parseSort", () => {
  it("is fastest commute unless sort=rent", () => {
    expect(parseSort({})).toBe("commute");
    expect(parseSort({ sort: "rent" })).toBe("rent");
    expect(parseSort({ sort: "price" })).toBe("commute");
    expect(parseSort({ sort: ["rent", "rent"] })).toBe("commute");
  });
});

describe("parseView and parseOpen", () => {
  it("shows the cards unless view=map", () => {
    expect(parseView({})).toBe("list");
    expect(parseView({ view: "map" })).toBe("map");
    expect(parseView({ view: "grid" })).toBe("list");
    expect(parseView({ view: ["map", "map"] })).toBe("list");
  });

  it("reads the card to open", () => {
    expect(parseOpen({ open: "A" })).toBe("A");
    expect(parseOpen({})).toBeNull();
  });
});
