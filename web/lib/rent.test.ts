import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  binEdges,
  binIndex,
  binLegend,
  detailLine,
  extraLines,
  formatRent,
  RENT_BINS,
  type RentEntry,
  type RentFile,
  type RentMeta,
  rentFeatureProps,
  roomLine,
  roundToStep,
  sourceLine,
} from "@/lib/rent";

// Clearly fake fixtures (CLAUDE.md): areas N1/N2, zone Z.
const META: RentMeta = {
  rounding: { step: 25, mode: "half_up" },
  shown_bedroom_types: ["studio", "1br", "2br"],
  cmhc: { period: "October 2025" },
  statcan: { quarter: "2026 Q2" },
  montreal: {
    studio: { cmhc_average: 1000, statcan_asking: 1250 },
    "1br": { cmhc_average: 1000, statcan_asking: 1480 },
    "2br": { cmhc_average: 1000, statcan_asking: 1820 },
    "3br_plus": { cmhc_average: 1000, statcan_asking: 2260 },
  },
  room: { estimate: 725 },
  grade_words: { a: "excellent", b: "very good", c: "good", d: "use with caution" },
};

const entry = (e: Partial<RentEntry>): RentEntry => ({
  estimate: 1500,
  label: "neighbourhood",
  grade: "b",
  coverage_pct: null,
  cmhc_areas: [{ type: "area", name: "N1", share: 1, grade: "b" }],
  ...e,
});

describe("rounding and classes", () => {
  it("rounds half up to $25 like the pipeline", () => {
    expect(roundToStep(1187.5, 25)).toBe(1200); // a tie goes up
    expect(roundToStep(1612.49, 25)).toBe(1600);
    expect(roundToStep(1258, 25)).toBe(1250);
  });

  it("puts class edges at % of the Montréal level, rounded to $25", () => {
    // Same numbers as the pipeline-side check for 2026 Q2.
    expect(binEdges(1250, 25)).toEqual([1075, 1200, 1325, 1450, 1625]);
    expect(binEdges(1480, 25)).toEqual([1250, 1400, 1550, 1700, 1925]);
    expect(binEdges(1820, 25)).toEqual([1550, 1725, 1900, 2100, 2375]);
  });

  it("assigns a rounded rent to a class: an edge belongs to the class above", () => {
    const edges = binEdges(1480, 25);
    expect(binIndex(1225, edges)).toBe(0);
    expect(binIndex(1250, edges)).toBe(1);
    expect(binIndex(1475, edges)).toBe(2);
    expect(binIndex(1925, edges)).toBe(5);
    expect(RENT_BINS).toHaveLength(edges.length + 1);
  });

  it("writes the legend in dollars with no gaps between classes", () => {
    expect(binLegend(binEdges(1480, 25), 25)).toEqual([
      "under $1,250",
      "$1,250–$1,375",
      "$1,400–$1,525",
      "$1,550–$1,675",
      "$1,700–$1,900",
      "$1,925 or more",
    ]);
    expect(formatRent(1475)).toBe("≈ $1,475");
  });
});

describe("texts", () => {
  it("uses the approved line for one CMHC area, with the grade in words", () => {
    expect(detailLine(entry({}), META)).toBe(
      "Based on CMHC's average rent in CMHC area N1 (October 2025, rated very good by CMHC), adjusted to current Montréal asking rents.",
    );
    expect(extraLines(entry({}), META)).toEqual([]);
  });

  it("names the wider zone for zone estimates, low or not", () => {
    const z = (label: RentEntry["label"], grade: string) =>
      entry({ label, grade, cmhc_areas: [{ type: "zone", name: "Z", share: 1, grade }] });
    expect(detailLine(z("zone", "c"), META)).toBe(
      "CMHC has no reliable figure for this area, so this uses the wider CMHC zone Z (rated good by CMHC).",
    );
    expect(detailLine(z("zone_low", "d"), META)).toBe(
      'Based on the wider CMHC zone Z, which CMHC rates "use with caution".',
    );
  });

  it("never prints a grade letter", () => {
    for (const grade of ["a", "b", "c", "d"]) {
      const label = grade === "d" ? "neighbourhood_low" : "neighbourhood";
      const text = detailLine(
        entry({ label, grade, cmhc_areas: [{ type: "area", name: "N1", share: 1, grade }] }),
        META,
      );
      expect(text).not.toMatch(new RegExp(`\\(${grade}\\)|rated ${grade}\\b`));
    }
  });

  it("splits: rating per area, raw whole-percent shares", () => {
    const e = entry({
      label: "neighbourhood_low",
      grade: "d",
      cmhc_areas: [
        { type: "area", name: "N1", share: 0.619, grade: "c" },
        { type: "area", name: "N2", share: 0.381, grade: "d" },
      ],
    });
    expect(detailLine(e, META)).toBe(
      'Based on CMHC\'s average rents in CMHC areas N1 and N2; CMHC rates at least one of them "use with caution".',
    );
    expect(extraLines(e, META)).toEqual([
      "Weighted average of CMHC areas N1 (62%, rated good) and N2 (38%, rated use with caution), by rental units.",
    ]);
  });

  it("partial coverage: covers X% plus the raw share of the area used", () => {
    const e = entry({
      coverage_pct: 86,
      cmhc_areas: [{ type: "area", name: "N1", share: 0.866, grade: "a" }],
    });
    expect(extraLines(e, META)).toEqual([
      "Covers 86% of this neighbourhood's rental units (N1: 86.6%); CMHC has no reliable figure for the rest.",
    ]);
  });

  it("not enough data has its own line", () => {
    const e = entry({ estimate: null, label: "none", grade: null, cmhc_areas: [] });
    expect(detailLine(e, META)).toBe(
      "CMHC doesn't publish a reliable rent for this size here or nearby.",
    );
    expect(extraLines(e, META)).toEqual([]);
  });

  it("source and room lines carry the dates", () => {
    expect(sourceLine(META)).toBe(
      "Estimated rent for a new lease, not a real listing. Based on CMHC (October 2025) and Statistics Canada's experimental asking rents (2026 Q2).",
    );
    expect(roomLine(META)).toBe(
      "Room: ≈ $725 a month: Montréal-wide average asking rent for a room, not specific to this neighbourhood (Statistics Canada, 2026 Q2).",
    );
  });
});

describe("map properties", () => {
  it("gives one class and one low-reliability flag per shown size", () => {
    const e = (estimate: number | null, label: RentEntry["label"]) => entry({ estimate, label });
    const props = rentFeatureProps(
      {
        studio: e(1000, "neighbourhood"),
        "1br": e(1475, "neighbourhood_low"),
        "2br": e(null, "none"),
        "3br_plus": e(3000, "zone"),
      },
      META,
    );
    expect(props).toEqual({
      rent_bin_studio: 0,
      rent_low_studio: false,
      rent_bin_1br: 2,
      rent_low_1br: true,
      rent_bin_2br: -1,
      rent_low_2br: false,
    });
  });
});

describe("the committed rent.json", () => {
  const file = JSON.parse(
    readFileSync(fileURLToPath(new URL("../public/data/rent.json", import.meta.url)), "utf8"),
  ) as RentFile;

  it("has every shown size for every neighbourhood, in $25 steps", () => {
    for (const entries of Object.values(file.results)) {
      for (const size of file.meta.shown_bedroom_types) {
        const e = entries[size];
        expect(e).toBeDefined();
        if (e.estimate !== null) expect(e.estimate % file.meta.rounding.step).toBe(0);
        expect(detailLine(e, file.meta).length).toBeGreaterThan(0);
      }
    }
  });

  it("spreads over the classes as reported in the PR (studio > 130% is empty)", () => {
    const counts = (size: "studio" | "1br" | "2br") => {
      const edges = binEdges(file.meta.montreal[size].statcan_asking, file.meta.rounding.step);
      const c = Array(RENT_BINS.length).fill(0);
      for (const entries of Object.values(file.results)) {
        const v = entries[size].estimate;
        if (v !== null) c[binIndex(v, edges)] += 1;
      }
      return c;
    };
    expect(counts("studio")).toEqual([37, 22, 16, 8, 8, 0]);
    expect(counts("1br")).toEqual([14, 25, 23, 9, 10, 4]);
    expect(counts("2br")).toEqual([9, 13, 38, 17, 3, 5]);
  });
});
