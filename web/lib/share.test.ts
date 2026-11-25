import { describe, expect, it } from "vitest";
import { parseSearch } from "./search";
import { sharePreview, summaryLine } from "./share";
import { strings } from "./strings";

// Clearly fake fixture (CLAUDE.md): campus "a", shown as "Campus A".
const parsed = (params: Record<string, string>) => {
  const r = parseSearch(params, ["a"]);
  if (!r.ok) throw new Error("fixture should parse");
  return r.search;
};

describe("sharing a search", () => {
  it("writes the summary line from the search's own values", () => {
    expect(summaryLine(parsed({ campus: "a", size: "1br", budget: "1500", max: "45" }), "Campus A")).toBe(
      "Campus A · 3½ · up to $1,500 a month · 45 min max",
    );
    expect(summaryLine(parsed({ campus: "a", size: "room", budget: "", max: "20" }), "Campus A")).toBe(
      "Campus A · Room · no budget · 20 min max",
    );
  });

  it("builds the link preview from the parsed search (size in a sentence, budget kept)", () => {
    expect(sharePreview(parsed({ campus: "a", size: "2br", budget: "1800", max: "30" }), "Campus A")).toEqual({
      title: "Campus A · 4½ · ≤ $1,800/mo · 30 min · [NAME]",
      description:
        "Montréal neighbourhoods within 30 min of Campus A by public transit, for a 4½ up to $1,800 a month, with estimated rents.",
    });
    const noBudget = sharePreview(parsed({ campus: "a", size: "studio", max: "60" }), "Campus A");
    expect(noBudget.title).toBe("Campus A · Studio · 60 min · [NAME]");
    expect(noBudget.description).toBe(
      "Montréal neighbourhoods within 60 min of Campus A by public transit, for a studio, with estimated rents.",
    );
  });

  it("keeps the site name within the first 60 characters (owner, M5.1)", () => {
    // The longest usual case: the longest campus label, the longest size label ("Studio"), a
    // four-digit budget, 60 min. Measured with the real site name, so it still guards once
    // "[NAME]" is replaced (a name of about 12 characters or more would fail it).
    const longestCampus = ["udem", "mcgill", "concordia_sgw"]
      .map((id) => strings.commute.campusShort(id, id))
      .reduce((a, b) => (b.length > a.length ? b : a));
    const { title } = sharePreview(parsed({ campus: "a", size: "studio", budget: "9999", max: "60" }), longestCampus);
    expect(title.endsWith(strings.siteName)).toBe(true);
    expect(title.length).toBeLessThanOrEqual(60);
  });
});
