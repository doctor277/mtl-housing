import { describe, expect, it } from "vitest";
import { alternates, pageAt, PATHS, switchPath } from "./routes";

describe("pages in two languages (owner, M5 decision 7)", () => {
  it("French is at the root, English under /en", () => {
    expect(PATHS.fr.home).toBe("/");
    expect(PATHS.en.home).toBe("/en");
    expect(Object.values(PATHS.en).every((p) => p === "/en" || p.startsWith("/en/"))).toBe(true);
    expect(Object.values(PATHS.fr).some((p) => p.startsWith("/en"))).toBe(false);
  });

  it("knows which page and language a path is", () => {
    expect(pageAt("/resultats")).toEqual({ lang: "fr", page: "results" });
    expect(pageAt("/en/results/")).toEqual({ lang: "en", page: "results" });
    expect(pageAt("/")).toEqual({ lang: "fr", page: "home" });
    expect(pageAt("/nowhere")).toBeNull();
  });

  it("switching keeps the search on the results page", () => {
    const q = "?campus=a&size=1br&max=45&sort=rent&view=map";
    expect(switchPath("/resultats", q)).toBe(`/en/results${q}`);
    expect(switchPath("/en/results", q)).toBe(`/resultats${q}`);
  });

  it("switching the other pages goes to their twin", () => {
    expect(switchPath("/", "")).toBe("/en");
    expect(switchPath("/en/how-it-works", "")).toBe("/comment-ca-marche");
    expect(switchPath("/sources", "?x=1")).toBe("/en/sources");
    expect(switchPath("/en/unknown", "")).toBe("/");
  });

  it("gives both languages and a French default as alternates", () => {
    expect(alternates("results", "campus=a")).toEqual({
      "fr-CA": "/resultats?campus=a",
      "en-CA": "/en/results?campus=a",
      "x-default": "/resultats?campus=a",
    });
  });
});
