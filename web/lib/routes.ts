// The site's pages in each language (M5.3b, owner's M5 decision 7 and M5.3 answers): French is
// the default at /, English at /en/…, each with its own words in the path. The search
// parameters (campus, size, budget, max, sort, view) are the same in both languages, so
// switching language keeps the search by changing only the path.
import type { Lang } from "./localized";

export type PageKey = "home" | "results" | "howItWorks" | "sources";

export const PATHS: Record<Lang, Record<PageKey, string>> = {
  fr: { home: "/", results: "/resultats", howItWorks: "/comment-ca-marche", sources: "/sources" },
  en: { home: "/en", results: "/en/results", howItWorks: "/en/how-it-works", sources: "/en/sources" },
};

export const LANGS: readonly Lang[] = ["fr", "en"];

export const otherLang = (lang: Lang): Lang => (lang === "fr" ? "en" : "fr");

/** The page a path shows, in whichever language, or null for anything else. */
export function pageAt(pathname: string): { lang: Lang; page: PageKey } | null {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  for (const lang of LANGS) {
    for (const page of Object.keys(PATHS[lang]) as PageKey[]) {
      if (PATHS[lang][page] === path) return { lang, page };
    }
  }
  return null;
}

/** The same page in the other language, keeping the query string ("?campus=…" or ""). Any
 * path that isn't one of the site's pages goes to the other language's home. */
export function switchPath(pathname: string, search: string): string {
  const here = pageAt(pathname);
  if (!here) return PATHS[pathname.startsWith("/en") ? "fr" : "en"].home;
  const to = PATHS[otherLang(here.lang)][here.page];
  return here.page === "results" ? `${to}${search}` : to;
}

/** hreflang alternates for a page's metadata: both languages, plus x-default (French). */
export function alternates(page: PageKey, query = "") {
  const q = query ? `?${query}` : "";
  return {
    "fr-CA": `${PATHS.fr[page]}${q}`,
    "en-CA": `${PATHS.en[page]}${q}`,
    "x-default": `${PATHS.fr[page]}${q}`,
  };
}
