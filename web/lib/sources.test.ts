import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { QUARTIERS_DOWNLOADED, SOURCES, VALIDATION, VALIDATION_FILE } from "./sources";

// The /sources page's typed facts, checked against the files they cite (owner, M5 decision 12:
// validation numbers are dated facts citing VALIDATION.md).
const repo = (p: string) => readFileSync(fileURLToPath(new URL(`../../${p}`, import.meta.url)), "utf8");

/** Minimal CSV reader: commas, double-quoted fields, "" escapes. */
function csv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  const endRow = () => {
    row.push(field);
    rows.push(row);
    row = [];
    field = "";
  };
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      endRow();
    } else field += ch;
  }
  if (field || row.length) endRow();
  const [head, ...body] = rows.filter((r) => r.some((c) => c !== ""));
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ""])));
}

const results = (campus: string) => csv(repo(`pipeline/validation/${campus}_results.csv`));
const transit = (campus: string) => results(campus).filter((r) => r.kind === "transit");

describe("/sources: validation facts match pipeline/validation", () => {
  it.each(Object.entries(VALIDATION.passed))("%s: transit trips passed", (campus, { pass, total }) => {
    const rows = transit(campus);
    expect(rows.length).toBe(total);
    expect(rows.filter((r) => r.verdict === "pass").length).toBe(pass);
  });

  it("the pass rule is the one the results use", () => {
    for (const campus of Object.keys(VALIDATION.passed)) {
      for (const r of transit(campus)) {
        const google = Number(r.google_min);
        const tol = Math.max(VALIDATION.rule.minMinutes, (VALIDATION.rule.pct / 100) * google);
        // The CSV keeps one decimal (8.25 is written 8.2).
        expect(Math.abs(Number(r.tolerance_min) - tol)).toBeLessThanOrEqual(0.05 + 1e-9);
      }
    }
  });

  it("UdeM route 4: Google's first trip, its like-for-like trip, and our time as shown", () => {
    const r = transit("udem").find((x) => x.route === "4")!;
    expect(Number(r.google_min)).toBe(VALIDATION.udemRoute4.googleFirst);
    expect(Number(r.google_alt_min)).toBe(VALIDATION.udemRoute4.googleLikeForLike);
    expect(r.alt_verdict).toBe("pass");
    expect(Math.round(Number(r.r5_median_min))).toBe(VALIDATION.udemRoute4.ours);
  });

  it("McGill route 5: the one McGill failure", () => {
    const r = transit("mcgill").find((x) => x.route === "5")!;
    expect(r.verdict).toBe("fail");
    expect(Number(r.google_min)).toBe(VALIDATION.mcgillRoute5.google);
    expect(Math.round(Number(r.r5_median_min))).toBe(VALIDATION.mcgillRoute5.ours);
  });

  it("Concordia from the east: the printed itineraries end at Peel with that walk", () => {
    const east = transit("concordia_sgw").filter((r) => r.r5_route_0745.includes("Station Peel"));
    expect(east.map((r) => r.route)).toEqual(["1", "3", "5"]);
    for (const r of east) expect(r.r5_route_0745.endsWith(`walk ${VALIDATION.concordiaPeelWalk}`)).toBe(true);
  });

  it("the collection dates are the ones VALIDATION.md gives", () => {
    const md = repo(VALIDATION_FILE);
    expect(md).toContain(`collected the Google numbers on ${VALIDATION.googleCollected.udem}`);
    expect(md).toContain(`Collected on ${VALIDATION.googleCollected.others}`);
  });
});

describe("/sources: sources match DATA_SOURCES.md and the manifest", () => {
  it("every source link is the one DATA_SOURCES.md or data/manifest.csv records", () => {
    const cited = repo("DATA_SOURCES.md") + repo("data/manifest.csv");
    for (const s of SOURCES) expect(cited, s.id).toContain(s.url);
  });

  it("the Ville de Montréal download date is the manifest's", () => {
    const row = csv(repo("data/manifest.csv")).find((r) => r.file.endsWith("quartierreferencehabitation.geojson"))!;
    expect(row.downloaded_on).toBe(QUARTIERS_DOWNLOADED);
  });
});
