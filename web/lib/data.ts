// Server-side reads of the pipeline outputs in public/data (the same files the map fetches).
// Server components only: this uses the file system. The files change only when the site is
// rebuilt, so the reads are cached for good ("use cache", Cache Components).

import { readFile } from "node:fs/promises";
import { cacheLife } from "next/cache";
import path from "node:path";
import type { CommuteFile } from "./commute";
import type { RentFile } from "./rent";
import type { Hood } from "./shortlist";

async function readJson<T>(name: string): Promise<T> {
  return JSON.parse(await readFile(path.join(process.cwd(), "public", "data", name), "utf-8")) as T;
}

export async function loadCommute(): Promise<CommuteFile> {
  "use cache";
  cacheLife("max");
  return readJson<CommuteFile>("commute.json");
}

export async function loadRent(): Promise<RentFile> {
  "use cache";
  cacheLife("max");
  return readJson<RentFile>("rent.json");
}

interface HoodProps extends Hood {
  no_residents: boolean;
}

/** Neighbourhoods with residents (the park quartier has none), properties only. */
export async function loadHoods(): Promise<Hood[]> {
  "use cache";
  cacheLife("max");
  const geo = await readJson<{ features: { properties: HoodProps }[] }>("neighbourhoods.geojson");
  return geo.features
    .map((f) => f.properties)
    .filter((p) => !p.no_residents)
    .map(({ id, name, borough }) => ({ id, name, borough }));
}
