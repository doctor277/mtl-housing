import { describe, expect, it } from "vitest";
import { parseSearch } from "./search";
import { sharePreview, summaryLine } from "./share";
import { en as strings, fr } from "./strings";

// Clearly fake fixture (CLAUDE.md): campus "a", shown as "Campus A".
const parsed = (params: Record<string, string>) => {
  const r = parseSearch(params, ["a"]);
  if (!r.ok) throw new Error("fixture should parse");
  return r.search;
};

describe("sharing a search", () => {
  it("writes the summary line from the search's own values", () => {
    expect(summaryLine(parsed({ campus: "a", size: "1br", budget: "1500", max: "45" }), "Campus A", strings)).toBe(
      "Campus A · 3½ · up to $1,500 a month · 45 min max",
    );
    expect(summaryLine(parsed({ campus: "a", size: "room", budget: "", max: "20" }), "Campus A", strings)).toBe(
      "Campus A · Room · no budget · 20 min max",
    );
  });

  it("builds the link preview from the parsed search (size in a sentence, budget kept)", () => {
    expect(
      sharePreview(parsed({ campus: "a", size: "2br", budget: "1800", max: "30" }), "Campus A", strings),
    ).toEqual({
      title: "Campus A · 4½ · ≤ $1,800/mo · 30 min",
      description:
        "Montréal neighbourhoods within 30 min of Campus A by public transit, for a 4½ up to $1,800 a month, with estimated rents.",
    });
    const noBudget = sharePreview(parsed({ campus: "a", size: "studio", max: "60" }), "Campus A", strings);
    expect(noBudget.title).toBe("Campus A · Studio · 60 min");
    expect(noBudget.description).toBe(
      "Montréal neighbourhoods within 60 min of Campus A by public transit, for a studio, with estimated rents.",
    );
  });

  it("writes French with Québec formats (M5.3b)", () => {
    const NB = " ";
    expect(summaryLine(parsed({ campus: "a", size: "1br", budget: "1500", max: "45" }), "Campus A", fr)).toBe(
      `Campus A · 3½ · jusqu’à 1${NB}500${NB}$ par mois · 45${NB}min${NB}max.`,
    );
    const p = sharePreview(parsed({ campus: "a", size: "room", budget: "1500", max: "30" }), "Campus A", fr);
    expect(p.title).toBe(`Campus A · Chambre · ≤${NB}1${NB}500${NB}$/mois · 30 min`);
    expect(p.description).toBe(
      `Les quartiers de Montréal à moins de 30 min de Campus A en transport collectif, pour une chambre jusqu’à 1${NB}500${NB}$ par mois, avec des loyers estimés.`,
    );
    // UdeM takes the article in French; McGill doesn't.
    expect(sharePreview(parsed({ campus: "a", size: "1br", max: "30" }), "UdeM", fr).description).toContain(
      "30 min de l’UdeM",
    );
  });

  it.each([
    ["en", strings],
    ["fr", fr],
  ] as const)("leaves the site name to og:site_name and fits a preview's ~60 characters: %s", (_, t) => {
    // Owner, M5.3b: no site name in the title (the preview shows og:site_name), so its length
    // no longer limits the name. The longest usual title: the longest campus label, the longest
    // size label, a four-digit budget, 60 min.
    const longestCampus = ["udem", "mcgill", "concordia_sgw"]
      .map((id) => t.commute.campusShort(id, id))
      .reduce((a, b) => (b.length > a.length ? b : a));
    const size = (["room", "studio", "1br", "2br"] as const).reduce((a, b) =>
      t.form.size.labels[b].length > t.form.size.labels[a].length ? b : a,
    );
    const { title } = sharePreview(parsed({ campus: "a", size, budget: "9999", max: "60" }), longestCampus, t);
    expect(title).not.toContain(t.siteName);
    expect(title.length).toBeLessThanOrEqual(60);
  });
});
