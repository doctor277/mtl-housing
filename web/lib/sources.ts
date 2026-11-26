// The /sources page's facts that aren't in the data files (M5.2, owner's M5 decisions 11–12):
// where each source is published, its licence, and the validation results. Wording lives in
// lib/strings. Every value here is checked by sources.test.ts against what it cites:
// DATA_SOURCES.md (links and licences) and data/manifest.csv for the sources,
// pipeline/validation/ for the numbers.

import type { Lang } from "./localized";

export type LicenceKey = "ccBy4" | "odbl" | "statcanOpen" | "cmhcData";

/** The licences' own pages in each language (English checked 2026-11-25, French 2026-11-26). */
export const LICENCE_URLS: Record<Lang, Record<LicenceKey, string>> = {
  en: {
    ccBy4: "https://creativecommons.org/licenses/by/4.0/",
    odbl: "https://www.openstreetmap.org/copyright",
    statcanOpen: "https://www.statcan.gc.ca/en/reference/licence",
    cmhcData:
      "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/cmhc-licence-agreement-use-of-data",
  },
  fr: {
    ccBy4: "https://creativecommons.org/licenses/by/4.0/deed.fr",
    odbl: "https://www.openstreetmap.org/copyright/fr",
    statcanOpen: "https://www.statcan.gc.ca/fr/reference/licence",
    cmhcData:
      "https://www.cmhc-schl.gc.ca/professionnels/marche-du-logement-donnees-et-recherche/donnees-sur-le-logement/entente-de-licence-avec-la-schl-pour-lutilisation-de-donnees",
  },
};

export type SourceId = "stm" | "rem" | "exo" | "osm" | "quartiers" | "census" | "cmhc" | "statcanRent";

export interface Source {
  id: SourceId;
  /** The publisher's page for the data, as in DATA_SOURCES.md. */
  url: string;
  /** Its French version, where the publisher has one and `url` isn't already French (M5.3b). */
  urlFr?: string;
  licence: LicenceKey;
}

/** The source's page in the reader's language, when there is one. */
export const sourceUrl = (s: Source, lang: Lang) => (lang === "fr" && s.urlFr ? s.urlFr : s.url);

/** In the order the page lists them: commute first, then rent. Dates come from the data files,
 * except the Ville de Montréal download date below. */
export const SOURCES: Source[] = [
  { id: "stm", url: "https://www.stm.info/a-propos/documents-donnees/donnees-ouvertes", licence: "ccBy4" },
  { id: "rem", url: "https://gtfs.gpmmom.ca/gtfs/gtfs.zip", licence: "ccBy4" },
  { id: "exo", url: "https://exo.quebec/fr/a-propos/donnees-ouvertes", licence: "ccBy4" },
  { id: "osm", url: "https://download.geofabrik.de/north-america/canada/quebec.html", licence: "odbl" },
  { id: "quartiers", url: "https://donnees.montreal.ca/dataset/quartiers", licence: "ccBy4" },
  {
    id: "census",
    url: "https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/attribute-attribs/index2021-eng.cfm",
    urlFr: "https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/attribute-attribs/index2021-fra.cfm",
    licence: "statcanOpen",
  },
  {
    id: "cmhc",
    url: "https://www03.cmhc-schl.gc.ca/hmip-pimh/en",
    urlFr: "https://www03.cmhc-schl.gc.ca/hmip-pimh/fr",
    licence: "cmhcData",
  },
  {
    id: "statcanRent",
    url: "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=4610009201",
    urlFr: "https://www150.statcan.gc.ca/t1/tbl1/fr/tv.action?pid=4610009201",
    licence: "statcanOpen",
  },
];

/** The Ville de Montréal quartiers have no date of their own in the data files: this is the
 * download date pinned in data/manifest.csv. */
export const QUARTIERS_DOWNLOADED = "2026-11-20";

/** The validation file every number below comes from. */
export const VALIDATION_FILE = "pipeline/validation/VALIDATION.md";

/** R5 against Google Maps, transit trips only (the platform walks are calibration). Pass rule:
 * |R5 − Google| ≤ max(5 min, 15% of Google). */
export const VALIDATION = {
  rule: { minMinutes: 5, pct: 15 },
  /** The day Google Maps was asked about ("arrive by 8:30"). Fixed here, not taken from
   * commute.json: a later refresh moves the analysis date, not these Google times. */
  googleDate: "2026-12-01",
  /** When the Google times were collected. */
  googleCollected: { udem: "2026-11-20", others: "2026-11-23" },
  passed: {
    udem: { pass: 6, total: 7 },
    mcgill: { pass: 4, total: 5 },
    concordia_sgw: { pass: 5, total: 5 },
  },
  /** UdeM route 4 (3800 Ontario Est): Google's first suggestion is a different, slower trip. */
  udemRoute4: { googleFirst: 60, googleLikeForLike: 52, ours: 47 },
  /** UdeM route 3 (1500 Fleury Est): passes Google's first suggestion, fails its fastest trip. */
  udemRoute3: { googleFirst: 50, googleFastest: 42, ours: 49 },
  /** McGill route 5 (Fairview–Pointe-Claire REM): the one McGill failure (limitation 3). */
  mcgillRoute5: { google: 33, ours: 40 },
  /** Concordia from the east: the printed 7:45 itineraries get off at Peel and walk this long. */
  concordiaPeelWalk: 9,
} as const;
