// Page metadata in each language (M5.3b): the site's title and description for link previews
// (text only, M5 decision 4), their locale, and the hreflang alternates that tie each page to
// its twin in the other language.
import type { Metadata } from "next";
import type { Lang } from "@/lib/localized";
import { alternates, otherLang, type PageKey, PATHS } from "@/lib/routes";
import { getStrings } from "@/lib/strings";

/** The root layout's metadata: the home page's title and description, used by every page
 * that doesn't set its own. */
export function siteMetadata(lang: Lang): Metadata {
  const s = getStrings(lang);
  return {
    title: s.meta.title,
    description: s.meta.description,
    openGraph: {
      title: s.meta.title,
      description: s.meta.description,
      type: "website",
      siteName: s.siteName,
      locale: s.meta.locale,
      alternateLocale: getStrings(otherLang(lang)).meta.locale,
    },
  };
}

/** A page's own metadata: its title (if any) and the links to both language versions. */
export function pageMetadata(lang: Lang, page: PageKey, title?: string, query = ""): Metadata {
  return {
    ...(title ? { title } : {}),
    alternates: {
      canonical: `${PATHS[lang][page]}${query ? `?${query}` : ""}`,
      languages: alternates(page, query),
    },
  };
}
