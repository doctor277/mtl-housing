import { describe, expect, it } from "vitest";
import type { RentEntry, RentMeta } from "../rent";
import { en, fr } from ".";

// French (M5.3b): the same shape as English, Québec formats (owner's M5 decision 8).
const NB = " ";

/** Every key path, with "fn/N" for a function of N parameters. */
function shape(obj: unknown, path = ""): string[] {
  if (typeof obj === "function") return [`${path} fn/${obj.length}`];
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    return Object.entries(obj).flatMap(([k, v]) => shape(v, `${path}.${k}`));
  }
  return [path];
}

/** Every string French shows: plain strings, and the functions' output with every argument a
 * number (7). Functions that need an object (rent lines, lists) can't run that way and are
 * skipped here; the rent and list tests below cover them. */
function allText(obj: unknown): string[] {
  if (typeof obj === "string") return [obj];
  if (typeof obj === "function") {
    try {
      const out = obj(...Array.from({ length: obj.length }, () => 7));
      return typeof out === "string" ? [out] : Array.isArray(out) ? out.filter((x) => typeof x === "string") : [];
    } catch {
      return [];
    }
  }
  if (obj && typeof obj === "object") return Object.values(obj).flatMap(allText);
  return [];
}

describe("French strings", () => {
  it("have exactly the English keys, and functions take as many arguments", () => {
    expect(shape(fr)).toEqual(shape(en));
  });

  it("use Québec formats", () => {
    expect(fr.format.dollars(1500)).toBe(`1${NB}500`);
    expect(fr.format.rent(1475)).toBe(`≈${NB}1${NB}475${NB}$`);
    expect(fr.format.clock(7 * 60 + 30)).toBe(`7${NB}h${NB}30`);
    expect(fr.format.longDate("2026-12-01")).toBe("mardi 1er décembre 2026");
    expect(fr.format.longDate("2026-11-24")).toBe("mardi 24 novembre 2026");
    expect(fr.format.date("2026-11-19T21:22:20Z")).toBe("19 novembre 2026");
    expect(fr.example.label("UdeM", "3½", 1500, 45)).toBe(`UdeM, 3½, 1${NB}500${NB}$, 45 min`);
    expect(fr.results.groupHint.over(10)).toBe(`Jusqu’à 10${NB}% au-dessus de votre budget.`);
    expect(fr.map.popup.signedMin(1.9)).toBe("+1,9 min");
    expect(fr.map.popup.signedMin(-2.4)).toBe("−2,4 min");
    expect(fr.howItWorks.commute.walking(4)).toContain("4 km/h");
    expect(fr.rent.classPct([0.85, 0.95])).toEqual([`<${NB}85${NB}%`, `85–95${NB}%`, `>${NB}95${NB}%`]);
    expect(fr.rent.classRanges([1275, 1425], 25)).toEqual([
      `moins de 1${NB}275${NB}$`,
      `1${NB}275${NB}$ à 1${NB}400${NB}$`,
      `1${NB}425${NB}$ ou plus`,
    ]);
  });

  it("put CMHC's dates and StatCan's quarter in French", () => {
    expect(fr.footer.dataLine("mardi 1er décembre 2026", "October 2025", "2026 Q2")).toContain(
      "SCHL (octobre 2025) et loyers demandés expérimentaux de Statistique Canada (2e trimestre de 2026)",
    );
    expect(fr.sources.list.dates.cmhc("October 2025")).toBe("Enquête d’octobre 2025.");
    expect(fr.sources.list.dates.cmhc("November 2025")).toBe("Enquête de novembre 2025.");
  });

  it("capitalize a building name only where it opens a line", () => {
    expect(
      fr.detail.buildings([
        { name: "pavillon Roger-Gaudry", time: "20 min" },
        { name: "pavillon Jean-Brillant", time: "12 min" },
      ]),
    ).toBe(`Pavillon Roger-Gaudry${NB}: 20 min · pavillon Jean-Brillant${NB}: 12 min`);
    expect(fr.howItWorks.commute.adjustment("pavillon Roger-Gaudry", "+1,9 min")).toBe(
      `Pavillon Roger-Gaudry${NB}: +1,9 min`,
    );
    expect(fr.detail.toPlace("portail Roddick")).toBe("jusqu’au portail Roddick");
  });

  it("use the owner's short size hint, breaking only between items (M5.3b)", () => {
    const hint = fr.form.size.hint;
    expect(hint.replaceAll(NB, " ").replaceAll("⁠", "")).toBe(
      "Chambre : dans un appartement partagé · Studio : 1½–2½ · 3½ : 1 chambre · 4½ : 2 chambres",
    );
    expect(hint.split(" · ").every((item) => !item.includes(" "))).toBe(true);
  });

  it("use the owner's wording for the commute range and unreachable homes (M5.3b)", () => {
    expect(fr.detail.range(5, 19, 120)).toBe(
      `Selon l’endroit dans le quartier${NB}: de 5 à 19 min pour la plupart des logements.`,
    );
    expect(fr.detail.manyUnreachable(15, 120)).toBe(
      `15${NB}% des logements de ce quartier sont à plus de 2 heures en transport collectif.`,
    );
  });

  it("give UdeM its article and McGill none", () => {
    expect(fr.results.noneWithin(30, "UdeM")).toBe("Aucun quartier n’est à moins de 30 min de l’UdeM.");
    expect(fr.results.noneWithin(30, "McGill")).toBe("Aucun quartier n’est à moins de 30 min de McGill.");
    expect(fr.detail.toClosestBuilding("UdeM")).toBe("jusqu’au pavillon de l’UdeM le plus proche");
  });

  it("never put a plain space before a colon or % (Québec: non-breaking)", () => {
    const sample = allText(fr);
    // Most French text comes from functions: make sure they were rendered, not skipped.
    expect(sample.length).toBeGreaterThan(200);
    expect(sample.filter((s) => / :/.test(s))).toEqual([]);
    // …and always a space after it (unless it ends the text).
    expect(sample.filter((s) => / :[^\s]/.test(s))).toEqual([]);
    expect(sample.filter((s) => / %/.test(s))).toEqual([]);
  });

  it("write the rent lines with CMHC's French grade words and published area names", () => {
    // Clearly fake fixtures (CLAUDE.md): areas N1/N2, zone Z.
    const meta = {
      cmhc: { period: "October 2025" },
      grade_words: {
        b: { en: "very good", fr: "très bon" },
        d: { en: "use with caution", fr: "utiliser avec prudence" },
      },
    } as unknown as RentMeta;
    const one = (label: RentEntry["label"], grade: string): RentEntry => ({
      estimate: 1500,
      label,
      grade,
      coverage_pct: null,
      cmhc_areas: [{ type: label.startsWith("zone") ? "zone" : "area", name: "N1", share: 1, grade }],
    });
    expect(fr.rent.detailLine(one("neighbourhood", "b"), meta)).toBe(
      `D’après le loyer moyen de la SCHL dans le secteur N1 (octobre 2025, cote de fiabilité «${NB}très bon${NB}» de la SCHL).`,
    );
    expect(fr.rent.detailLine(one("neighbourhood_low", "d"), meta)).toContain(
      `que la SCHL qualifie de «${NB}utiliser avec prudence${NB}».`,
    );
    const split: RentEntry = {
      estimate: 1500,
      label: "neighbourhood",
      grade: "b",
      coverage_pct: 86,
      cmhc_areas: [{ type: "area", name: "N1", share: 0.866, grade: "b" }],
    };
    expect(fr.rent.extraLines(split, meta)).toEqual([
      `Couvre 86${NB}% des logements locatifs de ce quartier (N1${NB}: 86,6${NB}%); la SCHL n’a pas de données fiables pour le reste.`,
    ]);
  });
});
