import { describe, expect, it } from "vitest";
import {
  type CampusMeta,
  type CampusResult,
  type CommuteFile,
  campusFeatureProps,
  campusOptions,
  commuteTarget,
  windowLabel,
} from "@/lib/commute";

// Clearly fake fixtures (CLAUDE.md): campuses A/B, buildings X/Y.
const dest = (id: string, name: string) => ({
  id,
  name,
  lat: 0,
  lon: 0,
  access_adjustment_min: 0,
});
const ONE: CampusMeta = { name: "Campus B", destinations: [dest("b_x", "Building X")] };
const TWO: CampusMeta = {
  name: "Campus A",
  destinations: [dest("a_x", "Building X"), dest("a_y", "Building Y")],
};

const result = (median: number | null, overMax: boolean): CampusResult => ({
  median,
  p10: median,
  p90: median,
  over_max: overMax ? ["median", "p10", "p90"] : [],
  n_points: 10,
  n_unreachable: 0,
  unreachable_share: 0,
  flags: [],
  rule: "fastest_destination",
  by_destination: {},
});

describe("campus picker and texts", () => {
  it("names what the time is measured to", () => {
    expect(commuteTarget("b", ONE)).toBe("to Building X");
    expect(commuteTarget("udem", TWO)).toBe("fastest UdeM building");
    expect(commuteTarget("a", TWO)).toBe("fastest Campus A building");
  });

  it("describes the departure window from the file's meta", () => {
    const meta = {
      analysis_date: "2026-12-01",
      departure_window: { start: "07:30", minutes: 60 },
    } as unknown as CommuteFile["meta"];
    expect(windowLabel(meta)).toBe("leaving 7:30–8:30, Tue 2026-12-01");
  });

  it("lists the campuses present in commute.json, in file order", () => {
    const commute = { meta: { campuses: { udem: TWO, b: ONE } } } as unknown as CommuteFile;
    expect(campusOptions(commute)).toEqual([
      { key: "udem", label: "UdeM" },
      { key: "b", label: "Campus B" },
    ]);
  });

  it("gives each campus its own status and median property", () => {
    const props = campusFeatureProps({ a: result(31.4, false), b: result(null, true) }, [
      "a",
      "b",
      "c",
    ]);
    expect(props).toEqual({
      status_a: "ok",
      median_a: 31.4,
      status_b: "over_max",
      status_c: "no_data",
    });
  });
});
