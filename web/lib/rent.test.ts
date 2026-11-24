import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  binEdges,
  binIndex,
  binLegend,
  dataLine,
  detailLine,
  extraLines,
  formatRent,
  RENT_BINS,
  type RentEntry,
  type RentFile,
  type RentMeta,
  rentFeatureProps,
  roomLine,
  sourceLine,
} from "@/lib/rent";

// Clearly fake fixtures (CLAUDE.md): areas N1/N2, zone Z, round-number levels and rents.
const META: RentMeta = {
  rounding: { step: 25, mode: "half_up" },
  shown_bedroom_types: ["studio", "1br", "2br"],
  cmhc: { period: "October 2025" },
  statcan: { quarter: "2026 Q2" },
  montreal: {
    studio: { cmhc_average: 900, statcan_asking: 1000 },
    "1br": { cmhc_average: 900, statcan_asking: 1200 },
    "2br": { cmhc_average: 900, statcan_asking: 1500 },
    "3br_plus": { cmhc_average: 900, statcan_asking: 2000 },
  },
  room: { estimate: 500 },
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

describe("classes", () => {
  it("puts each edge at the first $25 step at or above its % of the Montréal level", () => {
    expect(binEdges(1000, 25)).toEqual([850, 950, 1050, 1150, 1300]); // exact multiples stay
    expect(binEdges(1250, 25)).toEqual([1075, 1200, 1325, 1450, 1625]); // 1.3 × 1250 float noise
    // Regression (review): rounding to the nearest step put the 85% edge of 1480 at
    // 1250 = 84.5% and the 95% edge at 1400 = 94.6%; rounding up keeps them at or above.
    expect(binEdges(1480, 25)).toEqual([1275, 1425, 1575, 1725, 1925]);
  });

  it("never colours a rent in a class whose % it doesn't meet", () => {
    const pct = [0, 0.85, 0.95, 1.05, 1.15, 1.3, Infinity];
    for (const level of [1000, 1250, 1480, 1820, 2260, 1337]) {
      const edges = binEdges(level, 25);
      for (let rent = 500; rent <= 4000; rent += 25) {
        const i = binIndex(rent, edges);
        expect(rent / level).toBeGreaterThanOrEqual(pct[i]);
        expect(rent / level).toBeLessThan(pct[i + 1]);
      }
    }
  });

  it("assigns a rent equal to an edge to the class above", () => {
    const edges = binEdges(1000, 25);
    expect(binIndex(825, edges)).toBe(0);
    expect(binIndex(850, edges)).toBe(1);
    expect(binIndex(1000, edges)).toBe(2);
    expect(binIndex(1300, edges)).toBe(5);
    expect(RENT_BINS).toHaveLength(edges.length + 1);
  });

  it("writes the legend in dollars with no gaps between classes", () => {
    expect(binLegend(binEdges(1000, 25), 25)).toEqual([
      "under $850",
      "$850–$925",
      "$950–$1,025",
      "$1,050–$1,125",
      "$1,150–$1,275",
      "$1,300 or more",
    ]);
    expect(formatRent(1475)).toBe("≈ $1,475");
  });
});

describe("texts", () => {
  it("uses the approved line for one CMHC area, with the grade in words", () => {
    expect(detailLine(entry({}), META)).toBe(
      "Based on CMHC's average rent in CMHC area N1 (October 2025, rated very good by CMHC).",
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
      'Weighted average of CMHC areas N1 (62%, rated good) and N2 (38%, rated "use with caution"), by rental units.',
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

  it("uses the owner's line under every estimate; dates go in the data and room lines", () => {
    expect(sourceLine()).toBe(
      "Estimate based on average rents, adjusted to current Montréal asking rents. Not a listing, and possibly low in areas with many long-time tenants.",
    );
    expect(dataLine(META)).toBe(
      "Data: CMHC (October 2025) and Statistics Canada's experimental asking rents (2026 Q2).",
    );
    expect(roomLine(META)).toBe(
      "Room: ≈ $500 a month: Montréal-wide average asking rent for a room, not specific to this neighbourhood (Statistics Canada, 2026 Q2).",
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
    // studio 1000 at level 1000: edges 850/950/1050 → class 2; 3½ 1475 at level 1200:
    // edges 1025/1150/1275/1400/1575 → class 4
    expect(props).toEqual({
      rent_bin_studio: 2,
      rent_low_studio: false,
      rent_bin_1br: 4,
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

  // Counts cross-checked in exact (fraction) arithmetic outside this code.
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
    expect(counts("1br")).toEqual([14, 27, 21, 15, 4, 4]);
    expect(counts("2br")).toEqual([9, 13, 48, 7, 3, 5]);
  });
});
